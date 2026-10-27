# Phase 2 Spec: App Back End Reads from Redis (Shadow Mode)

## Objective
Move the app back end to read dashboard data from Redis snapshots, initially in shadow/dark mode comparing against legacy calculations without returning new values to clients.

## Scope
- **Consumer**: `app-back-end` (mobile API + public pages)
- **Producer**: Existing `back-end` (unchanged from Phase 1)
- **Data**: Same `DashboardSnapshot` v1 schema
- **Redis**: Per `redis-conventions.md`

## Deliverables

### 1. Redis Snapshot Client
**Location**: `app-back-end/app/clients/dashboard_snapshot_client.py` (new)

```python
class DashboardSnapshotClient:
    def __init__(self, redis: Redis, scope: str = "global"): ...
    
    async def start(self) -> None:
        """Subscribe, load initial snapshot, start reconciliation loop."""
    
    async def stop(self) -> None: ...
    
    def get_snapshot(self) -> DashboardSnapshot | None:
        """Return current local snapshot (never blocks)."""
    
    def get_site(self, site_id: str) -> SiteSnapshot | None: ...
    
    def get_totals(self) -> TotalsSnapshot | None: ...
    
    def get_outage_schedule(self, site_id: str) -> OutageScheduleSnapshot | None: ...
    
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
- On notification: if `version > local_version`, `GET` snapshot key, update local
- On reconnect: re-subscribe, `GET` snapshot key, update if newer
- Periodic reconciliation: every 60s `GET` snapshot key, compare version
- On cache miss (local snapshot is None): publish refresh request, wait for notification (max 5s), then `GET`

### 2. Shadow Comparison Middleware
**Location**: `app-back-end/app/middleware/shadow_compare.py` (new)

```python
async def shadow_compare_middleware(request: Request, call_next):
    # 1. Call legacy endpoint handler (existing logic)
    legacy_response = await call_next(request)
    
    # 2. If dashboard-related endpoint, also read from Redis
    if is_dashboard_endpoint(request):
        redis_snapshot = snapshot_client.get_snapshot()
        if redis_snapshot:
            legacy_data = extract_dashboard_data(legacy_response)
            redis_data = extract_dashboard_data(redis_snapshot)
            diff = deep_diff(legacy_data, redis_data)
            
            if diff:
                metrics.increment('shadow.parity.mismatch', 
                    tags={'path': diff.path, 'endpoint': request.url.path})
                logger.warning(
                    'Shadow parity mismatch',
                    extra={'path': diff.path, 'legacy': diff.legacy, 'redis': diff.redis}
                )
            
            # Optional: add shadow header for debugging
            legacy_response.headers['X-Shadow-Version'] = str(snapshot_client.version)
            legacy_response.headers['X-Shadow-Stale'] = str(snapshot_client.is_stale).lower()
    
    return legacy_response
