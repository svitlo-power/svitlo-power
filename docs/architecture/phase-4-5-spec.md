# Phase 4-5 Spec: Processing Service Shadow Mode & Snapshot Ownership Cutover

## Objective
Deploy a new `svitlo-power-processor` service that computes dashboard snapshots from authoritative source APIs, validate in shadow mode, then cut over snapshot ownership from the legacy back-end.

## Scope
- **New Service**: `svitlo-power-processor` (Python, deployed independently)
- **Phase 4**: Shadow mode — computes snapshots, compares with production, does NOT publish
- **Phase 5**: Cutover — becomes authoritative publisher; legacy back-end stops publishing
- **Consumers**: Both BFFs (unchanged, already reading from Redis)
- **Data**: Same `DashboardSnapshot` v1 schema
- **Redis**: Per `redis-conventions.md` (including lease for single-writer)

## Architecture

```
┌─────────────────┐     HTTP (internal)       ┌───────────────────┐
│  Deye API       │◄──────────────────────────│                   │
│  (external)     │                           │                   │
└─────────────────┘                           │                   │
                                              │  Processing       │
                                              │  Service          │
                                              │  (svitlo-power-   │
                                              │   processor)      │
                                              │                   │
                                              │  - Fetches from   │
┌─────────────────┐     HTTP (internal)       │    source APIs    │
│  Outage API     │◄──────────────────────────│  - Builds         │
│  (internal)     │                           │    snapshot       │
└─────────────────┘                           │  - Publishes to   │
                                              │    Redis (Phase 5)│
                                              │  - Holds lease    │
                                              └────────┬──────────┘
                                                       │ Redis
                                                       ▼
┌─────────────────┐     Redis Pub/Sub         ┌───────────────────┐
│  Admin BFF      │──────────────────────────►│                   │
│  (subscriber)   │                           │   Redis           │
└─────────────────┘                           │   (cache +        │
                                              │    notifications) │
┌─────────────────┐                           │                   │
│  App BFF        │──────────────────────────►│                   │
│  (subscriber)   │                           └───────────────────┘
└─────────────────┘
```

## Phase 4: Shadow Mode Deliverables

### 1. Processing Service Structure
```
svitlo-power-processor/
├── pyproject.toml
├── src/
│   └── processor/
│       ├── __init__.py
│       ├── main.py                 # Entry point, lifecycle
│       ├── config.py               # Pydantic settings
│       ├── snapshot/
│       │   ├── __init__.py
│       │   ├── builder.py          # Builds DashboardSnapshot
│       │   ├── sources.py          # HTTP clients for source APIs
│       │   └── schema.py           # Pydantic models from JSON schema
│       ├── redis/
│       │   ├── __init__.py
│       │   ├── client.py           # Redis client + Lua scripts
│       │   └── lease.py            # Single-writer lease
│       ├── scheduling/
│       │   ├── __init__.py
│       │   ├── scheduler.py        # Refresh triggers
│       │   └── triggers.py         # Event detection (polling, webhooks)
│       └── monitoring/
│           ├── __init__.py
│           └── metrics.py          # Prometheus metrics
├── tests/
│   ├── test_builder.py
│   ├── test_sources.py
│   ├── test_lease.py
│   └── test_parity.py              # Compares with production snapshots
└── Dockerfile
```

### 2. Source API Clients
**Interface** (language-neutral, versioned):
```python
class SourceAPIClients:
    async def fetch_stations(self) -> list[StationData]: ...
    async def fetch_measurements(self, since: datetime) -> list[MeasurementData]: ...
    async def fetch_outage_schedules(self) -> list[OutageScheduleData]: ...
```

**Implementation**: HTTP clients calling existing internal APIs (not direct MongoDB)
- `GET http://back-end/internal/v1/stations`
- `GET http://back-end/internal/v1/measurements?since=...`
- `GET http://back-end/internal/v1/outage-schedules`

**Contract**: OpenAPI spec for each (to be defined in Phase 6)

