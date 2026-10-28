# Migration Plan — Concrete Thresholds & Spec References

This document supplements `migration-plan.md` with measurable exit criteria and links to detailed phase specifications.

## Phase Specs Index

| Phase | Spec Document | Status |
|-------|---------------|--------|
| 0 | (Baselines — no separate spec) | — |
| 1 | [phase-1-spec.md](phase-1-spec.md) | Drafted |
| 2 | [phase-2-spec.md](phase-2-spec.md) | Drafted |
| 3 | [phase-3-spec.md](phase-3-spec.md) | Drafted |
| 4-5 | [phase-4-5-spec.md](phase-4-5-spec.md) | Drafted |
| 6 | [phase-6-spec.md](phase-6-spec.md) | Drafted |
| 7 | [phase-7-spec.md](phase-7-spec.md) | Drafted |
| 8 | [phase-8-spec.md](phase-8-spec.md) | Drafted |
| 9 | (Retirement — no separate spec) | — |

## Supporting Documents

| Document | Purpose |
|----------|---------|
| [snapshot-schema.json](snapshot-schema.json) | JSON Schema for DashboardSnapshot v1 (buildings, config, outagesSchedules) |
| [redis-conventions.md](redis-conventions.md) | Redis keys, channels, Lua scripts (CAS + lease fence), monitoring |

---

## Concrete Exit Thresholds (Per Phase)

### Phase 0: Baselines
| Metric | Baseline Target | Measurement |
|--------|-----------------|-------------|
| Dashboard API p99 latency | < 500ms | 7 days production |
| Dashboard API error rate | < 0.1% | 7 days production |
| SSE connection count | Baseline recorded | 7 days production |
| Scheduled job success rate | 100% | 7 days production |
| Snapshot freshness (legacy) | < 30s | 7 days production |

### Phase 1: Publish Snapshots
| Criterion | Threshold | Window |
|-----------|-----------|--------|
| Snapshot parity (field-level vs legacy API) | ≥ 99.9% | 24h production |
| Snapshot write success rate | 100% (0 errors) | 24h production |
| Version monotonicity | No decreases, no gaps > 1 within epoch | 24h production |
| Epoch stability | No unexpected increments | 24h production |
| Snapshot age (max) | < 300s (5 min) | Continuous |
| Refresh latency (request → notification) | p99 < 10s | 24h production |
| Empty-cache rebuild test | Passes | Staging + 1 prod test |

### Phase 2: App Back-end Redis Reads (Shadow → Enabled)
| Criterion | Threshold | Window |
|-----------|-----------|--------|
| Shadow parity (field-level, sampled) | ≥ 99.9% | 24h production at 100% rollout |
| p99 latency delta (Redis vs legacy) | < 50ms | 24h production |
| Freshness delta (snapshot age vs legacy) | < 5s | 24h production |
| Error rate (Redis path) | < 0.1% | 24h production |
| Version lag | ≤ 1 for 99.9% of time | 24h production |
| Restart/reconnect recovery | < 2s, no data loss | Staging + 1 prod test |
| Mobile API contract compatibility | 100% | Contract test suite |

### Phase 3: Back-end + App-back-end SSE Migration
| Criterion | Threshold | Window |
|-----------|-----------|--------|
| SSE latency (notification → client) | p99 < 500ms | 24h production |
| SSE reconnect recovery | < 2s, full snapshot received | 10 test reconnects |
| Connection stability | < 0.1% unexpected disconnects/min | 24h production |
| Authorization filtering | 0 admin fields leaked to public | Automated test |
| sse-back-end traffic | 0 required connections for 1 week | 1 week observation |
| REST API parity (vs Phase 2) | 100% field-level match | Contract tests |
| Backward compatibility | Existing web UI works without changes | E2E test |

### Phase 4: Processing Shadow Mode
| Criterion | Threshold | Window |
|-----------|-----------|--------|
| Shadow parity (field-level vs production) | ≥ 99.95% | 24h production |
| Build success rate | 100% (0 crashes) | 24h production |
| Build duration p99 | < 10s | 24h production |
| Refresh latency p99 (trigger → snapshot ready) | < 30s | 24h production |
| Lease stability | 0 unexpected losses | 24h production |
| Empty-cache rebuild | Passes | Staging + 1 prod test |
| Drift detection | 0 undetected drifts | 24h production |
| Shadow keys isolated | No production key access | Verified |

