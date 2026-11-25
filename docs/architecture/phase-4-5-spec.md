# Phase 4-5 Spec: Processing Service Shadow Mode & Snapshot Ownership Cutover

## Objective
Deploy a new `svitlo-power-processing` service that computes dashboard snapshots from **MongoDB directly** (using existing shared repositories), validate in shadow mode, then cut over snapshot ownership from the legacy `back-end`.

## Scope
- **New Service**: `svitlo-power-processing` (NestJS + TypeScript, deployed independently, reads MongoDB through Mongoose repositories in `shared/typescript`)
- **Phase 4**: Shadow mode — computes snapshots, compares with production, does NOT publish to production keys
- **Phase 5**: Cutover — becomes authoritative publisher; legacy `back-end` stops publishing
- **Consumers**: Both back-ends (unchanged, already reading from Redis)
- **Data**: Same `DashboardSnapshot` v1 schema
- **Redis**: Per `redis-conventions.md` (including lease for single-writer)

## Architecture

```
┌─────────────────┐     MongoDB (direct)       ┌──────────────────┐
│  Deye API       │◄──────────────────────────│                  │
│  (external)     │                           │                  │
└─────────────────┘                           │                  │
                                              │  Processing      │
┌─────────────────┐     MongoDB (direct)      │  Service         │
│  Stations       │◄──────────────────────────│  (svitlo-power-  │
│  (MongoDB)      │                           │   processing)    │
└─────────────────┘                           │                  │
                                              │  - Reads MongoDB │
┌─────────────────┐     MongoDB (direct)      │    via Mongoose  │
│  Outage         │◄──────────────────────────│    repositories  │
│  Schedule       │                           │  - Builds        │
│  (MongoDB)      │                           │    snapshot      │
└─────────────────┘                           │  - Publishes to  │
                                              │    Redis (Phase 5)│
                                              │  - Holds lease   │
                                              └────────┬─────────┘
                                                       │ Redis
                                                       ▼
┌─────────────────┐     Redis Pub/Sub         ┌──────────────────┐
│  Back-end       │──────────────────────────►│                  │
│  (admin, sub)   │                           │   Redis          │
└─────────────────┘                           │   (cache +       │
                                              │    notifications)│
┌─────────────────┐                           │                  │
│  App-back-end   │──────────────────────────►│                  │
│  (public, sub)  │                           └──────────────────┘
└─────────────────┘
```

**Key**: Processing reads MongoDB directly through the Mongoose schemas in
`shared/typescript` — no HTTP calls to `back-end`. This avoids circular
dependency and matches ADR ownership.

## Phase 4: Shadow Mode Deliverables

### 1. Processing Service Structure
```
svitlo-power-processing/
├── package.json
├── Dockerfile
├── src/
│   ├── main.ts                       # Entry point, lifecycle
│   ├── app.module.ts                 # Root module
│   ├── config/processing.config.ts   # Validated configuration
│   ├── snapshot/
│   │   ├── snapshot.builder.ts       # Builds DashboardSnapshot from MongoDB
│   │   └── snapshot.validator.ts     # Contract validation before publishing
│   ├── infrastructure/redis/         # Redis clients + Lua scripts
│   ├── lease/processing-lease.service.ts  # Single-writer lease
│   ├── scheduler/                    # Reconciliation cadence
│   ├── triggers/                     # Coalesced refresh trigger
│   ├── shadow/                       # Shadow publisher + comparator
│   ├── metrics/                      # Prometheus registry + listener
│   └── health/                       # Liveness/readiness
├── test/                             # node:test suites
└── tsconfig.json
```

### 2. MongoDB Access (Direct, via Shared Schemas)
**Uses the Mongoose schemas from `@svitlo-power/shared-typescript/schemas`**:
- `StationSchema` → station configuration
- `StationDataSchema` → measurements
- `ExtDataSchema` → reporter observations
- `OutagesScheduleSchema` → outage schedules (read from Redis in practice)
- `BuildingSchema` → buildings, config

