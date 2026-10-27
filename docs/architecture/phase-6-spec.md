# Phase 6 Spec: Move Remaining Processing Capabilities

## Objective
Move each background capability from the `back-end` to the Processing Service, one at a time, with explicit single-owner cutover and rollback.

## Capabilities & Order

| # | Capability | Source (Legacy) | Target (Processor) | Cutover Type |
|---|------------|-----------------|-------------------|--------------|
| 1 | Message Preview | `back-end` (admin) | Processor HTTP API | Proxy → Direct |
| 2 | Admin Domain CRUD/Queries | `back-end` (MongoDB) | Processor HTTP API | Proxy → Direct |
| 3 | Deye Polling & Station Sync | `back-end` scheduler | Processor scheduler | Lease transfer |
| 4 | Cleanup/Retention Jobs | `back-end` scheduler | Processor scheduler | Lease transfer |
| 5 | Message Delivery (Telegram + FCM) | `back-end` scheduler | Processor scheduler | Lease transfer + idempotency |
| 6 | Grid Reporter (separate service) | `grid-reporter` | Processor or keep separate | Evaluate |

---

## Capability 1: Message Preview

### Current Flow
```
Admin UI → back-end → Message Generator (Python) → Preview Response
```

### Target Flow
```
Admin UI → back-end → Processor POST /internal/v1/messages/preview → Preview Response
```

### Processor API Contract
**Endpoint**: `POST /internal/v1/messages/preview`
**Auth**: Service-to-service (mTLS) + User token (delegated)
**Request**:
```json
{
  "templateId": "outage-alert",
  "params": {
    "buildingId": "building-123",
    "outageStart": "2026-10-27T10:00:00Z",
    "outageEnd": "2026-10-27T14:00:00Z"
  },
  "locale": "uk"
}
```
**Response**:
```json
{
  "renderedSubject": "Planned outage for building-123",
  "renderedBody": "Dear customer, ...",
  "metadata": {
    "templateId": "outage-alert",
    "generatedAt": "2026-10-27T09:00:00Z",
    "recipientCount": 1
  }
}
```

### Migration Steps
1. **Add Processor endpoint** (implements same generation logic as legacy)
2. **Add contract tests** (request/response schema, preview vs delivery parity)
3. **Back-end**: Add proxy route → Processor, feature flag `MESSAGE_PREVIEW_VIA_PROCESSOR`
4. **Shadow mode**: Call both, compare responses, log mismatches
5. **Cutover**: Enable flag, verify parity, remove legacy generator code
6. **Rollback**: Disable flag, legacy generator serves

### Exit Gate
- Contract tests pass
- Shadow parity ≥ 99.9% (24h)
- Preview shares generation code with delivery (verified by code review)
- Preview cannot send/queue/persist (verified by test)

---

## Capability 2: Admin Domain CRUD & Queries

### Current Flow
```
Admin UI → back-end → MongoDB (direct) → Response
```

### Target Flow
```
Admin UI → back-end → Processor HTTP API → MongoDB → Response
```

### Processor API Contracts (Versioned, OpenAPI)

#### Buildings
| Operation | Endpoint | Description |
|-----------|----------|-------------|
| List | `GET /internal/v1/buildings` | Paginated, filterable |
| Get | `GET /internal/v1/buildings/{id}` | Single building |
| Create | `POST /internal/v1/buildings` | Admin only |
| Update | `PATCH /internal/v1/buildings/{id}` | Admin only |
| Delete | `DELETE /internal/v1/buildings/{id}` | Admin only |

#### Stations (Deye devices)
| Operation | Endpoint | Description |
|-----------|----------|-------------|
| List | `GET /internal/v1/stations` | Paginated |
| Get | `GET /internal/v1/stations/{id}` | Single station |
| Sync | `POST /internal/v1/stations/{id}/sync` | Trigger Deye sync |

#### Outage Schedules
| Operation | Endpoint | Description |
|-----------|----------|-------------|
| List | `GET /internal/v1/outage-schedules` | Filter by queue, date range |
| Get | `GET /internal/v1/outage-schedules/{queue}` | Single schedule |
| Create | `POST /internal/v1/outage-schedules` | Admin only |
| Update | `PATCH /internal/v1/outage-schedules/{queue}` | Admin only |
| Delete | `DELETE /internal/v1/outage-schedules/{queue}` | Admin only |

