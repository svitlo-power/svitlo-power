# Phase 0 Rollback Procedures

This document describes the rollback procedures for Phase 0 instrumentation and feature flags.

## Feature Flags

All Phase 0 feature flags are controlled via environment variables:

| Feature Flag | Environment Variable | Default |
|--------------|---------------------|---------|
| Dashboard Snapshot Publish | `FEATURE_DASHBOARD_SNAPSHOT_PUBLISH` | `false` |
| App Backend Redis Reads | `FEATURE_APP_BACKEND_REDIS_READS` | `false` |
| Backend SSE Redis | `FEATURE_BACKEND_SSE_REDIS` | `false` |
| App Backend SSE Redis | `FEATURE_APP_BACKEND_SSE_REDIS` | `false` |
| Processing Shadow Mode | `FEATURE_PROCESSING_SHADOW_MODE` | `false` |
| Processing Cutover | `FEATURE_PROCESSING_CUTOVER` | `false` |
| Message Preview Processing | `FEATURE_MESSAGE_PREVIEW_PROCESSING` | `false` |
| Admin CRUD Processing | `FEATURE_ADMIN_CRUD_PROCESSING` | `false` |
| Deye Polling Processing | `FEATURE_DEYE_POLLING_PROCESSING` | `false` |
| Cleanup Processing | `FEATURE_CLEANUP_PROCESSING` | `false` |
| Message Delivery Processing | `FEATURE_MESSAGE_DELIVERY_PROCESSING` | `false` |
| Identity Service | `FEATURE_IDENTITY_SERVICE` | `false` |
| Public Admin Separation | `FEATURE_PUBLIC_ADMIN_SEPARATION` | `false` |

## Rollback Procedures

### 1. Disable All New Instrumentation

To completely disable all Phase 0 instrumentation and return to pre-Phase 0 behavior:

```bash
# Set all feature flags to false
export FEATURE_DASHBOARD_SNAPSHOT_PUBLISH=false
export FEATURE_APP_BACKEND_REDIS_READS=false
export FEATURE_BACKEND_SSE_REDIS=false
export FEATURE_APP_BACKEND_SSE_REDIS=false
export FEATURE_PROCESSING_SHADOW_MODE=false
export FEATURE_PROCESSING_CUTOVER=false
export FEATURE_MESSAGE_PREVIEW_PROCESSING=false
export FEATURE_ADMIN_CRUD_PROCESSING=false
export FEATURE_DEYE_POLLING_PROCESSING=false
export FEATURE_CLEANUP_PROCESSING=false
export FEATURE_MESSAGE_DELIVERY_PROCESSING=false
export FEATURE_IDENTITY_SERVICE=false
export FEATURE_PUBLIC_ADMIN_SEPARATION=false

# Restart all services
docker-compose restart back-end app-back-end sse-back-end grid-reporter
```

### 2. Selective Rollback

#### Dashboard Snapshot Publishing (Phase 1)
```bash
export FEATURE_DASHBOARD_SNAPSHOT_PUBLISH=false
docker-compose restart back-end
```
**Effect**: Back-end stops publishing snapshots to Redis. Consumers (app-back-end, sse-back-end) continue using existing data paths.

#### App Backend Redis Reads (Phase 2)
```bash
export FEATURE_APP_BACKEND_REDIS_READS=false
docker-compose restart app-back-end
```
**Effect**: App-back-end returns 503 for dashboard endpoints. Mobile app falls back to legacy behavior (if implemented) or shows error.

#### SSE Redis Migration (Phase 3)
```bash
export FEATURE_BACKEND_SSE_REDIS=false
export FEATURE_APP_BACKEND_SSE_REDIS=false
docker-compose restart back-end sse-back-end app-back-end
```
**Effect**: SSE connections route back to legacy sse-back-end service.

#### Scheduled Job Ownership (Phase 6)
```bash
# Disable specific capability migrations
export FEATURE_DEYE_POLLING_PROCESSING=false
export FEATURE_CLEANUP_PROCESSING=false
export FEATURE_MESSAGE_DELIVERY_PROCESSING=false
docker-compose restart back-end
```
**Effect**: Back-end resumes ownership of scheduled jobs.

### 3. Verification Steps

After rollback, verify:

1. **Health checks pass**:
   ```bash
   curl http://back-end/health
   curl http://app-back-end/health
   curl http://sse-back-end/health
   curl http://grid-reporter:8081/health
   ```

2. **Dashboard API works**:
   ```bash
   curl http://back-end/api/dashboard/buildings
   curl http://back-end/api/dashboard/config
   ```

3. **SSE connections work**:
   ```bash
   # Test SSE endpoint
   curl -N http://sse-back-end/api/events
   ```

4. **Scheduled jobs running**:
   - Check logs for job execution
   - Verify Deye polling, outage schedule updates, cleanup jobs

5. **Metrics show no new activity**:
   - Dashboard snapshot metrics should stop updating
   - Redis operation metrics should return to baseline
   - SSE connection metrics should show legacy patterns

### 4. Emergency Rollback (Production)

If issues are detected in production:

1. **Immediate** (30 seconds):
   ```bash
   # Disable all feature flags via environment
   kubectl set env deployment/back-end FEATURE_DASHBOARD_SNAPSHOT_PUBLISH=false
   kubectl set env deployment/app-back-end FEATURE_APP_BACKEND_REDIS_READS=false
   kubectl set env deployment/sse-back-end FEATURE_BACKEND_SSE_REDIS=false
   kubectl set env deployment/sse-back-end FEATURE_APP_BACKEND_SSE_REDIS=false
   kubectl rollout restart deployment/back-end deployment/app-back-end deployment/sse-back-end
   ```

2. **Verify** (2 minutes):
   - Check health endpoints
   - Verify user-facing functionality
   - Check error rates in monitoring

3. **Investigate** (ongoing):
   - Review logs for error patterns
   - Check metrics for anomalies
   - Coordinate with team for root cause analysis

### 5. Rollback Checklist

- [ ] All feature flags set to `false`
- [ ] All services restarted
- [ ] Health checks passing
- [ ] Dashboard API responding correctly
- [ ] SSE connections established
- [ ] Scheduled jobs executing
- [ ] Error rates at baseline
- [ ] Latency at baseline
- [ ] Team notified of rollback
- [ ] Incident documented

## Monitoring During Rollback

Watch these key metrics:

| Metric | Expected Behavior After Rollback |
|--------|----------------------------------|
| `dashboard_snapshot_write_errors_total` | Stops increasing |
| `dashboard_snapshot_age_seconds` | Stops updating (or N/A) |
| `redis_operation_errors_total` | Returns to baseline |
| `sse_connections_active` | Returns to legacy pattern |
| `job_execution_success_total` | Continues for back-end jobs |
| `job_execution_failure_total` | No increase |

## Contact

For rollback assistance, contact the platform team or on-call engineer.