**No HTTP calls to back-end**. Processing is a **read-only** consumer of the
domain collections: `autoIndex` and `autoCreate` are disabled so the shadow
service never writes to the Python-owned collections.

### 3. Snapshot Builder
```typescript
class SnapshotBuilder {
  async build(input: { epoch: number; version: number }): Promise<SnapshotBuildResult> {
    // 1. Fetch config, buildings and outage schedules in parallel
    // 2. Transform to the snapshot schema (buildings, config, outagesSchedules)
    // 3. Assign (epoch, version) from the Redis counters
    // 4. Validate against the contract (SnapshotValidator)
    // 5. Return the snapshot plus build timing
  }
}
```

### 4. Scheduler & Triggers
| Trigger | Mechanism |
|---------|-----------|
| Startup | Immediate build + publish (Phase 5) |
| Deye poll cycle | **Detect new measurements in MongoDB** (latest timestamp per station); do NOT call Deye directly (polling stays in `back-end` until Phase 6.3) |
| Station sync | Listen to station changes (webhook or poll) |
| Outage schedule fetch (Yasno) | Detect new schedule in Redis (updatedAt); do NOT call Yasno directly (fetch stays in `back-end` until Phase 6.3) |
| Building CRUD / config save / station binding change | HTTP `POST /internal/v1/snapshots/refresh` (coalesced 500ms) |
| Cache miss (BFF request) | HTTP `POST /internal/v1/snapshots/refresh` (coalesced 500ms) |
| Periodic reconciliation | Every `PROCESSING_RECONCILIATION_INTERVAL_SECONDS` (default 300s): build + compare with Redis (detect drift) |

**Coalescing**: Multiple triggers within `PROCESSING_REFRESH_COALESCE_MS`
(default 500ms) produce a single build. A request that arrives while a build is
already running queues a follow-up build, so a refresh after a config change
cannot return a snapshot that predates it.

### 5. Lease Management (Single-Writer)
```typescript
class ProcessingLease {
  async acquire(): Promise<boolean>;   // Returns true if acquired
  async renew(): Promise<boolean>;     // Called every 10s
  async release(): Promise<void>;
  onAcquired(listener: () => void): void;
  get isHolder(): boolean;
}
```

- Only the lease holder builds and publishes snapshots
- If the lease is lost: stop publishing, wait for re-acquisition
- The epoch is re-seeded on every acquisition, so a replica that was a standby
  cannot get stuck rejecting its own writes as `epoch-stale`
- Metrics: `processing_lease_acquired_total`, `processing_lease_lost_total`

### 6. Shadow Mode Comparator (Separate Key Namespace)
**Critical**: Shadow mode MUST NOT touch production Redis keys/lease.

```typescript
class ShadowComparator {
  async compareWithProduction(snapshot: DashboardSnapshot): Promise<ShadowComparison> {
    // 1. Read the current production snapshot from Redis (cache:dashboard:v1:global)
    // 2. Skip the comparison when the two snapshots are further apart than
    //    PROCESSING_COMPARISON_MAX_SKEW_SECONDS (default 120s): live fields
    //    legitimately differ across a large skew
    // 3. Deep diff (field-level), matching buildings by id
    // 4. Record metrics: parity rate, field mismatches, skew
    // 5. Log sample mismatches (max 10/min); the metric counts every mismatch
  }
}
```

**Shadow Redis keys**: Prefixed with `shadow:` — completely isolated from production.

**Metrics**:
| Metric | Type | Target |
|--------|------|--------|
| `processing_shadow_parity_rate` | Gauge | ≥ 99.95% |
| `processing_shadow_mismatch_total` | Counter | < 0.1% of builds |
| `processing_shadow_comparisons_total` | Counter | — |
| `processing_shadow_comparison_skew_seconds` | Gauge | — |
| `processing_shadow_last_comparison_timestamp_seconds` | Gauge | `time() - metric` < 900s |
| `processing_shadow_mode_enabled` | Gauge | — |
| `processing_shadow_lease_held` | Gauge | — |
| `dashboard_snapshot_build_duration_seconds` | Histogram | p99 < 10s |
| `dashboard_snapshot_publish_duration_seconds` | Histogram | p99 < 30s |

