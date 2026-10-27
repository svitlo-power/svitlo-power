# Incremental production migration plan

This plan moves the production system from its current deployment toward the
target architecture in [ADR 0001](../adr/0001-service-boundaries-and-dashboard-data-flow.md).
Each phase is a separately deployable release that leaves production usable.
Do not defer all production traffic changes until every service has been built.

## Migration principles

- Treat the architecture migration as an ASAP priority and release useful,
  reversible increments as soon as each exit gate passes; do not wait for the
  full target system. Start the OIDC Identity Service work in parallel with the
  dashboard snapshot migration.
- Preserve existing UI and mobile API contracts unless a separately planned
  contract change is required.
- Make consumers support the new contract before switching producers.
- Use feature flags or routing controls for reversible cutovers where possible.
- For any state or scheduled side effect, have exactly one authoritative writer
  at a time. Never run old and new message senders or pollers concurrently
  without an explicit deduplication/lease mechanism.
- Dashboard and outage-schedule snapshots are disposable, rebuildable data.
  Redis loss must not require backup restoration; the producer refetches them
  from their authoritative source (MongoDB).
- During transition, legacy direct database access is temporary. Track and
  remove each access as its owning API is deployed; it is not the target
  architecture.
- Measure freshness, errors, parity, and resource health before expanding
  traffic. Define concrete thresholds from production baselines before each
  cutover.
- Keep each stage independently deployable and document its rollback trigger
  and procedure before enabling it in production.
- Snapshot refreshes are event/change driven: refresh at producer startup and
  when the source data changes. Where upstream APIs do not expose change
  notifications, detect changes in the existing fetch/poll cycle. A cache miss
  triggers an immediate coalesced refresh request via HTTP. Set stale-data alert
  limits from each upstream API's expected update cadence; do not add a long
  arbitrary observation delay.
- **No code removal until Phase 9** — legacy calculation code stays runnable for rollback.

## Phases

### 0. Establish baselines and release controls

**Deploy:** instrumentation and operational controls only.

- Inventory existing dashboard response shapes, update cadence, SSE event
  names, user-visible freshness, routes, scheduled jobs, and message behavior.
- Add or confirm health checks, structured logs, and metrics for dashboard
  generation/freshness, Redis connections, SSE subscribers, and scheduled job
  ownership.
- Establish production feature-flag and rollback procedures.

**Exit gate:** dashboards and scheduled jobs have measurable baselines; the
team can identify the active producer/scheduler and safely disable a new
consumer.

**Rollback:** disable new metrics or flags; user-visible behavior is unchanged.

### 1. Publish disposable dashboard and outage-schedule snapshots

**Deploy:** Redis snapshot writes while the existing `back-end` remains the sole
dashboard calculator and snapshot producer.

- Define a versioned, language-neutral JSON snapshot and Redis key/channel
  conventions. Include an atomic write with lease fencing, epoch+version, and generation
  time.
- Include the finite dashboard and outage-schedule fields used by the public
  front end and mobile app in one shared snapshot, one Redis key, and one
  notification channel. Both consumers use the same contract.
- Fetch/rebuild the snapshot from MongoDB (via shared repositories). Write it to
  Redis as a disposable cache, then publish a small invalidation notification.
- A missing or expired Redis key is a cache miss, not a data-loss incident.
  The producer must support fetching source data and repopulating the cache;
  BFFs request that refresh/read via HTTP `POST /internal/v1/snapshots/refresh`
  rather than becoming additional producers.
- Keep existing API responses and existing event delivery unchanged in this
  release.
- Add monitoring for snapshot age, write errors, and version progression.

**Exit gate:** snapshots match the existing back end's response data, are
written at the expected cadence, can be read atomically, and are successfully
rebuilt after an empty-cache test without affecting the current UI.

**Rollback:** disable Redis publishing; the existing calculator and API remain
authoritative.

### 2. Move the app back end to Redis-backed dashboard data

**Deploy:** Redis reads in the `app-back-end`, initially dark/shadow traffic.

- Subscribe before the initial snapshot load. Reload on subscription reconnect
  and periodically reconcile (epoch, version) so missed Pub/Sub messages do not leave
  a process stale.