#### Users & Permissions (Domain)
| Operation | Endpoint | Description |
|-----------|----------|-------------|
| List | `GET /internal/v1/users` | Domain users (not identity) |
| Get | `GET /internal/v1/users/{id}` | Profile + permissions |
| Update Permissions | `PATCH /internal/v1/users/{id}/permissions` | Admin only |

#### Power Logs (Query API - NOT in snapshot)
| Operation | Endpoint | Description |
|-----------|----------|-------------|
| Query | `POST /internal/v1/buildings/{id}/power-logs` | Date-range query |

> **Note**: Power logs are date-range queries and cannot be served from a finite snapshot. The Processor must expose a query API for this.

### Migration Steps (Per Resource)
1. **Add Processor endpoints** with contract tests
2. **Back-end**: Add proxy routes, feature flag per resource (e.g., `BUILDINGS_VIA_PROCESSOR`)
3. **Shadow mode**: Dual call, compare
4. **Cutover**: Enable flag, verify, remove MongoDB access for that resource
5. **Repeat** for each resource

### Authorization
- Processor validates: Service identity + User token (delegated)
- User token claims: `sub`, `roles`, `permissions`
- Processor enforces: Admin role required for mutations
- Audit log: Every mutation logs `actor_sub`, `action`, `resource`, `timestamp`

### Exit Gate (Per Resource)
- Contract tests pass (OpenAPI + schema validation)
- Shadow parity ≥ 99.9% (24h)
- All admin UI flows work via Processor
- Legacy MongoDB access removed for that resource
- Rollback rehearsed (< 2 min)

---

## Capability 3: Deye Polling & Station Synchronization

### Current Flow
```
back-end Scheduler (APScheduler) → Deye Client → MongoDB (measurements, stations)
```

### Target Flow
```
Processor Scheduler (lease-held) → Deye Client → Processor Internal API → MongoDB
```

### Key Changes
- **Single poller**: Processor lease ensures only one instance polls
- **Polling interval**: Configurable (default 120s, matches `DEYE_FETCH_INTERVAL`), per-station
- **Station sync**: Triggered by schedule or admin API call
- **Data flow**: Measurements → Processor → MongoDB (not direct from Deye client)

### Processor Internal API (for own use)
```
POST /internal/v1/measurements/batch
POST /internal/v1/stations/{id}/measurements
```

### Migration Steps
1. **Extract Deye client** into shared library (used by Processor)
2. **Implement polling in Processor** (scheduler + lease)
3. **Shadow mode**: Processor polls, writes to separate MongoDB collection (or dry-run), compares with legacy
4. **Cutover**: 
   - Disable legacy scheduler (`BACKEND_DEYE_POLL_ENABLED=false`)
   - Verify legacy stops (metrics)
   - Enable Processor polling (`PROCESSOR_DEYE_POLL_ENABLED=true`)
   - Verify measurements appear in MongoDB
5. **Rollback**: Reverse flags

### Exit Gate
- Zero data loss during cutover (measurement count matches)
- Polling interval maintained (p99 < 150s, matching current 120s default)
- Station sync on-demand works via Processor API
- Legacy scheduler code removed

---

## Capability 4: Cleanup / Retention Jobs

### Current Jobs
| Job | Schedule | Action |
|-----|----------|--------|
| Delete old data | Daily 00:10 | Delete measurements > `STATISTIC_KEEP_DAYS` |

### Target
Same job, running in Processor scheduler (lease-held).

### Migration Steps
1. **Implement in Processor** with same logic, configurable schedule
2. **Shadow mode**: Processor runs, logs what it *would* delete, compares with legacy actual deletions
3. **Cutover**: Disable legacy job, enable Processor job
4. **Verify**: Deletion counts match, no over-deletion

### Exit Gate
- Shadow deletion list matches legacy 100% (7 days)
- Production run: deletion count within 1% of baseline
- Rollback: Legacy job re-enabled, Processor job disabled

---

## Capability 5: Message Delivery (Telegram + FCM Push)

### Current Flow
```
back-end Scheduler → Message Generator → Telegram Bot API / FCM → MongoDB (delivery log)
```

### Target Flow
```
Processor Scheduler (lease) → Message Generator → Telegram Bot API / FCM → Processor Internal API → MongoDB
```

### Critical Requirements
- **Single sender**: Lease ensures only one Processor instance sends
- **Idempotency**: Each delivery has deterministic `delivery_id`
- **Deduplication**: `SETNX delivery:{delivery_id} 1 EX 86400` before send
- **Delivery tracking**: Status (pending, sent, failed, retrying) in MongoDB

