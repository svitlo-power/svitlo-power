# Phase 3 Spec: SSE Migration to Redis (Back-end + App-back-end)

## Objective
Move both `back-end` (admin) and `app-back-end` to Redis-backed reads with local SSE fan-out. Retire the standalone `sse-back-end`.

## Scope
- **Consumers**: `back-end` (admin SSE), `app-back-end` (public SSE)
- **Producer**: Existing `back-end` (unchanged from Phase 1)
- **Retired**: `sse-back-end` (after verification)
- **Data**: Same `DashboardSnapshot` v1 schema
- **Redis**: Per `redis-conventions.md`

## Deliverables

### 1. Shared SSE Fan-out Library
**Location**: `shared/python/shared/services/sse_fanout.py` (new, used by both back-ends)

```python
class SSEFanout:
    def __init__(self, snapshot_client: DashboardSnapshotClient, is_admin: bool): ...
    
    async def handle_connection(self, request: Request, user_id: str | None) -> StreamingResponse:
        """Main SSE endpoint handler - compatible with existing /api/events format."""
    
    async def _send_initial_snapshot(self, stream: ServerSentEventStream, user_id: str | None) -> None:
        """Send full snapshot on connect as unnamed events (for onmessage compatibility)."""
    
    async def _send_updates(self, stream: ServerSentEventStream, user_id: str | None) -> None:
        """Listen for snapshot updates, send incremental SSE events."""
    
    def _filter_for_client(self, snapshot: DashboardSnapshot, user_id: str | None) -> DashboardSnapshot:
        """Apply authorization: admin gets all fields, public gets filtered."""
```

**SSE Event Format (Backward Compatible)**:
- **Existing clients use `EventSource.onmessage`** which only receives **unnamed events**
- Keep unnamed events with `{type, data, private, user}` structure
- Add optional `event: dashboard-update` for new clients that use `addEventListener`

```
# Initial connection - unnamed events (for onmessage)
data: {"type": "dashboard", "data": {...}, "private": false, "user": null}

data: {"type": "buildings", "data": [...], "private": false, "user": null}

data: {"type": "config", "data": {...}, "private": false, "user": null}

# Updates - unnamed for backward compat, plus named for new clients
data: {"type": "dashboard-update", "data": {"epoch": 1, "version": 43}, "private": false, "user": null}
event: dashboard-update
id: 1-43
data: {"epoch": 1, "version": 43}

# Heartbeat - SSE comment (no id, doesn't reset lastEventId)
: ping
```