```

**Endpoints covered**:
- `GET /api/v1/dashboard` (mobile)
- `GET /api/v1/sites/{site_id}` (mobile)
- `GET /api/v1/outages/{site_id}` (mobile)
- Public page dashboard endpoints

### 3. Feature Flag
**Flag**: `APP_BACKEND_REDIS_DASHBOARD_ENABLED` (default: `false`)

| Value | Behavior |
|-------|----------|
| `false` | Legacy calculation only; shadow comparison runs but results discarded |
| `true` | Redis snapshot used for response; legacy calculation retained as fallback |

**Rollout**: Gradual (10% → 50% → 100% of app-back-end instances)

### 4. Metrics (Additional to Phase 1)
| Metric | Type | Labels | Target |
|--------|------|--------|--------|
| `shadow.parity.mismatch` | Counter | path, endpoint | < 0.1% of requests |
| `shadow.parity.latency_delta_ms` | Histogram | endpoint | p99 < 50ms |
| `redis_snapshot_version_lag` | Gauge | — | ≤ 1 |
| `redis_snapshot_age_seconds` | Gauge | — | < 300s |
| `redis_snapshot_reconciliation_total` | Counter | result (ok, stale, error) | — |
| `redis_snapshot_cache_miss_total` | Counter | — | 0 after warmup |

### 5. Health Check
**Endpoint**: `GET /health/redis-dashboard`
```json
{
  "status": "healthy",
  "localVersion": 42,
  "redisVersion": 42,
  "versionLag": 0,
  "snapshotAgeSeconds": 45,
  "isStale": false,
  "subscribed": true,
  "lastNotificationAt": "2026-10-27T18:05:00Z"
}
```
- **Unhealthy if**: version lag > 1 for > 60s, not subscribed, snapshot age > 600s

## Exit Gate (Measurable Thresholds)

| Criterion | Threshold | Measurement Window |
|-----------|-----------|-------------------|
| Shadow parity (field-level) | ≥ 99.9% | 24h production at 100% rollout |
| p99 latency delta (Redis vs legacy) | < 50ms | 24h production |
| Freshness delta (snapshot age vs legacy) | < 5s | 24h production |
| Error rate (Redis path) | < 0.1% | 24h production |
| Version lag | ≤ 1 for 99.9% of time | 24h production |
| Restart/reconnect test | Recovers within 2s, no data loss | Staging + 1 production test |
| Mobile API contract compatibility | 100% (no breaking changes) | Contract test suite |

## Rollback Procedure

1. **Immediate**: Set `APP_BACKEND_REDIS_DASHBOARD_ENABLED=false`
2. **Effect**: All responses served from legacy calculation; shadow comparison continues
3. **Verification**: Confirm error rate drops, latency returns to baseline
4. **Investigation**: Analyze parity mismatches, Redis connectivity, version lag
5. **Re-enable**: After fix, gradual rollout again

## Deployment Steps

1. **Staging**:
   - Deploy with flag `false`
   - Verify shadow comparison runs, metrics emit, no crashes
   - Run restart test: kill app-back-end, restart, verify snapshot loaded
   - Run reconnect test: restart Redis, verify re-subscription works

2. **Production (shadow only)**:
   - Deploy to all instances with flag `false`
   - Monitor shadow parity for 24h
   - Alert on mismatch rate > 0.1%

3. **Production (gradual enable)**:
   - Enable flag on 10% of instances
   - Monitor for 2h: error rate, latency, parity
   - Increase to 50%, then 100%
   - At each step: verify exit gate thresholds

## Dependencies
- Phase 1 complete (snapshots publishing, version monotonic)
- Redis client library with Pub/Sub support
- Feature flag infrastructure
- Deep-diff utility (e.g., `deepdiff` package)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Redis connection storm on deploy | Staggered startup: random 0-30s delay before `start()` |
| Stale snapshot served | `is_stale` check: if stale, log warning, fall back to legacy (when flag enabled) |
| Version lag during high load | Reconciliation every 60s + notification-driven updates |
| Mobile app breaks | Contract test suite runs in CI; mobile API shape unchanged |
| Memory leak in local snapshot | Single snapshot object, replaced atomically; no accumulation |

## Test Checklist

- [ ] Unit: Client loads snapshot, updates on notification, handles reconnect
- [ ] Unit: Cache miss → refresh request → notification → snapshot loaded
- [ ] Unit: Reconciliation detects stale local version
- [ ] Integration: Shadow middleware compares correctly, emits metrics
- [ ] Integration: Feature flag toggles behavior correctly
- [ ] Load: 1000 concurrent requests, shadow comparison adds < 5ms p99
- [ ] Chaos: Redis down → client serves stale (with warning) or falls back
- [ ] Chaos: Redis flapping → reconnection works, no duplicate subscriptions
- [ ] Parity: 24h production shadow run, mismatch rate < 0.1%
- [ ] Contract: Mobile API test suite passes with flag enabled