### Delivery ID Format
```
delivery_id = sha256(template_id + recipient_id + scheduled_at_iso + params_json)[:16]
```

### Migration Steps
1. **Extract message generator** into shared library
2. **Implement Processor delivery scheduler** with lease + idempotency
3. **Shadow mode**: Processor generates deliveries, logs but doesn't send; compares with legacy sent messages
4. **Cutover** (highest risk — separate maintenance window):
   - Disable legacy scheduler
   - Verify 0 deliveries from legacy for 10 min
   - Enable Processor delivery
   - Monitor: delivery success rate, latency, duplicates
5. **Rollback**: Reverse flags, verify legacy resumes

### Exit Gate
- Shadow parity: 100% delivery list match (7 days)
- Production: 0 duplicate deliveries, success rate ≥ 99.5%
- Idempotency verified: retry doesn't double-send
- Rollback rehearsed and timed (< 3 min)

---

## Capability 6: Grid Reporter (Separate Service)

### Current State
- Separate `grid-reporter` service with its own Deye polling
- Runs independently, writes to MongoDB
- Has its own `ClientWorker` per client

### Evaluation Needed
- Does it duplicate Deye polling from `back-end`?
- Should it be merged into Processor, or kept separate with its own lease?
- If merged: Processor needs multi-tenant Deye polling (different credentials per client)

**Decision**: Defer to after Phase 6.5. Document current behavior, evaluate consolidation.

---

## Cross-Cutting Concerns

### Service-to-Service Auth
- **Processor**: Validates mTLS cert + JWT (service identity)
- **Back-end**: Calls Processor with service cert + user token (delegated)
- **Token exchange**: Back-end calls Identity `/token/exchange` → gets Processor-audience token

### Contract Testing
- **Pact** or **Schemathesis** for each Processor endpoint
- Run in CI for both Provider (Processor) and Consumer (Back-end)
- Versioned: `v1`, `v2` — breaking changes = new version

### Observability (Per Capability)
| Metric | Capability |
|--------|------------|
| `processor_capability_{name}_duration_seconds` | All |
| `processor_capability_{name}_errors_total` | All |
| `processor_capability_{name}_cutover_status` | Gauge (0=legacy, 1=processor) |

### Rollback Procedure Template (Per Capability)
```markdown
## Rollback: {Capability Name}

**Trigger**: {Specific condition, e.g., error rate > 1% for 5 min}

**Steps**:
1. Set `{CAPABILITY}_VIA_PROCESSOR=false` (or equivalent flag)
2. Verify Processor stops processing (metrics, logs)
3. Set `{CAPABILITY}_LEGACY_ENABLED=true`
4. Verify legacy resumes (metrics, logs)
4. Confirm: {Specific verification, e.g., "measurements appearing in MongoDB"}

**Owner**: {Team/Person}
**Max Time**: {e.g., 3 min}
**Communication**: #incidents channel
```

---

## Deployment Order & Dependencies

```
Phase 6.1 (Message Preview)     ──► Independent, can start after Phase 5
Phase 6.2 (Admin CRUD)          ──► After 6.1 (uses same auth pattern)
Phase 6.3 (Deye Polling)        ──► After 6.2 (Processor owns MongoDB writes)
Phase 6.4 (Cleanup Jobs)        ──► After 6.3 (same scheduler)
Phase 6.5 (Message Delivery)    ──► Last (highest risk, depends on generator from 6.1)
Phase 6.6 (Grid Reporter)       ──► Evaluate separately
```

**Parallelizable**: 6.1 and 6.2 can overlap (different code paths)

---

## Test Checklist (Per Capability)

- [ ] Unit: Processor endpoint/logic matches legacy behavior
- [ ] Contract: OpenAPI spec validated, consumer tests pass
- [ ] Integration: Back-end → Processor → MongoDB round-trip
- [ ] Shadow: 7-day parity run, mismatch rate < 0.1%
- [ ] Cutover: Flag toggle works, verification steps documented
- [ ] Rollback: Drill completed < max time, no data loss
- [ ] Load: Processor handles 3× peak load for capability
- [ ] Chaos: Processor crashes mid-operation → lease transfer, no corruption
- [ ] Auth: Unauthorized requests rejected (401/403)
- [ ] Audit: Mutations logged with actor, action, resource