# Phase 3 Spec: Admin Back End & SSE Migration to Redis

## Objective
Move both BFFs (admin-back-end, app-back-end) to Redis-backed reads with local SSE fan-out. Retire the standalone `sse-back-end`.

## Scope
- **Consumers**: `admin-back-end`, `app-back-end` (both get Redis client + SSE fan-out)
- **Producer**: Existing `back-end` (unchanged)
- **Retired**: `sse-back-end` (after verification)
- **Data**: Same `DashboardSnapshot` v1 schema
- **Redis**: Per `redis-conventions.md`

## Deliverables

### 1. Shared SSE Fan-out Library
**Location**: `shared/sse_fanout/` (new package, used by both BFFs)

```python
class SSEFanout:
    def __init__(self, snapshot_client: DashboardSnapshotClient, authz: Authorization): ...
    
    async def handle_connection(self, request: Request, response: StreamingResponse) -> None:
        """Main SSE endpoint handler."""
    
    async def _send_initial_snapshot(self, stream: ServerSentEventStream) -> None:
        """Send full snapshot on connect."""
    
    async def _send_updates(self, stream: ServerSentEventStream) -> None:
        """Listen for snapshot updates, send incremental SSE events."""
    
    def _filter_for_client(self, snapshot: DashboardSnapshot, user: User) -> DashboardSnapshot:
        """Apply authorization: remove admin-only fields for public/mobile clients."""
```

**SSE Event Format**:
```
event: dashboard-update
id: 42
data: {"version": 42, "generatedAt": "...", "sites": [...], "totals": {...}, "outageSchedules": [...]}

event: heartbeat
id: 0
data: {"timestamp": "2026-10-27T18:05:00Z"}
```

- **Event ID**: Snapshot version (enables client reconnect with `Last-Event-ID`)
- **Heartbeat**: Every 30s (configurable) to detect dead connections
- **Initial event**: Full snapshot on connect (not incremental)

### 2. Admin Back End Integration
**Changes**:
- Add `DashboardSnapshotClient` (same as Phase 2)
- Add `SSEFanout` with admin authorization (all fields included)
- New endpoint: `GET /api/v1/admin/dashboard/stream` (SSE)
- Existing REST endpoints (`GET /api/v1/admin/dashboard`, etc.) now read from Redis snapshot
- Remove direct dashboard calculation code

### 3. App Back End SSE (if not in Phase 2)
**Changes**:
- Add `SSEFanout` with public/mobile authorization (filter admin-only fields)
- New endpoint: `GET /api/v1/dashboard/stream` (SSE)
- Mobile app can use same endpoint or continue polling REST

### 4. Authorization Filtering
**Admin-only fields** (removed for public/mobile):
- `SiteSnapshot.inverterModel` (if sensitive)
- `SiteSnapshot.capacityKw` (if sensitive)
- Any future fields marked `adminOnly: true` in schema

**Implementation**:
```python
def _filter_for_client(self, snapshot: DashboardSnapshot, user: User) -> DashboardSnapshot:
    if user.is_admin:
        return snapshot
    
    filtered_sites = []
    for site in snapshot.sites:
        filtered_sites.append(SiteSnapshot(
            id=site.id,
            name=site.name,
            currentPowerKw=site.currentPowerKw,
            energyTodayKwh=site.energyTodayKwh,
            energyTotalKwh=site.energyTotalKwh,
            lastMeasurementAt=site.lastMeasurementAt,
            status=site.status,
            # inverterModel and capacityKw omitted
        ))
    
    return DashboardSnapshot(
        version=snapshot.version,
        generatedAt=snapshot.generatedAt,
        sites=filtered_sites,
        totals=snapshot.totals,  # totals are aggregated, safe
        outageSchedules=snapshot.outageSchedules  # public info
    )
```

### 5. sse-back-end Retirement
**Current role**: Handles SSE connections for both admin and public clients
**Migration**:
1. Both BFFs deploy SSE endpoints (above)
2. Edge proxy routes SSE traffic to new endpoints (feature flag)
3. Monitor for 1 week: connection count, latency, errors
4. Scale down `sse-back-end` to 0
5. Remove `sse-back-end` deployment, code, infrastructure

### 6. Metrics (Additional)
| Metric | Type | Labels | Target |
|--------|------|--------|--------|
| `sse_connections_active` | Gauge | bff (admin, app) | — |
| `sse_connection_duration_seconds` | Histogram | bff | — |
| `sse_events_sent_total` | Counter | bff, event_type | — |
| `sse_reconnect_total` | Counter | bff | — |
| `sse_filtered_fields_total` | Counter | bff, field | — |
| `sse_backend_connections_active` | Gauge | — | 0 (after retirement) |

