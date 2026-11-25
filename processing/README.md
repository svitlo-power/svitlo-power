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
| `processing_lease_acquired_total` | Counter | Lease acquisitions |
| `processing_lease_lost_total` | Counter | Lease losses |
| `processing_job_executions_total` | Counter | Scheduled job outcomes |

`processing_shadow_parity_rate` has no numeric value until the first comparison
completes, and is set back to `NaN` whenever a comparison is skipped (no
baseline yet, or the two snapshots are further apart than
`PROCESSING_COMPARISON_MAX_SKEW_SECONDS`). `0` therefore only ever means a real
0% parity, so a `parity < X` alert cannot fire on a skipped comparison; use
`processing_shadow_last_comparison_timestamp_seconds` to tell "stale" from
"healthy".

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