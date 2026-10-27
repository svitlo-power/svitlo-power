# Phase 1 Spec: Publish Dashboard Snapshots to Redis

## Objective
Deploy Redis snapshot writes from the existing `back-end` while it remains the sole dashboard calculator and authoritative producer. No consumer changes in this phase.

## Scope
- **Producer**: Existing `back-end` (Python/FastAPI)
- **Consumers**: Unchanged (`app-back-end`, `sse-back-end` via `back-end` events)
- **Data**: Dashboard + outage-schedule snapshot per `dashboard-snapshot/v1.json`
- **Redis**: Keys/channels per `redis-conventions.md`

## Deliverables

### 1. Snapshot Generation Module
**Location**: `back-end/app/services/dashboard_snapshot.py` (new)

```python
# Interface
class DashboardSnapshotService:
    async def build_snapshot(self) -> DashboardSnapshot: ...
    async def publish_snapshot(self, snapshot: DashboardSnapshot) -> None: ...
    async def refresh_and_publish(self) -> DashboardSnapshot: ...
    async def handle_refresh_request(self, reason: str, requested_by: str) -> dict: ...
```

**Responsibilities**:
- Fetch data from existing internal services (Deye client, station repo, outage schedule repo, dashboard service)
- Transform to `DashboardSnapshot` Pydantic model (validates against JSON schema)
- Atomic write to Redis via Lua script with lease fencing and CAS on (epoch, version)
- Increment monotonic version (from Redis `meta:dashboard:version`)
- Handle HTTP refresh requests with server-side coalescing

### 2. Version & Epoch Management
- **Epoch key**: `meta:dashboard:epoch` (Redis string, integer) — increments on Redis flush/failover
- **Version key**: `meta:dashboard:version` (Redis string, integer) — `INCR` per successful write
- **Initial values**: Set on deploy (read current max from any existing snapshot or start at epoch=1, version=1)
- **Lease**: `back-end` acquires lease `lock:processing:dashboard:v1` on startup (single instance in Phase 1)

### 3. Trigger Points
| Trigger | Action |
|---------|--------|
| Back-end startup | `refresh_and_publish()` |
| Deye poll completes (new measurements) | `refresh_and_publish()` |
| Station sync completes | `refresh_and_publish()` |
| Outage schedule CRUD | `refresh_and_publish()` |
| Manual API `POST /api/admin/dashboard/refresh` | `refresh_and_publish()` |
| HTTP refresh request (BFF cache miss) | Coalesced: debounce 500ms, single refresh |

### 4. Coalesced Refresh on HTTP Request
- New endpoint: `POST /internal/v1/snapshots/refresh` (internal, not public)
- On request: schedule refresh if not already scheduled within 500ms
- Use asyncio `Event` or similar to coalesce multiple requests
- Return current snapshot if already fresh, otherwise trigger rebuild

### 5. Monitoring & Metrics
| Metric | Type | Labels | Target |
|--------|------|--------|--------|
| `dashboard_snapshot_build_duration_seconds` | Histogram | — | p99 < 5s |
| `dashboard_snapshot_publish_duration_seconds` | Histogram | — | p99 < 1s |
| `dashboard_snapshot_epoch` | Gauge | — | Monotonic |
| `dashboard_snapshot_version` | Gauge | — | Monotonic within epoch |
| `dashboard_snapshot_age_seconds` | Gauge | — | < 300s (alert) |
| `dashboard_snapshot_write_errors_total` | Counter | error_type | 0 |
| `dashboard_refresh_requests_total` | Counter | reason (cache-miss, manual, poll) | — |
| `dashboard_refresh_coalesced_total` | Counter | — | — |

### 6. Health Check
**Endpoint**: `GET /health/dashboard-snapshot`
```json
{
  "status": "healthy",
  "lastSnapshotEpoch": 1,
  "lastSnapshotVersion": 42,
  "lastSnapshotAt": "2026-10-27T18:00:00Z",
  "snapshotAgeSeconds": 120,
  "redisConnected": true,
  "leaseHeld": true
}
```
- **Unhealthy if**: snapshot age > 600s, Redis disconnected, version not increasing, lease lost