- **Event ID**: `epoch-version` (enables client reconnect with `Last-Event-ID`)
- **Heartbeat**: Every 30s as SSE comment `: ping` (no `id`, doesn't reset `lastEventId`)
- **Initial events**: Full snapshot split by type (dashboard, buildings, config, outages)

### 2. Back-end (Admin) Integration
**Changes**:
- Add `DashboardSnapshotClient` (same as Phase 2)
- Add `SSEFanout` with `is_admin=True` (all fields included)
- **Existing endpoint**: `GET /api/events` (unchanged path, now reads from Redis)
- Existing REST endpoints (`GET /api/dashboard/*`, etc.) now read from Redis snapshot
- Remove direct dashboard calculation code from `DashboardService` (keep for Phase 1-4 producer role)

### 3. App-back-end SSE
**Changes**:
- Add `SSEFanout` with `is_admin=False` (filter admin-only fields)
- **Existing endpoint**: `GET /api/events` (unchanged path, now reads from Redis)
- Public/mobile clients continue using same endpoint

### 4. Authorization Filtering
**Admin-only fields** (removed for public/mobile):
- Building: `hasBoundStation` (if sensitive), internal IDs
- Config: `enableOutagesSchedule`, `outagesScheduleQueue` (internal settings)

**Implementation**:
```python
def _filter_for_client(self, snapshot: DashboardSnapshot, user_id: str | None) -> DashboardSnapshot:
    if user_id and await self._is_admin(user_id):
        return snapshot  # Admin gets all fields
    
    # Public/mobile: filter sensitive fields
    filtered_buildings = []
    for building in snapshot.buildings:
        filtered_buildings.append(BuildingSnapshot(
            id=building.id,
            name=building.name,
            color=building.color,
            order=building.order,
            hasBoundStation=False,  # Always false for public
            isGridAvailable=building.isGridAvailable,
            gridAvailabilityPct=building.gridAvailabilityPct,
            hasMixedReporterStates=building.hasMixedReporterStates,
            isCharging=building.isCharging,
            isDischarging=building.isDischarging,
            isOffline=building.isOffline,
            batteryPercent=building.batteryPercent,
            consumptionPower=building.consumptionPower,
            batteryDischargeTime=building.batteryDischargeTime,
            batteryChargeTime=building.batteryChargeTime,
            chargeSource=building.chargeSource,
            chargePower=building.chargePower,
        ))
    
    filtered_config = ConfigSnapshot(
        title=snapshot.config.title,
        enableOutagesSchedule=False,  # Internal setting
        outagesScheduleQueue=None,    # Internal setting
    )
    
    return DashboardSnapshot(
        epoch=snapshot.epoch,
        version=snapshot.version,
        generatedAt=snapshot.generatedAt,
        buildings=filtered_buildings,
        config=filtered_config,
        outagesSchedules=snapshot.outagesSchedules  # Public info
    )
```

### 5. JWT in Query Parameter (Current Reality)
**Current**: `/api/events?token=<jwt>` — token ends up in logs
**Phase 3**: Keep query param for backward compatibility, add migration path:
- Short-term: Accept token in query param, log warning
- Medium-term: Add `Authorization: Bearer` header support
- Long-term: Short-lived SSE ticket via `POST /api/events/ticket` (returns one-time token)

### 6. sse-back-end Retirement
**Current role**: Handles SSE connections for both admin and public clients
**Migration**:
1. Both back-ends deploy SSE endpoints (above)
2. Edge proxy routes SSE traffic to new endpoints (feature flag)
3. Monitor for 1 week: connection count, latency, errors
4. Scale down `sse-back-end` to 0
5. Remove `sse-back-end` deployment, code, infrastructure

### 7. Metrics (Additional)
| Metric | Type | Labels | Target |
|--------|------|--------|--------|
| `sse_connections_active` | Gauge | backend (back-end, app-back-end) | — |
| `sse_connection_duration_seconds` | Histogram | backend | — |
| `sse_events_sent_total` | Counter | backend, event_type | — |
| `sse_reconnect_total` | Counter | backend | — |
| `sse_filtered_fields_total` | Counter | backend, field | — |
| `sse_backend_connections_active` | Gauge | — | 0 (after retirement) |

### 8. Health Checks
**Back-end**: `GET /health/sse`
```json
{
  "status": "healthy",
  "activeConnections": 42,
  "snapshotEpoch": 1,
  "snapshotVersion": 42,
  "snapshotAgeSeconds": 30,
  "lastEventSentAt": "2026-10-27T18:05:00Z"
}
```

**App-back-end**: `GET /health/sse` (same structure)

## Exit Gate (Measurable Thresholds)

| Criterion | Threshold | Measurement Window |
|-----------|-----------|-------------------|
| SSE latency (notification → client) | p99 < 500ms | 24h production |
| SSE reconnect recovery | < 2s, full snapshot received | 10 test reconnects |
| Connection stability | < 0.1% unexpected disconnects/min | 24h production |
| Authorization filtering | 0 admin fields leaked to public | Automated test |
| sse-back-end traffic | 0 required connections for 1 week | 1 week observation |
| REST API parity (vs Phase 2) | 100% field-level match | Contract tests |
| Backward compatibility | Existing web UI works without changes | E2E test |

## Rollback Procedure

### Per-Back-end Rollback
1. **Feature flag**: `BACKEND_REDIS_SSE_ENABLED=false` (per back-end)
2. **Effect**: 
   - REST endpoints fall back to legacy calculation
   - SSE endpoint proxies to `sse-back-end` (or returns 503)
3. **Edge proxy**: Route SSE traffic back to `sse-back-end`

### Full Rollback
1. Disable both back-end flags
2. Scale up `sse-back-end` to previous capacity
3. Verify all SSE clients reconnect successfully
4. Investigate: Redis connectivity, snapshot freshness, fan-out logic

## Deployment Steps

1. **Staging**:
   - Deploy both back-ends with SSE fan-out, flag `false`
   - Verify REST parity with Phase 2
   - Test SSE: connect, receive initial snapshot, receive updates, reconnect
   - Test authorization filtering (admin vs public user)
   - Load test: 5000 concurrent SSE connections per back-end

2. **Production (shadow SSE)**:
   - Deploy with flag `false`, SSE endpoints active but not routed
   - Internal test traffic to SSE endpoints
   - Monitor metrics for 24h

3. **Production (gradual SSE cutover)**:
   - Edge proxy: 10% SSE traffic → new back-end endpoints
   - Monitor: connection count, latency, errors, client reconnects
   - Increase: 50% → 100%
   - At 100%: scale down `sse-back-end` to 1 instance (standby)

4. **Production (sse-back-end retirement)**:
   - Observe 1 week with 0 required traffic on `sse-back-end`
   - Scale to 0, remove deployment
   - Remove `sse-back-end` code after 30 days

## Dependencies
- Phase 2 complete (app-back-end Redis client working)
- Shared `sse_fanout` module in `shared/python/shared/services/`
- Edge proxy supports host/path routing with feature flags
- Authorization context available in both back-ends (user roles)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| SSE connection leak | Heartbeat + connection timeout (5 min no activity → close); metrics on active connections |
| Large snapshot on connect | Snapshot < 512KB; split into multiple unnamed events |
| Admin fields leaked | Unit test: public user receives filtered snapshot; integration test in CI |
| sse-back-end clients don't reconnect | Web: EventSource auto-reconnect; mobile: same |
| Version lag causes stale SSE | Reconciliation every 60s + notification-driven; alert on lag > 1 |
| JWT in query param | Log warning; plan migration to header/ticket in Phase 6+ |

## Test Checklist

- [ ] Unit: SSEFanout sends initial snapshot as unnamed events, then updates
- [ ] Unit: Authorization filtering removes admin fields for public user
- [ ] Unit: Heartbeat sent as `: ping` comment every 30s
- [ ] Unit: Reconnect with Last-Event-ID receives missed events (or full snapshot)
- [ ] Unit: Backward compatibility - unnamed events received by `onmessage`
- [ ] Integration: Back-end REST + SSE both read from Redis
- [ ] Integration: App-back-end REST + SSE both read from Redis
- [ ] Integration: Edge proxy routes SSE correctly per host
- [ ] Load: 5000 concurrent SSE connections, p99 latency < 500ms
- [ ] Chaos: Redis down → SSE sends stale snapshot with warning, heartbeats continue
- [ ] Chaos: Back-end restart → clients reconnect, receive full snapshot
- [ ] Chaos: sse-back-end scaled to 0 → no client errors
- [ ] Contract: Existing web UI works without code changes