# svitlo-power-processing

NestJS service that builds the versioned `DashboardSnapshot v1` from MongoDB and
Redis. Phase 4 of the migration runs it in **shadow mode**: it writes only to
isolated `shadow:`-prefixed Redis keys and compares its output with the legacy
Python producer, which stays authoritative.

## What it does

1. Reads buildings, stations, measurements, reporter observations and settings
   from MongoDB through Mongoose repositories.
2. Reads the cached Yasno outage schedules from the Redis `outages_schedule`
   hash.
3. Builds a `DashboardSnapshot v1` identical in shape to the legacy producer's.
4. Validates the snapshot against the published contract.
5. Publishes it to the `shadow:` key namespace under a Redis lease.
6. Compares it field by field with the production snapshot and exports parity
   metrics.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8100` | HTTP port (health + refresh trigger) |
| `METRICS_PORT` | `9095` | Prometheus scrape port |
| `MONGO_URI` | `mongodb://127.0.0.1:27017` | MongoDB connection string |
| `MONGO_DB` | `svitlo-power` | MongoDB database name |
| `REDIS_URI` | `redis://svitlo-power-rds:6379/0` | Redis connection string |
| `FEATURE_PROCESSING_SHADOW_MODE` | `false` | Enables the shadow snapshot flow |
| `FEATURE_PROCESSING_PUBLISH_ENABLED` | `false` | Phase 5 cutover: publish to the production snapshot keys instead of `shadow:` keys (requires shadow mode) |
| `FEATURE_PROCESSING_CUTOVER` | back-end | `false` | Phase 5: legacy back-end publishes refresh hints instead of snapshots |
| `PROCESSING_RECONCILIATION_INTERVAL_SECONDS` | `300` | Safety-net reconciliation cadence |
| `PROCESSING_REFRESH_COALESCE_MS` | `500` | Refresh debounce window |
| `PROCESSING_COMPARISON_MAX_SKEW_SECONDS` | `120` | Maximum tolerated age gap between the compared snapshots |
| `PROCESSING_LEASE_TTL_SECONDS` | `30` | Shadow lease TTL |
| `PROCESSING_LEASE_RENEW_INTERVAL_SECONDS` | `10` | Shadow lease renewal cadence |
| `DEYE_REPORT_INTERVAL` | `300` | Reporter cadence used for the assumed-offline threshold |
| `DEYE_ASSUMED_OFFLINE_REPORTS` | `2` | Missed reports before a station counts as offline |
| `PROCESSING_LOG_LEVEL` | `info` | Pino log level |

## Endpoints

| Route | Purpose |
|---|---|
| `GET /health/live` | Liveness probe |
| `GET /health/ready` | Readiness probe (Redis + last build) |
| `GET /health` | Detailed health report |
| `POST /internal/v1/snapshots/refresh` | Coalesced refresh trigger |

## Refresh triggers

Snapshots are rebuilt from three sources, all of which fold into one build
through `RefreshCoordinator`:

| Source | Mechanism |
|---|---|
| BFF cache miss / admin action | `POST /internal/v1/snapshots/refresh` |
| Legacy back-end mutation | Redis pub/sub on `processing:triggers:snapshot-refresh` |
| Safety net | Reconciliation cron (`PROCESSING_RECONCILIATION_INTERVAL_SECONDS`) |

The pub/sub path exists because the legacy back-end used to call
`refresh_and_publish()` inline from about a dozen in-process sites; after the
cutover those calls cannot reach Processing. The back-end publishes a hint:

```json
{ "reason": "buildings-change", "changedSections": ["buildings"], "source": "back-end" }
```

The payload is a hint, never state: Processing re-reads MongoDB and rebuilds.
Delivery is at least once, publishing is fire and forget, and bursts are
coalesced, so a slow Processing cannot fail an admin write.

### This path is transitional

The pub/sub hop exists only because the mutation and the rebuild live in
different processes during Phase 5. Phase 6.2 moves admin CRUD into Processing
and Phase 6.3 moves the schedulers, so the mutation and the rebuild end up in
the same process and the notification is no longer needed at all: the mutation
path calls `RefreshCoordinator.request()` directly, exactly as the legacy
back-end called `refresh_and_publish()` inline.

The channel is therefore **deleted in Phase 6**, not migrated onto a general
event bus. Until then it is the only mechanism that keeps snapshot age under the
60 s exit gate while the legacy back-end still owns the writes.

## Shadow isolation

Every key the service writes is derived from the `shadow:` prefix:

