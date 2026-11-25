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

Exactly one producer may hold the lease `lock:processing:dashboard:v1` at any
time. Never enable both publishers.

## Cutover

1. **Disable the legacy publisher**
   `FEATURE_DASHBOARD_SNAPSHOT_PUBLISH=false` on `back-end`.
2. **Verify the legacy producer stopped** (≤ 2 min)
   - `dashboard_snapshot_version` from `job="svitlo-power-back-end"` stops
     incrementing.
   - `lock:processing:dashboard:v1` is released (`GET` returns nil).
3. **Enable the Processing publisher**
   `FEATURE_PROCESSING_PUBLISH_ENABLED=true` on `processing`.
4. **Enable the back-end trigger**
   `FEATURE_PROCESSING_CUTOVER=true` on `back-end`.
5. **Verify**
   - `processing_publish_enabled` is `1` and the lease holder is `processing-*`.
   - `dashboard_snapshot_version` increments from
     `job="svitlo-power-processing"`.
   - `cache:dashboard:v1:invalidations` notifications flow to both BFFs.
   - `processing_refresh_notifications_total` increases while exercising admin
     CRUD, station sync and the outage schedule refresh.
6. **Freshness gate** — `dashboard_snapshot_age_seconds < 60` continuously while
   the triggers above are exercised. The pub/sub path must be the one producing
   the refreshes, not the 300 s reconciliation cron.
7. **Monitor for 30 min** before closing the change.

## Rollback (< 2 min)

1. `FEATURE_PROCESSING_PUBLISH_ENABLED=false` on `processing`; the processor
   releases the lease and stops writing.
2. Verify the lease is free and `dashboard_snapshot_version` stopped moving.
3. `FEATURE_PROCESSING_CUTOVER=false` on `back-end` so the re-enabled legacy
   publisher is not fed hints it no longer needs.
4. `FEATURE_DASHBOARD_SNAPSHOT_PUBLISH=true` on `back-end`; the legacy producer
   re-acquires the lease and publishes on the next trigger (or
   `POST /internal/v1/snapshots/refresh` for an immediate build).
5. Verify snapshot age returns to `< 60s` and both BFFs receive notifications.

Rehearse both directions in staging on the day of the cutover and record the
timings in the [cutover checklist](migration-thresholds.md).

## Observability

| Signal | Meaning |
|---|---|
| `processing_publish_enabled` | `1` on the instance that owns the production keys |
| `processing_shadow_lease_held` | `1` on the lease holder; exactly one instance |
| `processing_refresh_notifications_total` | Hints received, by `reason` |
| `processing_refresh_notification_errors_total` | Hints whose rebuild failed |
| `processing_refresh_acknowledged_version` | Version that answered the last hint |
| `dashboard_snapshot_age_seconds` | Freshness; the `< 60s` exit gate |

A subscription that receives nothing looks identical to "no data changed", so
`processing_refresh_notifications_total` and the acknowledgement gauges are the
signals that distinguish the two.