### 6. Health Checks
**Admin BFF**: `GET /health/admin-sse`
```json
{
  "status": "healthy",
  "activeConnections": 42,
  "snapshotVersion": 42,
  "snapshotAgeSeconds": 30,
  "lastEventSentAt": "2026-10-27T18:05:00Z"
}
```

**App BFF**: `GET /health/app-sse` (same structure)

## Exit Gate (Measurable Thresholds)

| Criterion | Threshold | Measurement Window |
|-----------|-----------|-------------------|
| SSE latency (notification → client) | p99 < 500ms | 24h production |
| SSE reconnect recovery | < 2s, full snapshot received | 10 test reconnects |
| Connection stability | < 0.1% unexpected disconnects/min | 24h production |
| Authorization filtering | 0 admin fields leaked to public | Automated test |
| sse-back-end traffic | 0 required connections for 1 week | 1 week observation |
| REST API parity (vs Phase 2) | 100% field-level match | Contract tests |

## Rollback Procedure

### Per-BFF Rollback
1. **Feature flag**: `BFF_REDIS_SSE_ENABLED=false` (per BFF)
2. **Effect**: 
   - REST endpoints fall back to legacy calculation (or proxy to old back-end)
   - SSE endpoint returns 503 or proxies to `sse-back-end`
3. **Edge proxy**: Route SSE traffic back to `sse-back-end`

### Full Rollback
1. Disable both BFF flags
2. Scale up `sse-back-end` to previous capacity
3. Verify all SSE clients reconnect successfully
4. Investigate: Redis connectivity, snapshot freshness, fan-out logic

## Deployment Steps

1. **Staging**:
   - Deploy both BFFs with SSE fan-out, flag `false`
   - Verify REST parity with Phase 2
   - Test SSE: connect, receive initial snapshot, receive updates, reconnect
   - Test authorization filtering (admin vs public user)
   - Load test: 5000 concurrent SSE connections per BFF

2. **Production (shadow SSE)**:
   - Deploy with flag `false`, SSE endpoints active but not routed
   - Internal test traffic to SSE endpoints
   - Monitor metrics for 24h

3. **Production (gradual SSE cutover)**:
   - Edge proxy: 10% SSE traffic → new BFF endpoints
   - Monitor: connection count, latency, errors, client reconnects
   - Increase: 50% → 100%
   - At 100%: scale down `sse-back-end` to 1 instance (standby)

4. **Production (sse-back-end retirement)**:
   - Observe 1 week with 0 required traffic on `sse-back-end`
   - Scale to 0, remove deployment
   - Remove `sse-back-end` code after 30 days

## Dependencies
- Phase 2 complete (app-back-end Redis client working)
- Shared `sse_fanout` package published
- Edge proxy supports host/path routing with feature flags
- Authorization context available in both BFFs (user roles)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| SSE connection leak | Heartbeat + connection timeout (5 min no activity → close); metrics on active connections |
| Large snapshot on connect | Snapshot < 512KB; if larger, consider delta updates (future) |
| Admin fields leaked | Unit test: public user receives filtered snapshot; integration test in CI |
| sse-back-end clients don't reconnect | Mobile app: implement `Last-Event-ID` reconnect; web: EventSource auto-reconnect |
| Version lag causes stale SSE | Reconciliation every 60s + notification-driven; alert on lag > 1 |

## Test Checklist

- [ ] Unit: SSEFanout sends initial snapshot, then updates on notification
- [ ] Unit: Authorization filtering removes admin fields for public user
- [ ] Unit: Heartbeat sent every 30s
- [ ] Unit: Reconnect with Last-Event-ID receives missed events (or full snapshot)
- [ ] Integration: Admin BFF REST + SSE both read from Redis
- [ ] Integration: App BFF REST + SSE both read from Redis
- [ ] Integration: Edge proxy routes SSE correctly per host
- [ ] Load: 5000 concurrent SSE connections, p99 latency < 500ms
- [ ] Chaos: Redis down → SSE sends stale snapshot with warning, heartbeats continue
- [ ] Chaos: BFF restart → clients reconnect, receive full snapshot
- [ ] Chaos: sse-back-end scaled to 0 → no client errors
- [ ] Contract: Mobile app SSE client works (if applicable)