### 3. Snapshot Builder
```python
class SnapshotBuilder:
    def __init__(self, sources: SourceAPIClients): ...
    
    async def build(self) -> DashboardSnapshot:
        # 1. Fetch all source data in parallel
        # 2. Transform to snapshot schema
        # 3. Compute totals
        # 4. Assign monotonic version (from Redis INCR)
        # 5. Validate against Pydantic model (JSON schema)
        # 6. Return snapshot
```

### 4. Scheduler & Triggers
| Trigger | Mechanism |
|---------|-----------|
| Startup | Immediate build + publish (Phase 5) |
| Deye poll cycle | Poll existing Deye client library; on new data → build |
| Station sync | Listen to station API changes (webhook or poll) |
| Outage schedule CRUD | Webhook from admin API or poll |
| Cache miss (BFF request) | Subscribe to `cache:dashboard:v1:refresh-requests`, coalesce 500ms |
| Periodic reconciliation | Every 5 min: build + compare with Redis (detect drift) |

**Coalescing**: Multiple triggers within 500ms → single build

### 5. Lease Management (Single-Writer)
```python
class ProcessingLease:
    def __init__(self, redis: Redis, instance_id: str): ...
    
    async def acquire(self) -> bool:  # Returns True if acquired
    async def renew(self) -> bool:    # Called every 10s
    async def release(self) -> bool:
    @property
    def is_holder(self) -> bool: ...
```

- Only lease holder builds and publishes snapshots
- If lease lost: stop publishing, wait for re-acquisition
- Metrics: `processing_lease_acquired_total`, `processing_lease_lost_total`

### 6. Shadow Mode Comparator
```python
class ShadowComparator:
    async def compare_with_production(self, snapshot: DashboardSnapshot) -> ComparisonResult:
        # 1. Read current production snapshot from Redis
        # 2. Deep diff (field-level)
        # 3. Record metrics: parity rate, field mismatches
        # 4. Log sample mismatches (max 10/min)
```

**Metrics**:
| Metric | Type | Target |
|--------|------|--------|
| `processing_shadow_parity_rate` | Gauge | ≥ 99.9% |
| `processing_shadow_mismatch_total` | Counter | < 0.1% of builds |
| `processing_build_duration_seconds` | Histogram | p99 < 10s |
| `processing_refresh_latency_seconds` | Histogram | p99 < 30s (trigger → snapshot ready) |

### 7. Empty-Cache Rebuild Test
- On startup with empty Redis: build snapshot, verify it matches production
- Automated test in CI: `FLUSHDB` → start processor → verify snapshot appears

## Phase 5: Cutover Deliverables

### 1. Publishing Activation
**Feature flag**: `PROCESSOR_PUBLISH_ENABLED` (default: `false` in Phase 4, `true` in Phase 5)

When enabled:
- Lease holder calls `redis_client.publish_snapshot(snapshot)` (Lua script)
- Version from `INCR meta:dashboard:version`
- Notification published to `cache:dashboard:v1:invalidations`

### 2. Legacy Publisher Quiesce
**Feature flag**: `BACKEND_PUBLISH_ENABLED` (default: `true`)

**Cutover Procedure**:
1. Set `BACKEND_PUBLISH_ENABLED=false` (legacy stops publishing)
2. Wait 2 min: verify Redis version stops incrementing from legacy
3. Set `PROCESSOR_PUBLISH_ENABLED=true` (processor starts publishing)
4. Verify: version increments, notifications flow, BFFs receive updates
5. Monitor for 30 min

### 3. Fast Rollback
**Rollback Procedure** (must complete < 2 min):
1. Set `PROCESSOR_PUBLISH_ENABLED=false`
2. Verify processor stops publishing (lease released, no new versions)
3. Set `BACKEND_PUBLISH_ENABLED=true`
4. Legacy back-end publishes on next trigger (or manual refresh)
5. BFFs automatically pick up new snapshots (same schema, same Redis keys)

### 4. Post-Cutover Cleanup
After 24h observation:
- Remove dashboard calculation code from legacy back-end
- Remove Deye polling, station sync, outage schedule logic from legacy back-end
- Legacy back-end becomes pure admin BFF (Phase 6+)

## Exit Gates

