# Phase 5 Cutover Runbook

Moves snapshot ownership from the legacy Python `back-end` to
`svitlo-power-processing`. The legacy calculation code stays in place (removed in
Phase 9); only the publish flag moves.

## Flags

| Flag | Owner | Before | After cutover |
|---|---|---|---|
| `FEATURE_DASHBOARD_SNAPSHOT_PUBLISH` | back-end | `true` | `false` |
| `FEATURE_PROCESSING_SHADOW_MODE` | processing | `true` | `true` (unchanged) |
| `FEATURE_PROCESSING_PUBLISH_ENABLED` | processing | `false` | `true` |
| `FEATURE_PROCESSING_CUTOVER` | back-end | `false` | `true` |

`FEATURE_PROCESSING_PUBLISH_ENABLED` requires
`FEATURE_PROCESSING_SHADOW_MODE=true`; the service refuses to start otherwise.

**Every flag change is a restart.** Both services read the flags once at startup
(`FeatureFlags._load_from_env` on the back-end, `registerAs` on Processing), so
each step below is a service restart, not a runtime toggle.

**Which service each flag is set on.** `docker-compose.yml` loads the same
`.env` into every service, so a flag set in `.env` reaches all of them. Set the
producer/trigger flags only where they belong:

| Flag | Set on | Notes |
|---|---|---|
| `FEATURE_DASHBOARD_SNAPSHOT_PUBLISH` | `back-end` | Legacy producer. Must be `false` everywhere else. |
| `FEATURE_PROCESSING_CUTOVER` | `back-end` | Legacy hint publisher. |
| `FEATURE_PROCESSING_PUBLISH_ENABLED` | `processing` | Production producer. |
| `FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS` | both BFFs | Stays `true` across the cutover: reads follow either producer. |

Because the BFF read gate now accepts either producer, the BFFs keep serving the
dashboard from Redis after the cutover without a flag change.

Exactly one producer may hold the lease `lock:processing:dashboard:v1` at any
time. Never enable both publishers.

## Cutover

Order matters: the trigger is enabled **before** the legacy publisher is
disabled, so there is no window with neither a producer nor triggers. While
Processing is still in shadow mode the hints only start shadow builds, so the
trigger path can be verified before the producer moves.

1. **Enable the back-end trigger**
   `FEATURE_PROCESSING_CUTOVER=true` on `back-end`, then restart `back-end`.
   - Mutations now publish hints; Processing (still in shadow mode) rebuilds the
     `shadow:` snapshot. The production snapshot is still owned by the legacy
     producer.
2. **Disable the legacy publisher**
   `FEATURE_DASHBOARD_SNAPSHOT_PUBLISH=false` on `back-end`, then restart
   `back-end`.
3. **Verify the legacy producer stopped** (<= 2 min after the restart)
   - `dashboard_snapshot_version` from `job="svitlo-power-back-end"` stops
     incrementing.
   - `lock:processing:dashboard:v1` is released (`GET` returns nil). This
     depends on a graceful stop; after a crash, wait out the 30 s lease TTL.
4. **Enable the Processing publisher**
   `FEATURE_PROCESSING_PUBLISH_ENABLED=true` on `processing`, then restart
   `processing`.
5. **Repoint the BFF cache-miss refresh at Processing**
   Set `APP_BACKEND_SNAPSHOT_REFRESH_URL` to
   `http://svitlo-power-processing:8100/internal/v1/snapshots/refresh` on both
   BFFs and restart them. Processing guards `/internal` with
   `InternalTokenGuard`, so `INTERNAL_API_TOKEN` must match Processing's
   `INTERNAL_API_TOKEN`. Until this is done the back-end forwards cache misses to
   Processing as hints (the `cache-miss` reason), so the path still works, just
   through one extra hop.
6. **Verify**
   - `processing_publish_enabled` is `1` and the lease holder is `processing-*`.
   - `dashboard_snapshot_version` from `job="svitlo-power-processing"`
     increments **and matches the production key** (`GET meta:dashboard:version`);
     the gauge is also exported for the shadow publisher, so a value that only
     increments is not enough.
   - `cache:dashboard:v1:invalidations` notifications flow to both BFFs.
   - **BFFs still serve from Redis:** each BFF's snapshot-hit metric keeps
     increasing (or `/health/dashboard-snapshot` stays fresh). Reads must not
     fall back to the per-request Mongo path.
   - `processing_refresh_notifications_total` increases while exercising admin
     CRUD, station sync and the outage schedule refresh.
