# Phase 2 Spec: App Back End Reads from Redis

## Objective
Move the `app-back-end` to read dashboard data from Redis snapshots. Keep the
snapshot client current through Redis invalidations and periodic reconciliation;
do not recalculate legacy dashboard responses for shadow comparisons.

## Scope
- **Consumer**: `app-back-end` (mobile API + public pages)
- **Producer**: Existing `back-end` (unchanged from Phase 1)
- **Data**: Same `DashboardSnapshot` v1 schema
- **Redis**: Per `redis-conventions.md`

## Deliverables

### 1. Redis Snapshot Client
**Location**: `shared/python/shared/services/dashboard_snapshot/client.py` (new)

The snapshot schema and client live in `shared` so other services can consume the
same versioned snapshot contract without duplicating Redis subscription logic.

```python
class DashboardSnapshotClient:
    def __init__(self, redis: Redis): ...
    
    async def start(self) -> None:
        """Subscribe, load initial snapshot, start reconciliation loop."""
    
    async def stop(self) -> None: ...
    
    def get_snapshot(self) -> DashboardSnapshot | None:
        """Return current local snapshot (never blocks)."""
    
    def get_buildings(self) -> list[BuildingSnapshot]:
        """Return buildings from snapshot."""
    
    def get_building(self, building_id: str) -> BuildingSnapshot | None: ...
    
    def get_config(self) -> ConfigSnapshot | None: ...
    
    def get_outages_schedule(self, queue: str) -> UnitSchedule | None: ...
    
    @property
    def epoch(self) -> int: ...
    
    @property
    def version(self) -> int: ...
    
    @property
    def is_stale(self) -> bool:
        """True if snapshot age > stale_threshold (configurable, default 300s)."""
    
    @property
    def age_seconds(self) -> float: ...
```

**Behavior**:
- Subscribe to `cache:dashboard:v1:invalidations` on `start()`
- On notification: if `(epoch, version) > local`, `GET` snapshot key, update local
- On reconnect: re-subscribe, `GET` snapshot key, update if newer
- Periodic reconciliation: every 60s `GET` snapshot key, compare (epoch, version)
- On cache miss (local snapshot is None): call HTTP refresh endpoint on producer, wait for notification (max 5s), then `GET`

### 2. Feature Flag
**Flag**: `APP_BACKEND_REDIS_DASHBOARD_ENABLED` (default: `false`), together
with `FEATURE_DASHBOARD_SNAPSHOT_PUBLISH=true`.

The back-end feature `BACKEND_REDIS_DASHBOARD_ENABLED` (environment variable
`FEATURE_BACKEND_REDIS_DASHBOARD_ENABLED`) controls whether the public UI uses
post-publish `dashboard_updated` events; it does not switch admin back-end
routes to Redis. `GET /api/app/features` exposes this as
`dashboardUpdatedEventEnabled`, which is true only when snapshot publishing is
enabled and `FEATURE_DEYE_POLLING_PROCESSING` is disabled. The UI otherwise
uses the legacy event set. The producer emits `dashboard_updated` only after a
snapshot write succeeds. If such events stop, the UI retries data reads every
five minutes; after the snapshot becomes stale, API routes fall back to legacy
calculations.

| Value | Behavior |
|-------|----------|
| `false` | Legacy calculation serves responses |
| `true` | Fresh Redis snapshots serve responses; legacy calculation is the fallback when the snapshot is missing or stale |

**Rollout**: Gradual (10% → 50% → 100% of app-back-end instances)

### 3. Metrics (Additional to Phase 1)
| Metric | Type | Labels | Target |
|--------|------|--------|--------|
| `redis_snapshot_version_lag` | Gauge | — | ≤ 1 |
| `redis_snapshot_age_seconds` | Gauge | — | < 300s |
| `redis_snapshot_reconciliation_total` | Counter | result (ok, stale, miss, error) | — |
| `redis_snapshot_cache_miss_total` | Counter | — | 0 after warmup |

The consumer exposes `GET /health/redis-dashboard`, including local/Redis epoch
and version, lag, age, subscription state, and the most recent invalidation time.

### 4. Health Check
**Endpoint**: `GET /health/redis-dashboard`
```json
{
  "status": "healthy",
  "localEpoch": 1,
  "localVersion": 42,
  "redisEpoch": 1,
  "redisVersion": 42,
  "versionLag": 0,
  "snapshotAgeSeconds": 45,
  "isStale": false,
  "subscribed": true,
  "lastNotificationAt": "2026-10-27T18:05:00Z"
}
```
- **Unhealthy if**: version lag > 1 for > 60s, not subscribed, snapshot age > 600s, epoch mismatch

## Exit Gate (Measurable Thresholds)

| Criterion | Threshold | Measurement Window |
|-----------|-----------|-------------------|
| Error rate (Redis path) | < 0.1% | 24h production |
| Version lag | ≤ 1 for 99.9% of time | 24h production |
| Restart/reconnect test | Recovers within 2s, no data loss | Staging + 1 production test |
| Mobile API contract compatibility | 100% (no breaking changes) | Contract test suite |

## Rollback Procedure

1. **Immediate**: Set `APP_BACKEND_REDIS_DASHBOARD_ENABLED=false`
2. **Effect**: Responses use the legacy calculation; no shadow comparison runs
3. **Verification**: Confirm error rate drops, latency returns to baseline
4. **Investigation**: Analyze Redis connectivity, reconciliation outcomes, and version lag
5. **Re-enable**: After fix, gradual rollout again

## Deployment Steps

1. **Staging**:
   - Deploy with flag `false`
   - Verify snapshot reconciliation metrics emit and no crashes
   - Run restart test: kill app-back-end, restart, verify snapshot loaded
   - Run reconnect test: restart Redis, verify re-subscription works
   - Test epoch change: `FLUSHDB`, verify client accepts new epoch

2. **Production (Redis reads disabled)**:
   - Deploy to all instances with flag `false`
   - Verify legacy fallback and snapshot client health

3. **Production (gradual enable)**:
   - Enable flag on 10% of instances
   - Monitor for 2h: error rate, latency, and snapshot freshness
   - Increase to 50%, then 100%
   - At each step: verify exit gate thresholds

## Dependencies
- Phase 1 complete (snapshots publishing, epoch/version monotonic)
- Redis client library with Pub/Sub support
- Feature flag infrastructure

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Redis connection storm on deploy | Staggered startup: readiness gate waits for initial snapshot load |
| Stale snapshot served | `is_stale` check: if stale, log warning, fall back to legacy (when flag enabled) |
| Version lag during high load | Reconciliation every 60s + notification-driven updates |
| Mobile app breaks | Contract test suite runs in CI; mobile API shape unchanged |
| Memory leak in local snapshot | Single snapshot object, replaced atomically; no accumulation |

## Test Checklist

- [ ] Unit: Client loads snapshot, updates on notification, handles reconnect
- [ ] Unit: Cache miss → HTTP refresh request → notification → snapshot loaded
- [ ] Unit: Reconciliation detects stale local (epoch, version)
- [ ] Unit: Epoch change handling (accepts lower version when epoch increases)
- [ ] Integration: Feature flag toggles behavior correctly
- [ ] Load: 1000 concurrent requests, shadow sampling adds negligible overhead
- [ ] Chaos: Redis down → client serves stale (with warning) or falls back
- [ ] Chaos: Redis flapping → reconnection works, no duplicate subscriptions
- [ ] Contract: Mobile API test suite passes with flag enabled