```
shadow:cache:dashboard:v1:global
shadow:cache:dashboard:v1:invalidations
shadow:lock:processing:dashboard:v1
shadow:meta:dashboard:epoch
shadow:meta:dashboard:version:next
shadow:meta:dashboard:version
```

The production snapshot key is only ever read, for comparison. The legacy
producer keeps publishing to the production keys until the Phase 5 cutover.

### Phase 5 cutover

Setting `FEATURE_PROCESSING_PUBLISH_ENABLED=true` (with shadow mode still on)
switches the destination from the `shadow:` namespace to the production keys:

```
cache:dashboard:v1:global
cache:dashboard:v1:invalidations
lock:processing:dashboard:v1
meta:dashboard:epoch
meta:dashboard:version:next
meta:dashboard:version
```

The write is the same Lua script the legacy producer uses — lease fencing plus
compare-and-set on `(epoch, committed version)` — so exactly one producer can
ever write. Rollback is the reverse: set the flag back to `false`, let the
processor release the lease, then re-enable
`FEATURE_DASHBOARD_SNAPSHOT_PUBLISH` on the legacy back-end.

The service is a read-only MongoDB consumer: `autoIndex` and `autoCreate` are
disabled, so the indexes declared on the shared schemas are never built against
the Python-owned collections.

## Metrics

The `dashboard_snapshot_*` and `dashboard_refresh_*` metric names are shared
with the legacy Python producer, so every panel and alert must filter on
`job="svitlo-power-processing"` until the cutover. The shadow-only metrics carry
a `processing_shadow_` prefix and never collide:

| Metric | Type | Purpose |
|---|---|---|
| `processing_shadow_parity_rate` | Gauge | Field-level parity vs production |
| `processing_shadow_mismatch_total` | Counter | Mismatches by `section`/`field` |
| `processing_shadow_comparisons_total` | Counter | Comparisons by outcome |
| `processing_shadow_comparison_skew_seconds` | Gauge | Age gap between the compared snapshots |
| `processing_shadow_last_comparison_timestamp_seconds` | Gauge | Unix time of the last completed comparison, or of process start while shadow mode is on |
| `processing_shadow_mode_enabled` | Gauge | 1 when shadow mode is on for this instance |
| `processing_shadow_lease_held` | Gauge | 1 while this instance holds the shadow lease |
| `processing_publish_enabled` | Gauge | 1 when this instance publishes to the production snapshot keys |
| `processing_refresh_notifications_total` | Counter | "Data changed" notifications received, by `reason` |
| `processing_refresh_notification_errors_total` | Counter | Notifications whose rebuild failed, by `reason` |
| `processing_refresh_acknowledged_version` | Gauge | Snapshot version that acknowledged the last notification |
| `processing_refresh_acknowledged_timestamp_seconds` | Gauge | Unix time of the last acknowledged notification |
| `processing_lease_acquired_total` | Counter | Lease acquisitions |
| `processing_lease_lost_total` | Counter | Lease losses |
| `processing_job_executions_total` | Counter | Scheduled job outcomes |

`processing_shadow_parity_rate` has no numeric value until the first comparison
completes, and is set back to `NaN` whenever a comparison is skipped (no
baseline yet, the two snapshots are further apart than
`PROCESSING_COMPARISON_MAX_SKEW_SECONDS`, or the cutover is done and Processing
owns the production key). `0` therefore only ever means a real 0% parity, so a
`parity < X` alert cannot fire on a skipped comparison; use
`processing_shadow_last_comparison_timestamp_seconds` to tell "stale" from
"healthy". After the cutover the comparison is always skipped, so parity and the
parity/staleness alerts are meaningless.

Two alerts watch this: `processing-shadow-parity-stale` fires when the lease
holder has not completed a comparison for 15 minutes, and `processing-down`
fires when the target cannot be scraped. The freshness rule is scoped to
instances that are supposed to compare (`processing_shadow_mode_enabled` and
`processing_shadow_lease_held`), so a standby replica or a shadow-mode-off
deployment stays quiet.

## Development

```bash
npm run build -w svitlo-power-processing
npm run lint -w svitlo-power-processing
npm run format:check -w svitlo-power-processing
npm test -w svitlo-power-processing
npm run start:dev -w svitlo-power-processing
```

## Tests

Tests use Node's built-in test runner (`node:test`) with `@nestjs/testing`,
matching `app-back-end`. No Jest.

```bash
npm test -w svitlo-power-processing
```