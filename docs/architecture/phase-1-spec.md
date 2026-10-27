# Phase 1 Spec: Publish Dashboard Snapshots to Redis

## Objective
Deploy Redis snapshot writes from the existing back end while it remains the sole dashboard calculator and authoritative producer. No consumer changes in this phase.

## Scope
- **Producer**: Existing `back-end` (Python/FastAPI)
- **Consumers**: Unchanged (app-back-end, admin-back-end, sse-back-end)
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
```

**Responsibilities**:
- Fetch data from existing internal services (Deye client, station repo, outage schedule repo)
- Transform to `DashboardSnapshot` Pydantic model (validates against JSON schema)
- Atomic write to Redis via Lua script
- Increment monotonic version (stored in Redis `meta:dashboard:version` or derived from snapshot)

### 2. Version Management
- **Version key**: `meta:dashboard:version` (Redis string, integer)
- **Increment**: `INCR meta:dashboard:version` → use as `snapshot.version`
- **Initial value**: Set on deploy (read current max from any existing snapshot or start at 1)

### 3. Trigger Points
| Trigger | Action |
|---------|--------|
| Back-end startup | `refresh_and_publish()` |
| Deye poll completes (new measurements) | `refresh_and_publish()` |
| Station sync completes | `refresh_and_publish()` |
| Outage schedule CRUD | `refresh_and_publish()` |
| Manual API `POST /admin/dashboard/refresh` | `refresh_and_publish()` |
| Cache miss (BFF publishes refresh request) | Coalesced: debounce 500ms, single refresh |

### 4. Coalesced Refresh on Cache Miss
- Back-end subscribes to `cache:dashboard:v1:refresh-requests`
- On message: schedule refresh if not already scheduled within 500ms
- Use asyncio `Event` or similar to coalesce multiple requests

### 5. Monitoring & Metrics
| Metric | Type | Labels | Target |
|--------|------|--------|--------|
| `dashboard_snapshot_build_duration_seconds` | Histogram | — | p99 < 5s |
| `dashboard_snapshot_publish_duration_seconds` | Histogram | — | p99 < 1s |
| `dashboard_snapshot_version` | Gauge | — | Monotonic increasing |
| `dashboard_snapshot_age_seconds` | Gauge | scope | < 300s (alert) |
| `dashboard_snapshot_write_errors_total` | Counter | error_type | 0 |
| `dashboard_refresh_requests_total` | Counter | reason (cache-miss, manual, poll) | — |
| `dashboard_refresh_coalesced_total` | Counter | — | — |

### 6. Health Check
**Endpoint**: `GET /health/dashboard-snapshot`
```json
{
  "status": "healthy",
  "lastSnapshotVersion": 42,
  "lastSnapshotAt": "2026-10-27T18:00:00Z",
  "snapshotAgeSeconds": 120,
  "redisConnected": true
}
```
- **Unhealthy if**: snapshot age > 600s, Redis disconnected, version not increasing

## Exit Gate (Measurable Thresholds)

| Criterion | Threshold | Measurement Window |
|-----------|-----------|-------------------|
| Snapshot parity (field-level) | ≥ 99.9% vs legacy API response | 24h production |
| Snapshot write success rate | 100% (0 errors) | 24h production |
| Version monotonicity | No decreases, no gaps > 1 | 24h production |
| Snapshot age (max) | < 300s (5 min) | Continuous |
| Refresh latency (request → notification) | p99 < 10s | 24h production |
| Empty-cache rebuild test | Passes (snapshot rebuilt, version increments) | Staging + 1 production test |

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
   - Run empty-cache test: `FLUSHDB`, trigger refresh, verify snapshot appears
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
| Large snapshot (>512KB) | Monitor size; if needed, split by tenant (Phase 2+) |
| Coalesced refresh storm | 500ms debounce + max 1 refresh per 10s per scope |
| Schema drift | CI test: validate generated snapshot against schema on every build |

## Test Checklist

- [ ] Unit: `build_snapshot()` matches schema
- [ ] Unit: `publish_snapshot()` calls Lua script with correct args
- [ ] Integration: Full refresh cycle (startup → snapshot → notification)
- [ ] Integration: Cache miss → refresh request → notification → snapshot read
- [ ] Integration: Coalesced refresh (10 rapid requests → 1 refresh)
- [ ] Load: 100 concurrent refresh requests → 1 refresh, no errors
- [ ] Chaos: Redis down during publish → error logged, no crash, alert fires
- [ ] Chaos: Redis down during read → cache miss path works
- [ ] Parity: 10k production requests shadow-compared, mismatch rate < 0.1%