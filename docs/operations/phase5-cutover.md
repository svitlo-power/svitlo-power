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
5. **Verify**
   - `processing_publish_enabled` is `1` and the lease holder is `processing-*`.
   - `dashboard_snapshot_version` from `job="svitlo-power-processing"`
     increments **and matches the production key** (`GET meta:dashboard:version`);
     the gauge is also exported for the shadow publisher, so a value that only
     increments is not enough.
   - `cache:dashboard:v1:invalidations` notifications flow to both BFFs.
   - `processing_refresh_notifications_total` increases while exercising admin
     CRUD, station sync and the outage schedule refresh.
6. **Freshness gate** - `dashboard_snapshot_age_seconds < 60` continuously while
   the triggers above are exercised. The pub/sub path must be the one producing
   the refreshes, not the 300 s reconciliation cron.
7. **Monitor for 30 min** before closing the change.

### After the cutover

- **Parity is meaningless.** Processing now owns the production key, so the
  shadow comparison is skipped and `processing_shadow_parity_rate` is exported
  as `NaN`. Do not read parity or the parity/staleness alerts after the cutover.
- **The UI event mode switches off.** `dashboardUpdatedEventEnabled` is only set
  while `FEATURE_DASHBOARD_SNAPSHOT_PUBLISH` is on, and only the legacy producer
  sends `dashboard_updated`. After the cutover the front-end falls back to
  per-entity events. Sending `dashboard_updated` from Processing is planned for a
  later phase.

## Rollback (< 2 min)

Every step is a restart.

1. `FEATURE_PROCESSING_PUBLISH_ENABLED=false` on `processing`, then restart
   `processing`; the processor releases the lease and stops writing.
2. Verify the lease is free and `dashboard_snapshot_version` stopped moving.
3. `FEATURE_PROCESSING_CUTOVER=false` on `back-end`, then restart `back-end` so
   the re-enabled legacy publisher is not fed hints it no longer needs.
4. `FEATURE_DASHBOARD_SNAPSHOT_PUBLISH=true` on `back-end`, then restart
   `back-end`; the legacy producer re-acquires the lease and publishes on the
   next trigger (or `POST /internal/v1/snapshots/refresh` for an immediate
   build).
5. Verify snapshot age returns to `< 60s` and both BFFs receive notifications.

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
