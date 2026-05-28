# T-e2.0 — Unified Conversation + Observability Design

**Status:** done (design-only)  
**Date:** 2026-05-28  
**Verdict:** **PASS WITH NOTES**

---

## Goal

Design E2 layer: unified conversation continuity + end-to-end observability across channels after E1 unified ingress. **No runtime changes** in this task.

---

## Deliverables

| File | Purpose |
|------|---------|
| [`docs/architecture/unified-conversation-observability.md`](../../docs/architecture/unified-conversation-observability.md) | Master E2 design + verdict |
| [`specs/architecture/unified-conversation-model.md`](../../specs/architecture/unified-conversation-model.md) | Flow/conversation/message + governance |
| [`specs/observability/message-trace-lifecycle.md`](../../specs/observability/message-trace-lifecycle.md) | Trace stages + `message_traces` |
| [`docs/ops/message-debugging-runbook.md`](../../docs/ops/message-debugging-runbook.md) | Ops debugging order |
| [`docs/project-status/current-state.md`](../../docs/project-status/current-state.md) | E2.0 noted |
| [`docs/project-status/next-steps.md`](../../docs/project-status/next-steps.md) | E2.1+ queue |

---

## Key decisions

1. **Golden rule:** one flow = one bot behavior.
2. **Option B retained:** separate businesses (`demo_barbershop_001`, `alpstein_ai_demo_001`); flows table adds behavior dimension within business.
3. **New tables (future):** `flows`, `message_traces`.
4. **Conversation lookup target:** `(flow_id, channel, external_conversation_id)`.
5. **Idempotency target:** `(flow_id, channel, external_message_id)`.
6. **API:** optional `flow_key` on webhook; response adds stable `conversation_id` / `message_id` / `trace_id`.
7. **n8n:** pass `flow_key`, require `X-N8n-Execution-Id`; no new workflow in E2.0.

---

## Current gaps documented

- `ConversationService` does not use `external_conversation_id`.
- No `flow_id` column.
- No `message_traces` table / `reply_sent` persistence.
- Idempotency scoped to `business_id` only.

---

## Next implementation slices

| ID | Task |
|----|------|
| E2.1 | `flows` migration + backfill |
| E2.2 | ConversationService + `flow_id` |
| E2.3 | Message idempotency index migration |
| E2.4 | `message_traces` persistence |
| E2.5 | API spec + response fields |
| E2.6 | n8n `flow_key` + delivery logging |
| E2.7 | Ops gate + Langfuse verification on compose |

---

## Constraints respected

- No backend code, migrations, n8n workflow, ports, containers, env, or production cutover in E2.0.