### Phase 4 Exit Gate (Shadow Mode)
| Criterion | Threshold | Window |
|-----------|-----------|--------|
| Shadow parity (field-level) | ≥ 99.95% | 24h production |
| Build success rate | 100% (0 crashes) | 24h production |
| Build duration p99 | < 10s | 24h production |
| Refresh latency p99 | < 30s | 24h production |
| Lease stability | 0 unexpected losses | 24h production |
| Empty-cache rebuild | Passes | Staging + 1 prod test |
| Drift detection | 0 undetected drifts | 24h production |

### Phase 5 Exit Gate (Cutover)
| Criterion | Threshold | Window |
|-----------|-----------|--------|
| All BFFs on processor snapshots | 100% | Immediate |
| Parity vs legacy (pre-cutover) | ≥ 99.99% | 1h post-cutover |
| Freshness (snapshot age) | < 60s | Continuous |
| Version monotonicity | No gaps, no decreases | Continuous |
| Rollback rehearsed | < 2 min | Staging drill |
| Legacy code removed | Dashboard calc deleted | 24h post-cutover |

## Deployment Steps

### Phase 4 (Shadow)
1. **Staging**:
   - Deploy processor with `PUBLISH_ENABLED=false`
   - Run parity test against production Redis (read-only)
   - Run empty-cache rebuild test
   - Load test: simulate 100 triggers/min

2. **Production (shadow)**:
   - Deploy to production namespace
   - Connect to production Redis (read-only for snapshots, read-write for lease)
   - Monitor shadow metrics for 48h
   - Alert on parity < 99.95%

### Phase 5 (Cutover)
1. **Staging rehearsal**:
   - Full cutover + rollback drill
   - Time each step, document

2. **Production cutover** (scheduled maintenance window):
   - 0:00  Disable legacy publisher (`BACKEND_PUBLISH_ENABLED=false`)
   - 0:02  Verify legacy stopped (metrics)
   - 0:03  Enable processor publisher (`PROCESSOR_PUBLISH_ENABLED=true`)
   - 0:05  Verify processor publishing (version increment, notifications)
   - 0:10  Verify BFFs receiving updates (health checks)
   - 0:30  Confirm all green
   - 1:00  Begin legacy code removal (separate deploy)

## Dependencies
- Phase 3 complete (BFFs reading from Redis, SSE working)
- Source APIs available (internal HTTP endpoints on back-end)
- JSON schema published, Pydantic models generated
- Redis lease Lua scripts registered
- Feature flag infrastructure
- CI/CD for new `svitlo-power-processor` service

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Processor crashes, lease expires | Lease TTL 30s, renewal every 10s; new instance acquires within 30s |
| Source API unavailable | Circuit breaker: cache last good snapshot, alert, retry with backoff |
| Version conflict (both publish) | Feature flags + verification wait; lease prevents concurrent publish |
| Schema drift | CI validates every build against schema; schema registry with compatibility check |
| Large snapshot build time | Parallel fetches; incremental build if only measurements changed (future) |
| BFFs don't reconnect | Phase 3 already validated reconnect behavior |

## Test Checklist

### Phase 4
- [ ] Unit: SnapshotBuilder produces valid schema output
- [ ] Unit: Source clients handle errors, timeouts, retries
- [ ] Unit: Lease acquire/renew/release works correctly
- [ ] Unit: Scheduler coalesces triggers correctly
- [ ] Integration: Full build cycle (trigger → build → compare)
- [ ] Integration: Empty-cache rebuild produces valid snapshot
- [ ] Integration: Lease loss → publishing stops, re-acquisition works
- [ ] Load: 100 triggers/min → coalesced to ~1 build/min
- [ ] Chaos: Source API down → circuit breaker, cached snapshot served
- [ ] Chaos: Redis down → lease lost, rebuild on recovery
- [ ] Parity: 48h shadow run, mismatch rate < 0.05%

### Phase 5
- [ ] Integration: Cutover procedure (flags, verification steps)
- [ ] Integration: Rollback procedure (< 2 min)
- [ ] Load: Post-cutover, 1000 BFF reads/min + 10 builds/min
- [ ] Chaos: Processor crashes mid-cutover → legacy takes over
- [ ] Contract: BFFs unchanged, mobile API unaffected