The `dashboard_snapshot_*` and `dashboard_refresh_*` names are shared with the
legacy Python producer, so every panel and alert must filter on
`job="svitlo-power-processing"` until the cutover. The shadow-only metrics carry
a `processing_shadow_` prefix and never collide.

`processing_shadow_parity_rate` is exported as `NaN` until the first comparison
completes and is set back to `NaN` whenever a comparison is skipped, so `0` only
ever means a real 0% parity and a `parity < X` alert cannot fire on a skipped
comparison. Freshness is read from
`processing_shadow_last_comparison_timestamp_seconds` instead, which is seeded
with the process start time while shadow mode is enabled. The
`processing-shadow-parity-stale` alert is scoped to instances that are supposed
to compare (`processing_shadow_mode_enabled` and `processing_shadow_lease_held`
both 1), and `processing-down` covers a target that stops being scraped.

### 7. Empty-Cache Rebuild Test
- On startup with empty Redis: build snapshot, verify it matches production
- Automated test in CI: `FLUSHDB` → start processing → verify snapshot appears

## Phase 5: Cutover Deliverables

### 1. Publishing Activation
**Feature flag**: `FEATURE_PROCESSING_PUBLISH_ENABLED` (default: `false` in Phase 4, `true` in Phase 5)

When enabled:
- Lease holder calls `redis_client.publish_snapshot(snapshot)` (Lua script with CAS + lease fence)
- Version from `INCR meta:dashboard:version` (epoch from `meta:dashboard:epoch`)
- Notification published to `cache:dashboard:v1:invalidations`

### 2. Legacy Publisher Quiesce
**Feature flag**: `BACKEND_PUBLISH_ENABLED` (default: `true`)

**Cutover Procedure**:
1. Set `BACKEND_PUBLISH_ENABLED=false` (legacy stops publishing, releases lease)
2. Wait 2 min: verify Redis version stops incrementing from legacy, lease released
3. Set `FEATURE_PROCESSING_PUBLISH_ENABLED=true` (processing acquires lease, starts publishing)
4. Verify: lease holder = `processing-*`, version increments, notifications flow, BFFs receive updates
5. Monitor for 30 min

### 3. Fast Rollback
**Rollback Procedure** (must complete < 2 min):
1. Set `FEATURE_PROCESSING_PUBLISH_ENABLED=false` (processing releases lease)
2. Verify processing stops publishing (lease released, no new versions)
3. Set `BACKEND_PUBLISH_ENABLED=true` (legacy acquires lease)
4. Legacy back-end publishes on next trigger (or manual refresh)
5. BFFs automatically pick up new snapshots (same schema, same Redis keys)

### 4. Post-Cutover: NO Code Removal Yet
**Critical**: Do NOT remove dashboard calculation, Deye polling, station sync, or outage schedule logic from `back-end` yet. Those capabilities only move in **Phase 6**.

`back-end` continues to:
- Run Deye polling & station sync (Phase 6.3)
- Run outage schedule fetch (Phase 6.3)
- Run cleanup jobs (Phase 6.4)
- Run message delivery (Phase 6.5)
- Serve admin CRUD APIs (Phase 6.2)

Only the **snapshot publishing** code path is disabled via flag.

Code removal happens in **Phase 9** after all capabilities are moved.

## Exit Gates

### Phase 4 Exit Gate (Shadow Mode)
| Criterion | Threshold | Window |
|-----------|-----------|--------|
| Shadow parity (field-level vs production) | ≥ 99.95% | 24h production |
| Build success rate | 100% (0 crashes) | 24h production |
| Build duration p99 | < 10s | 24h production |
| Refresh latency p99 | < 30s | 24h production |
| Lease stability | 0 unexpected losses | 24h production |
| Empty-cache rebuild | Passes | Staging + 1 prod test |
| Drift detection | 0 undetected drifts | 24h production |
| Shadow keys isolated | No production key access | Verified |