### Phase 5: Processing Cutover
| Criterion | Threshold | Window |
|-----------|-----------|--------|
| All BFFs on processor snapshots | 100% | Immediate |
| Parity vs legacy (pre-cutover) | ≥ 99.99% | 1h post-cutover |
| Freshness (snapshot age) | < 60s | Continuous |
| Version monotonicity | No gaps, no decreases | Continuous |
| Rollback rehearsed | < 2 min | Staging drill |
| Legacy publish code disabled | Flag off, no writes | 24h post-cutover |
| **Legacy calculation code REMAINS** | Not removed | Phase 9 |

### Phase 6: Capability Migration (Per Capability)
| Capability | Parity Threshold | Cutover Window | Rollback Max |
|------------|------------------|----------------|--------------|
| Message Preview | ≥ 99.9% (24h shadow) | 1 deploy | 2 min |
| Admin CRUD (per resource) | ≥ 99.9% (24h shadow) | 1 deploy/resource | 2 min |
| Deye Polling | 0 data loss, interval p99 < 150s | 1 deploy | 3 min |
| Cleanup Jobs | 100% shadow match (7 days) | 1 deploy/job | 2 min |
| Message Delivery (Telegram + FCM) | 100% shadow match (7 days), 0 duplicates | 1 deploy | 3 min |
| Grid Reporter | Evaluate separately | — | — |
| Outage Schedule Fetch | 100% shadow match (7 days) | 1 deploy | 2 min |
| Station Sync (3-hourly) | 100% shadow match (7 days) | 1 deploy | 2 min |
| Ping Check (ext-device) | 100% shadow match (7 days) | 1 deploy | 2 min |

### Phase 7: Identity Migration (Admin Only)
| Phase | Criterion | Threshold |
|-------|-----------|-----------|
| 7a (Deploy) | OIDC flows work, load test | 100 auth req/s, p99 < 200ms |
| 7b (Admin) | Login success, token exchange | ≥ 99.9%, 100% |
| 7c (Legacy removal) | 0 legacy validations | 14 days |

### Phase 8: Host Separation
| Criterion | Threshold |
|-----------|-----------|
| Public app bundle size | < 500KB gzipped |
| Admin app bundle size | < 1MB gzipped |
| API contract parity (app-back-end vs legacy) | 100% |
| Shadow parity (24h production) | ≥ 99.99% |
| Mobile API unchanged | Contract tests pass |
| Auth cookie isolation (admin host-only) | Verified (no cross-host leakage) |
| SSE works on both hosts | Verified |

### Phase 9: Retirement
| Criterion | Threshold |
|-----------|-----------|
| Legacy dashboard computation | 0 executions in logs (7 days) |
| Legacy scheduled jobs | 0 executions in logs (7 days) |
| Legacy MongoDB credentials | Revoked |
| Legacy SSE service | Scaled to 0, deployment removed |
| Migration flags | All removed from code |
| Runbooks updated | Redis failure, stale projection, processor down, job ownership |

---

## Cross-Phase Production Gate (Enhanced)

Before **each** production flag/routing cutover, record in a **Cutover Checklist**:

```markdown
## Cutover Checklist: {Phase/Capability}

**Date**: 
**Owner**: 
**Reviewer**: 

### Change Details
- Service/Version: 
- Traffic Scope: (e.g., "100% of app-back-end instances", "admin.svitlo-power.pp.ua host")
- Feature Flag: 

### Thresholds (from table above)
- Parity: 
- Latency: 
- Freshness: 
- Error Rate: 

### Rollback Plan
- Trigger: (e.g., "error rate > 0.5% for 5 min")
- Steps: (numbered, with commands)
- Max Time: 
- Verification: 

### Observers
- Primary: 
- Secondary: 
- Communication Channel: 

### Observation Period
- Duration: (e.g., "24h", "1 week")
- Success Criteria: 

### Sign-off
- [ ] Owner confirms thresholds met
- [ ] Reviewer approves
- [ ] Rollback drill completed in staging
```

---

