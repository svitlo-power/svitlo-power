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
| `METRICS_PORT` | `9099` | Prometheus scrape port |
| `MONGO_URI` | `mongodb://127.0.0.1:27017` | MongoDB connection string |
| `MONGO_DB` | `svitlo-power` | MongoDB database name |
| `REDIS_URI` | `redis://svitlo-power-rds:6379/0` | Redis connection string |
| `FEATURE_PROCESSING_SHADOW_MODE` | `false` | Enables the shadow snapshot flow |
| `PROCESSING_RECONCILIATION_INTERVAL_SECONDS` | `300` | Safety-net reconciliation cadence |
| `PROCESSING_REFRESH_COALESCE_MS` | `500` | Refresh debounce window |
| `PROCESSING_LEASE_TTL_SECONDS` | `30` | Shadow lease TTL |
| `PROCESSING_LEASE_RENEW_INTERVAL_SECONDS` | `10` | Shadow lease renewal cadence |
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