### Phase 5 Exit Gate (Cutover)
| Criterion | Threshold | Window |
|-----------|-----------|--------|
| All BFFs on processing snapshots | 100% | Immediate |
| Parity vs legacy (pre-cutover) | ≥ 99.99% | 1h post-cutover |
| Freshness (snapshot age) | < 60s | Continuous |
| Version monotonicity | No gaps, no decreases | Continuous |
| Rollback rehearsed | < 2 min | Staging drill |
| Legacy publish code disabled | Flag off, no writes | 24h post-cutover |
| **Legacy calculation code REMAINS** | Not removed | Phase 9 |

## Deployment Steps

### Phase 4 (Shadow)
1. **Staging**:
   - Deploy processing with `PUBLISH_ENABLED=false`
   - Run parity test against production Redis (read-only for snapshots, read-write for shadow keys)
   - Run empty-cache rebuild test
   - Load test: simulate 100 triggers/min

2. **Production (shadow)**:
   - Deploy to production namespace
   - Connect to production Redis (read-only for production snapshots, read-write for shadow keys)
   - Monitor shadow metrics for 48h
   - Alert on parity < 99.95%

### Phase 5 (Cutover)
1. **Staging rehearsal**:
   - Full cutover + rollback drill
   - Time each step, document

2. **Production cutover** (scheduled maintenance window):
   - 0:00  Disable legacy publisher (`BACKEND_PUBLISH_ENABLED=false`)
   - 0:02  Verify legacy stopped (metrics)
   - 0:03  Enable processing publisher (`FEATURE_PROCESSING_PUBLISH_ENABLED=true`)
   - 0:05  Verify processing publishing (version increment, notifications)
   - 0:10  Verify BFFs receiving updates (health checks)
   - 0:30  Confirm all green
   - 1:00  **Do NOT remove legacy code** — only disable publish flag

## Dependencies
- Phase 3 complete (BFFs reading from Redis, SSE working)
- Mongoose schemas published from `shared/typescript`
- Snapshot contract published (`docs/architecture/snapshot-schema.json`)
- Redis lease Lua scripts registered
- Feature flag infrastructure
- CI/CD for new `svitlo-power-processing` service

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Processing crashes, lease expires | Lease TTL 30s, renewal every 10s; new instance acquires within 30s |
| MongoDB unavailable | Startup failure is logged and reported by `/health/ready`; the scheduler retries |
| Version conflict (both publish) | Feature flags + verification wait; lease prevents concurrent publish |
| Schema drift | CI validates every build against the contract; schema registry with compatibility check |
| Large snapshot build time | Parallel fetches; incremental build if only measurements changed (future) |
| BFFs don't reconnect | Phase 3 already validated reconnect behavior |
| Circular dependency | Processing reads MongoDB directly, no HTTP to back-end |

## Test Checklist

### Phase 4
- [ ] Unit: SnapshotBuilder produces valid schema output from MongoDB
- [ ] Unit: Lease acquire/renew/release works correctly
- [ ] Unit: Scheduler coalesces triggers correctly
- [ ] Integration: Full build cycle (trigger → build → compare)
- [ ] Integration: Empty-cache rebuild produces valid snapshot
- [ ] Integration: Lease loss → publishing stops, re-acquisition works
- [ ] Integration: Shadow keys isolated from production keys
- [ ] Load: 100 triggers/min → coalesced to ~1 build/min
- [ ] Chaos: MongoDB down → circuit breaker, cached snapshot served
- [ ] Chaos: Redis down → lease lost, rebuild on recovery
- [ ] Parity: 48h shadow run, mismatch rate < 0.05%

### Phase 5
- [ ] Integration: Cutover procedure (flags, verification steps)
- [ ] Integration: Rollback procedure (< 2 min)
- [ ] Load: Post-cutover, 1000 BFF reads/min + 10 builds/min
- [ ] Chaos: processing crashes mid-cutover → legacy takes over
- [ ] Contract: BFFs unchanged, mobile API unaffected
- [ ] Verify: Legacy calculation code still present and runnable (for rollback)