## Rollback Drill Schedule

| Phase | Drill Deadline | Environment |
|-------|----------------|-------------|
| 1 | Before production deploy | Staging |
| 2 | Before 100% rollout | Staging |
| 3 | Before sse-back-end scale-down | Staging |
| 4 | Before Phase 5 cutover | Staging |
| 5 | **Day of cutover** (morning) | Staging |
| 6 (each) | Before capability cutover | Staging |
| 7 (admin) | Before admin cutover | Staging |
| 8 | Before host DNS switch | Staging |

**Drill must include**: Full rollback procedure execution, timing, verification steps.

---

## Capacity & Load Test Gates

| Service | Test | Threshold | When |
|---------|------|-----------|------|
| Processor (Phase 4) | 3× peak projection rate | p99 < 200ms, 0 errors | Before Phase 5 |
| Processor (Phase 6) | 3× peak per capability | p99 < 500ms, 0 errors | Before each capability |
| Identity Service | 100 auth req/s | p99 < 200ms | Phase 7a |
| App Back-end | 10k req/s (public) | p99 < 300ms | Phase 8 |
| Admin Back-end | 1k req/s | p99 < 500ms | Phase 8 |
| Redis | 5k ops/s (read + pub/sub) | p99 < 10ms | Phase 1 |

---

## Observability Requirements (Must Exist Before Phase 2)

### Dashboards
1. **Snapshot Health**: Epoch, version, age, write latency, error rate
2. **Consumer Health**: Version lag, reconciliation status, stale snapshot alert
3. **SSE Health**: Active connections, event latency, reconnect rate, filtered fields
4. **Processor Health**: Build duration, trigger latency, lease status, shadow parity
5. **Identity Health**: Auth success rate, token exchange latency, JWKS cache hit rate

### Alerts (Critical)
| Alert | Condition | Severity |
|-------|-----------|----------|
| SnapshotStale | Age > 300s | Critical |
| VersionLag | Consumer lag > 1 for > 60s | Critical |
| ProcessorDown | Lease not renewed > 60s | Critical |
| ParityDegraded | Shadow mismatch rate > 0.1% | Warning |
| SSEConnectionsDrop | > 10% drop in 5 min | Warning |
| IdentityServiceDown | Health check failing > 1 min | Critical |

---

## Dependency Graph

```
Phase 0 (Baselines)
    │
    ├─► Phase 1 (Publish Snapshots) ──► Phase 2 (App BFF Redis Reads)
    │                                        │
    │                                        ├─► Phase 3 (Back-end + App-back-end SSE)
    │                                        │
    │                                        └─► Phase 8 (Host Split) ◄── Phase 7 (Identity)
    │
    └─► Phase 4 (Processor Shadow) ──► Phase 5 (Processor Cutover)
                                             │
                                             └─► Phase 6 (Capabilities)
                                                      │
                                                      ├─► 6.1 Message Preview
                                                      ├─► 6.2 Admin CRUD
                                                      ├─► 6.3 Deye Polling + Station Sync + Outage Schedule Fetch
                                                      ├─► 6.4 Cleanup Jobs + Ping Check
                                                      ├─► 6.5 Message Delivery
                                                      └─► 6.6 Grid Reporter (evaluate)

Phase 7 (Identity) starts **with Phase 1** — independent timeline
Phase 8 (Host Split) requires Phase 3 (SSE) + Phase 7 (Admin Auth) + Phase 2 (App BFF APIs)
```

---

## Definition of Done (Per Phase)

A phase is **Done** when:
1. All exit gate thresholds met (measured, documented)
2. Rollback drill completed in staging (< max time)
3. Cutover checklist signed off
4. Observability dashboards/alerts active
5. Runbook updated for new failure modes
6. Legacy code for this phase marked for removal (Phase 9)

---

## Next Steps

1. **Review & approve** phase specs with team
2. **Implement Phase 0** baselines (instrumentation)
3. **Publish snapshot schema** + Redis conventions to schema registry
4. **Begin Phase 1** implementation (snapshot service in back-end)
5. **Kick off Phase 7a** (Identity Service) in parallel
6. **Schedule Phase 5 cutover rehearsal** (target: 2 weeks before planned cutover)