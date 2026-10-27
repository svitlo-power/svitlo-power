# Architecture Migration — Deliverables Index

This directory contains the complete specification set for the incremental migration from the current monolithic deployment to the target architecture defined in [ADR 0001](../adr/0001-service-boundaries-and-dashboard-data-flow.md).

## Core Documents

| File | Description | Start Here? |
|------|-------------|-------------|
| [migration-plan.md](migration-plan.md) | High-level phase overview (updated with disposable-cache semantics, parallel identity work) | ✅ Yes |
| [migration-thresholds.md](migration-thresholds.md) | Concrete exit criteria, thresholds, cutover checklists, dependency graph | ✅ Yes |

## Phase Specifications (Detailed Implementation Guides)

| Phase | File | Covers |
|-------|------|--------|
| 1 | [phase-1-spec.md](phase-1-spec.md) | Publish dashboard/outage snapshots to Redis from existing back-end |
| 2 | [phase-2-spec.md](phase-2-spec.md) | App back-end reads from Redis (shadow mode → gradual enable) |
| 3 | [phase-3-spec.md](phase-3-spec.md) | Admin back-end + SSE migration; retire sse-back-end |
| 4-5 | [phase-4-5-spec.md](phase-4-5-spec.md) | Processing service shadow mode → snapshot ownership cutover |
| 6 | [phase-6-spec.md](phase-6-spec.md) | Move remaining capabilities: preview, CRUD, Deye polling, cleanup, delivery |
| 7 | [phase-7-spec.md](phase-7-spec.md) | Identity Service (OIDC) migration in parallel |
| 8 | [phase-8-spec.md](phase-8-spec.md) | Separate public/admin front-ends, host routing, API migration |

## Contracts & Conventions

| File | Description |
|------|-------------|
| [snapshot-schema.json](snapshot-schema.json) | JSON Schema (draft-07) for DashboardSnapshot v1 — used by all phases |
| [redis-conventions.md](redis-conventions.md) | Redis key/channel naming, Lua scripts for atomic write + lease, monitoring |

## ADR Reference

| File | Description |
|------|-------------|
| [../adr/0001-service-boundaries-and-dashboard-data-flow.md](../adr/0001-service-boundaries-and-dashboard-data-flow.md) | Target architecture decision record |

---

## Quick Start: Implementation Order

```
Week 1-2:  Phase 0 (Baselines) + Phase 1 (Publish Snapshots)
           └─► Parallel: Phase 7a (Identity Service deploy)

Week 3-4:  Phase 2 (App BFF Redis Reads)
           └─► Phase 7b (Admin Identity Migration)

Week 5-6:  Phase 3 (Admin BFF + SSE)
           └─► Phase 7c (Public Identity Migration)

Week 7-8:  Phase 4 (Processor Shadow)
           └─► Phase 7d (Mobile Identity Migration)

Week 9:    Phase 5 (Processor Cutover) — scheduled maintenance window

Week 10+:  Phase 6 (Capabilities, one per week)
           Phase 8 (Host Split) — after Phase 3 + 7c complete
           Phase 9 (Retirement) — after all capabilities moved
```

## Key Architectural Decisions (Summary)

1. **Disposable Redis Cache** — Snapshots are rebuildable; Redis loss ≠ data loss
2. **Single Writer** — Processing service holds lease; legacy back-end quiesced before cutover
3. **Event-Driven Refresh** — Change detection + coalesced cache-miss refresh (no arbitrary polling)
4. **Parallel Identity Migration** — Starts Week 1, doesn't block dashboard migration
5. **Capability-by-Capability** — Each background job moved independently with rollback
6. **Host Separation Last** — After APIs and auth are separated

## Required Before Phase 1 Deploy

- [ ] `snapshot-schema.json` published to schema registry (or bundled)
- [ ] `redis-conventions.md` Lua scripts registered in Redis
- [ ] Pydantic models generated from schema (both back-end and processor)
- [ ] Feature flag infrastructure ready
- [ ] Baseline metrics (Phase 0) collected for 7 days
- [ ] Cutover checklist template approved

## Rollback Discipline

**Every phase** must have:
- Feature flag for instant disable
- Documented rollback procedure with max time
- Staging drill completed before production
- Observation period with defined success criteria

---

## File Tree

```
docs/architecture/
├── migration-plan.md              # High-level plan (updated)
├── migration-thresholds.md        # Concrete thresholds & checklists
├── snapshot-schema.json           # DashboardSnapshot v1 JSON Schema
├── redis-conventions.md           # Redis keys, channels, Lua scripts
├── phase-1-spec.md                # Publish snapshots
├── phase-2-spec.md                # App BFF Redis reads
├── phase-3-spec.md                # Admin BFF + SSE
├── phase-4-5-spec.md              # Processor shadow → cutover
├── phase-6-spec.md                # Capability migration
├── phase-7-spec.md                # Identity Service migration
└── phase-8-spec.md                # Host separation
```

---

## Next Actions

1. **Team Review** — Walk through `migration-plan.md` + `migration-thresholds.md` with stakeholders
2. **Schema Registry** — Publish `snapshot-schema.json` (Confluent, Apicurio, or Git-based)
3. **Redis Scripts** — Register Lua scripts from `redis-conventions.md` in all environments
4. **Phase 0 Kickoff** — Instrumentation tickets for baseline collection
5. **Phase 7a Kickoff** — Identity Service scaffold (NestJS + OIDC provider)
6. **Cutover Calendar** — Schedule Phase 5 maintenance window (target 8-10 weeks out)