## Exit Gate (Measurable Thresholds)

| Criterion | Threshold | Measurement Window |
|-----------|-----------|-------------------|
| Snapshot parity (field-level vs legacy API) | ≥ 99.9% | 24h production |
| Snapshot write success rate | 100% (0 errors) | 24h production |
| Version monotonicity | No decreases, no gaps > 1 within epoch | 24h production |
| Epoch stability | No unexpected increments | 24h production |
| Snapshot age (max) | < 300s (5 min) | Continuous |
| Refresh latency (request → notification) | p99 < 10s | 24h production |
| Empty-cache rebuild test | Passes (snapshot rebuilt, epoch/version increments) | Staging + 1 production test |

**Parity Measurement**:
- Shadow compare: On each legacy API request, also read Redis snapshot, deep-diff
- Log mismatches with path, legacy value, redis value
- Alert if mismatch rate > 0.1%

## Rollback Procedure

1. **Feature flag**: `DASHBOARD_SNAPSHOT_PUBLISH_ENABLED=false` (env var)
2. **Effect**: `publish_snapshot()` becomes no-op; `refresh_and_publish()` still builds but doesn't write
3. **Verification**: Confirm Redis key stops updating, version stops incrementing
4. **Consumer impact**: None (consumers unchanged in Phase 1)
5. **Re-enable**: Set flag `true`, next trigger publishes fresh snapshot

## Deployment Steps

1. **Staging**:
   - Deploy with flag `false`
   - Verify health check, metrics, Lua script works
   - Run empty-cache test: `FLUSHDB`, trigger refresh, verify snapshot appears with epoch=1, version=1
   - Run parity test: compare 1000 requests vs legacy

2. **Production (canary)**:
   - Deploy to 1 instance with flag `true`
   - Monitor metrics for 30 min
   - Verify parity on canary instance

3. **Production (full)**:
   - Enable flag on all instances
   - Monitor for 2h
   - Confirm exit gate thresholds met

## Dependencies
- Redis Lua script registered (idempotent)
- JSON schema published to schema registry (or bundled)
- Pydantic model `DashboardSnapshot` generated from schema
- Feature flag infrastructure available

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Redis unavailable | Circuit breaker: log error, don't crash request path; snapshot age alert fires |
| Version gap (crash mid-increment) | Version from `INCR` is atomic; snapshot version = Redis version; no gap possible |
| Large snapshot (>512KB) | Monitor size; if needed, optimize (future) |
| Coalesced refresh storm | 500ms debounce + max 1 refresh per 10s |
| Schema drift | CI test: validate generated snapshot against schema on every build |
| Out-of-order writes | Lua script CAS on (epoch, version) prevents stale overwrites |
| Lease loss during Phase 1 | `back-end` is single instance; lease auto-renewed; if lost, log alert |

## Test Checklist

- [ ] Unit: `build_snapshot()` matches schema
- [ ] Unit: `publish_snapshot()` calls Lua script with correct args (lease token, epoch, version)
- [ ] Unit: Lua script rejects stale epoch/version, accepts valid
- [ ] Integration: Full refresh cycle (startup → snapshot → notification)
- [ ] Integration: Cache miss → HTTP refresh request → notification → snapshot read
- [ ] Integration: Coalesced refresh (10 rapid requests → 1 refresh)
- [ ] Integration: Epoch change handling (simulate FLUSHDB, verify consumers accept epoch=2, version=1)
- [ ] Load: 100 concurrent refresh requests → 1 refresh, no errors
- [ ] Chaos: Redis down during publish → error logged, no crash, alert fires
- [ ] Chaos: Redis down during read → cache miss path works
- [ ] Parity: 10k production requests shadow-compared, mismatch rate < 0.1%