- On a Redis cache miss, request a source refresh/read through the producer via
  HTTP `POST /internal/v1/snapshots/refresh`; do not rely on a Redis backup or treat a missing key as authoritative empty
  data.
- In shadow mode, compare Redis-backed values against the app back end's
  current calculations without returning the new values to clients (background sampling).
- Add a feature flag to serve the Redis projection while retaining the current
  calculation temporarily as a rollback path.
- Enable gradually and compare response parity, error rates, and freshness.

**Exit gate:** production parity and freshness remain within pre-agreed
thresholds; restart and Redis reconnect tests show the app back end recovers
from missed notifications. Mobile API response compatibility is verified.

**Rollback:** turn off the Redis-read flag and serve the legacy calculation.
Keep publishing Redis snapshots while investigating.

### 3. Move the back-end (admin) and app-back-end SSE to Redis

**Deploy:** Redis-backed reads and local SSE fan-out for both `back-end` (admin)
and `app-back-end` (public); retire `sse-back-end`.

- Both back-ends subscribe, load/reconcile snapshots, and serve their
  established response shapes.
- Fan out update events to clients connected to each back-end. SSE reconnects fetch
  a fresh normal API snapshot; Pub/Sub is not treated as replayable history.
- Keep the existing `sse-back-end` available until both back-ends' SSE paths have
  passed reconnect and load checks.
- **Backward-compatible SSE**: Keep unnamed events for `onmessage` compatibility;
  add named `dashboard-update` events for new clients. Heartbeat as `: ping` comment.
- Ensure projections and authorization prevent admin-only fields from
  reaching public or mobile clients.

**Exit gate:** both back-ends deliver updates with acceptable latency, survive
restarts/reconnects, and apply their own client access policies. Existing web UI works without changes.

**Rollback:** route SSE traffic back to the existing SSE service and disable
Redis-backed reads per back-end. Retire the old SSE service only after an agreed
observation period with no required traffic.

### 4. Deploy Processing in dashboard snapshot shadow mode

**Deploy:** a Processing service that reads MongoDB directly (via shared repositories),
builds disposable snapshots, but does not publish to production Redis keys/channels.

- Define and test the versioned projection and internal HTTP contracts without
  coupling them to Python models, MongoDB documents, or framework details.
- Refresh once on startup and whenever a source change is detected. If an
  upstream source has no change notification, detect changes during its
  existing fetch/poll cycle. Support an immediate, coalesced refresh on BFF
  cache miss via HTTP.
- Compare Processing output with the existing back end's production snapshots,
  including a test where Redis starts empty.
- Monitor processing duration, data freshness, and projection parity.
- **Shadow isolation**: Use `shadow:` prefixed Redis keys; never touch production keys or lease.

**Exit gate:** output parity and reliability meet agreed thresholds over a
representative production period, including failure/restart cases.

**Rollback:** stop or disable the shadow worker. Production Redis remains
written by the existing back end.

### 5. Switch snapshot ownership to Processing

**Deploy:** a controlled producer cutover; one authoritative publisher at a
time.

- Quiesce or disable the legacy dashboard publisher before enabling
  Processing's production publishing.
- Keep Redis keys, channel names, and snapshot version compatible with
  existing consumers. Redis remains a disposable cache; verify Processing can
  rebuild it from MongoDB after an empty-cache start.
- Maintain a fast rollback to the legacy publisher. Before rollback, ensure
  Processing has stopped publishing; never have both publishers race.
- **Do NOT remove dashboard calculation code from back-end yet** — only disable
  the publish flag. Legacy code stays runnable for rollback until Phase 9.

**Exit gate:** all back-ends consume Processing snapshots, freshness and parity
remain acceptable, and rollback has been rehearsed.

**Rollback:** stop Processing publishing, verify it is inactive, then
re-enable the existing back-end publisher. Consumers need no change if the
projection contract is unchanged.

### 6. Move remaining processing capabilities one at a time

Move each capability as its own release, preserving existing client-facing
routes where practical. The `back-end` proxies to Processing over private,
versioned HTTP APIs.

Suggested order:

1. **Message preview:** proxy the admin request to Processing; verify preview
   shares generation logic with delivery and cannot send, queue, or persist a
   delivery.
2. **Admin domain CRUD and queries:** add Processing endpoints and contract
   tests, route the back-end through them, then remove its corresponding MongoDB
   reads/writes. Do not remove direct access until all required operations have
   an API owner. Includes: Buildings, Stations, Outage Schedules, Users, Power Logs (query API).
3. **Deye polling and station synchronization:** transfer the scheduler and
   ownership, ensuring only one active poller per source. Interval: 120s default.
4. **Cleanup:** transfer retention job (daily 00:10, `STATISTIC_KEEP_DAYS`) and verify
   deletion scope before disabling the old job.
5. **Message delivery (Telegram + FCM Push):** move scheduled sending last with
   explicit single-owner cutover, idempotency/deduplication, and delivery monitoring.
6. **Grid Reporter (separate service):** evaluate consolidation separately.

**Exit gate for each capability:** contract tests pass, production behavior is
verified, ownership is unambiguous, and a rollback procedure is rehearsed.

**Rollback:** disable the Processing capability before restoring the legacy
implementation. For scheduled side effects, confirm the new worker is stopped
before enabling the old one.

### 7. Introduce the identity boundary (Admin Only)

**Deploy:** migrate identity independently from dashboard and processing
cutovers; begin this work in parallel so it does not delay the dashboard
rollout. **Public web and mobile remain anonymous.**

- Implement the new Identity Service in NestJS as an OIDC provider using
  `oidc-provider` (panva), a standards-compliant library.
- Store identity-owned records in the existing service MongoDB deployment with
  credentials restricted to identity collections. Processing is the sole
  owner and writer of application-domain user profiles, bindings, and
  permissions.
- Link OIDC identities to Processing-owned domain users with a stable `sub`;
  Identity must not update domain bindings directly.
- Authenticate back-end-to-Processing calls with private-network service identity
  (preferably mTLS/workload identity) plus a separate short-lived user or
  delegated token whose audience is Processing. Use token exchange (RFC 8693)
  or validate the signed user token at Processing.
- Migrate **admin clients only** while preserving existing login behavior until the new
  issuer and account mappings are verified.

**Exit gate:** admin authentication paths are verified; Processing validates both
service and user identity, authorization and account linking work, and rollback
does not strand users. Public/mobile unchanged.

**Rollback:** switch admin clients back to the existing issuer/session mechanism
while preserving account mappings. Avoid destructive credential migrations.

### 8. Separate public and admin applications

**Deploy:** separate static front ends and host-aware edge routing.

- Move public-facing routes from the `back-end` to the `app-back-end` before
  restricting the `back-end` to admin operations.
- Deploy public UI at `svitlo-power.pp.ua` and admin UI at
  `admin.svitlo-power.pp.ua`.
- Route each host to its matching back-end and retain the mobile API contract.
- Configure explicit origins and separate authentication cookie/session
  boundaries. **Admin cookie host-only (no Domain attr).**

**Exit gate:** public, admin, and mobile smoke tests pass through production
routes; old routes have no required traffic.

**Rollback:** restore the previous host routing and UI deployment while
keeping APIs backward compatible.

### 9. Retire legacy components and permissions

**Deploy:** cleanup after observation and sign-off.

- Remove old dashboard computations, jobs, routes, database credentials, and
  SSE service only when logs confirm no required consumers remain.
- Remove temporary compatibility flags and migration-only code after their
  rollback window closes.
- Keep operational runbooks for Redis failure, stale projections, Processing
  unavailability, and scheduled-job ownership.

**Exit gate:** target ownership is reflected in deployments, code, credentials,
and monitoring; no legacy path is still serving production traffic.

## Cross-phase production gate

Before each production flag/routing cutover, record:

- The exact service/version and traffic scope being changed.
- Expected parity, freshness, latency, and error-rate thresholds.
- Who is watching production and who can initiate rollback.
- The rollback trigger and the ordered steps, especially for single-writer
  jobs.
- The observation period and evidence required before removing the old path.

Do not combine unrelated ownership changes into one release solely to reduce
deployment count. Each release should have a single clear behavior change and
a known-good production state to return to.