7. **Freshness gate** - `dashboard_snapshot_age_seconds < 60` continuously while
   the triggers above are exercised. The pub/sub path must be the one producing
   the refreshes, not the 300 s reconciliation cron.
8. **Monitor for 30 min** before closing the change.

### After the cutover

- **Parity is meaningless.** Processing now owns the production key, so the
  shadow comparison is skipped and `processing_shadow_parity_rate` is exported
  as `NaN`. The `processing-shadow-parity-stale` alert excludes
  `processing_publish_enabled == 1`, so it stays quiet after the cutover; a
  dedicated `processing-snapshot-freshness` alert watches
  `dashboard_snapshot_age_seconds` on the Processing producer instead.
- **The UI event mode switches off, but per-entity events keep flowing.**
  `dashboardUpdatedEventEnabled` is only set while
  `FEATURE_DASHBOARD_SNAPSHOT_PUBLISH` is on, and only the legacy producer sends
  `dashboard_updated`. After the cutover the front-end falls back to the
  per-entity `dashboard_config_updated` / `buildings_updated` events, which the
  back-end now sends whenever any producer is active (not only the legacy one).
  Sending `dashboard_updated` from Processing is planned for a later phase.

## Rollback (< 2 min)

Every step is a restart. Steps 3 and 4 are both back-end flags, so they go in a
single `back-end` restart.

1. `FEATURE_PROCESSING_PUBLISH_ENABLED=false` on `processing`, then restart
   `processing`; the processor releases the lease and stops writing.
2. Verify the lease is free and `dashboard_snapshot_version` stopped moving.
3. **In one `back-end` restart:** set `FEATURE_PROCESSING_CUTOVER=false` (stop
   feeding hints to a publisher that is going away) **and**
   `FEATURE_DASHBOARD_SNAPSHOT_PUBLISH=true` (the legacy producer re-acquires the
   lease and publishes on the next trigger, or
   `POST /internal/v1/snapshots/refresh` for an immediate build).
4. If step 5 of the cutover repointed `APP_BACKEND_SNAPSHOT_REFRESH_URL` at
   Processing, set it back to
   `http://svitlo-power-back-end:5005/internal/v1/snapshots/refresh` on both BFFs
   in the same restart.
5. Verify snapshot age returns to `< 60s` and both BFFs receive notifications.

**Expected gap.** Between step 1 and step 3 nobody writes the production keys,
so the snapshot ages. The BFFs keep serving the last snapshot until it is older
than `APP_BACKEND_REDIS_DASHBOARD_STALE_THRESHOLD_SECONDS` (300 s), after which
they fall back to live reads for the remainder of the gap. Keep the gap under
300 s; if it will be longer, accept the temporary live-read load.

Rehearse both directions in staging on the day of the cutover and record the
timings in the [cutover checklist](migration-thresholds.md).

## Observability

| Signal | Meaning |
|---|---|
| `processing_publish_enabled` | `1` on the instance that owns the production keys |
| `processing_shadow_lease_held` | `1` on the lease holder; exactly one instance. The name is historical: after the cutover it tracks the production lease. |
| `processing_refresh_notifications_total` | Hints received, by `reason` |
| `processing_refresh_notification_errors_total` | Hints whose rebuild failed, by `reason` |
| `processing_refresh_acknowledged_version` | Version that answered the last hint (stamped only when a version was published) |
| `dashboard_snapshot_age_seconds` | Freshness; the `< 60s` exit gate |

A subscription that receives nothing looks identical to "no data changed", so
`processing_refresh_notifications_total` and the acknowledgement gauges are the
signals that distinguish the two.

## Retirement in Phase 6

The pub/sub trigger is transitional. Phase 6.2 moves admin CRUD into Processing
and Phase 6.3 moves the schedulers, after which the mutation and the snapshot
rebuild are in the same process: the mutation path calls
`RefreshCoordinator.request()` directly and the channel is deleted.

Until then the channel is the only thing keeping snapshot age under the 60 s exit
gate while the legacy back-end still owns the writes, so it must not be removed
early. Removing it requires `FEATURE_PROCESSING_CUTOVER` to be off and the
legacy publisher to be re-enabled, i.e. a full rollback.
