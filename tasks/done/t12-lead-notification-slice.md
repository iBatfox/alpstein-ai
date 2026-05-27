# T12 — Lead & notification slice (implementation plan)

**Status:** todo — design approved pending review  
**Date:** 2026-05-24  
**Design reference:** [`docs/project-status/t12-lead-notification-plan.md`](../../docs/project-status/t12-lead-notification-plan.md)

**Goal:** Persist leads on inbound customer messages and return accurate `lead_created` / `lead_updated` / `notify_owner` (+ optional `notification`) from `POST /api/v1/webhook/message`.

**Depends on:** T10 webhook, T11 AI path (complete).

**Out of scope:** n8n workflow changes, CRM/spreadsheet routing, vector/memory, AI-only lead qualification.

**Architecture:** `LeadService` + `AsyncSession` (T4–T11 pattern). No generic repository layer.

---

## Spec alignment

- **In MVP:** yes — `specs/mvp/mvp-scope.md` §4.7, §4.9
- **Primary specs:** `lead-creation-flow.md`, `notification-flow.md`, `incoming-message-flow.md`, `webhooks.md`, `api-endpoints.md`, `database-schema.md` §9

---

## Task list

### P0 — Critical path

| ID | Task | Depends on | Done when | Suggested skill | Review gate |
|----|------|------------|-----------|-----------------|-------------|
| **T12.1** | Alembic `leads` table + `Lead` SQLAlchemy model per `database-schema.md` §9 (indexes on `tenant_id`, `business_id`, `customer_id`, `status`, `created_at`) | T11 | Migration up/down clean; model/migration tests pass; `test_alembic_migration.py` updated | **alpstein-migration-engineer** / **alpstein-database-architect** | Migration review |
| **T12.2** | `LeadService`: `find_active_lead(tenant_id, business_id, customer_id, conversation_id)` for statuses `new\|in_progress\|contacted`; `create_lead(...)`; `update_lead(...)` with tenant validation | T12.1 | pytest: create, update, active lookup, cross-tenant isolation, closed lead allows new create | **alpstein-backend-engineer** | **Gate 1** — reviewer after T12.2 |
| **T12.3** | `LeadNotificationPolicy` (or equivalent pure module): input = lead outcome + `is_duplicate` + AI outcome (`used_fallback`, etc.) + inbound text; output = `notify_owner`, `notification.type`, `notification.priority` per design plan §3 | — | pytest: truth table cases (duplicate, new lead, update, urgent, ai_failure, handoff keyword) | **alpstein-backend-engineer** | — |
| **T12.4** | MVP keyword heuristics: urgent + human-handoff substring lists (config constants, not AI); integrate into T12.3 | T12.3 | pytest: keyword match / no-match | **alpstein-backend-engineer** | — |
| **T12.5** | Extend response layer: Pydantic `WebhookLeadSummary`, `WebhookNotificationPayload`; add `lead_updated` to route payload; include `lead` / `notification` when set | T12.3 | **done** — see `tasks/done/T12.5-webhook-response-schemas.md` | **alpstein-api-designer** + **alpstein-backend-engineer** | Contract review |
| **T12.6** | Wire `WebhookMessageService`: after inbound save, if `not is_duplicate` → `LeadService.create_or_update_for_message(...)`; after AI path → apply T12.3 policy; populate `WebhookMessageProcessResult` | T12.2–T12.5, T11 | Duplicate skips lead; new message creates lead; follow-up updates; flags match design plan | **alpstein-backend-engineer** | **Gate 2** — reviewer after T12.6 |
| **T12.7** | Integration tests: webhook route end-to-end for new lead + notify, lead update + no notify, duplicate + no lead/notify, AI fallback + `ai_failure` notify; mock Gateway | T12.6 | All T12 scenarios green alongside T11 regression | **alpstein-backend-engineer** | **Gate 3** — **alpstein-reviewer** |
| **T12.8** | Update `docs/project-status/{completed,current-state,next-steps}.md` | T12.7 | Docs reflect lead/notify path | **alpstein-backend-engineer** | — |

### P1 — Defer (post-T12 MVP hardening)

| ID | Task | Depends on | Done when |
|----|------|------------|-----------|
| **T12.9** | Optional AI enrichment: populate `service_requested` / `ai_summary` on lead from orchestration metadata | T12.6 | Enrichment only when AI succeeds; backend still owns create/update |
| **T12.10** | `is_ai_active=false` path: skip Gateway, handoff-safe customer text, notify rules documented | T12.6 | pytest for inactive conversation flag |

### Parallel / not T12

| ID | Task | Notes |
|----|------|--------|
| **T10-F3** | `IntegrityError` duplicate handling at webhook boundary | Same lead/notify rules as `is_duplicate=true` when implemented |
| **T13** (proposed) | n8n notification + reply workflows consuming T12 contract | Separate n8n slice — **no workflow changes in T12** |

---

## Processing order (WebhookMessageService)

```text
resolve business → customer → conversation
→ save incoming message
→ IF NOT is_duplicate: LeadService create_or_update
→ AI reply path (T11)
→ LeadNotificationPolicy.decide(...)
→ return WebhookMessageProcessResult
```

Lead persistence **does not** wait for AI success.

---

## Idempotency checklist (implementation)

- [ ] `is_duplicate=true` → no lead write, `notify_owner=false`
- [ ] Active lead lookup before insert
- [ ] `lead_created` and `lead_updated` mutually exclusive per message
- [ ] T10-F3 (when done) → same as duplicate

---

## Dependency graph

```text
T11 ─► T12.1 ─► T12.2 ─┬─► T12.6 ─► T12.7 ─► T12.8
T12.3 ─► T12.4 ─┤
T12.3 ─► T12.5 ─┘
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| Lead on duplicate | Gate lead step on `is_duplicate` — T12.6, T12.7 |
| Notify on routine update | T12.3 truth table tests |
| Response contract drift | T12.5 + api-designer review |
| Repository abstraction | Explicitly forbidden — service + session only |

---

## Recommended next task

**T12.1** — `leads` migration + model. Blocks all lead/notify implementation.

---

## n8n handoff (design only — implement in T13)

Backend returns complete JSON; n8n branches on `notify_owner` only. See design plan §8.
