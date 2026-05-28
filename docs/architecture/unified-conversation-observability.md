# Unified Conversation & Observability (E2.0)

**Status:** design-only — **no runtime changes in E2.0**  
**Date:** 2026-05-28  
**Verdict:** **PASS WITH NOTES** (see §12)

**Canonical runtime (unchanged):** `alpstein_postgres` → `alpstein_backend` → `alpstein_n8n_compose` → workflow **`alpstein-customer-ingress`** (`aYrRmAGKhP4TJbG9`) per [`runtime-map.md`](../ops/runtime-map.md).

**Child specs:**

| Document | Role |
|----------|------|
| [`specs/architecture/unified-conversation-model.md`](../../specs/architecture/unified-conversation-model.md) | Flow, conversation, message, governance |
| [`specs/observability/message-trace-lifecycle.md`](../../specs/observability/message-trace-lifecycle.md) | Trace stages, `message_traces`, correlation |
| [`docs/ops/message-debugging-runbook.md`](../ops/message-debugging-runbook.md) | Operator debugging order |
| [`unified-customer-ingress-workflow.md`](unified-customer-ingress-workflow.md) | E1 ingress topology |
| [`specs/architecture/observability-metadata.md`](../../specs/architecture/observability-metadata.md) | D1 metadata envelope (implemented partially) |

---

## 1. Strategic purpose

Phase **E1** unified **ingress** (Telegram + Website Chat → one n8n workflow → one backend webhook). Phase **E2** unifies **continuity and observability**:

- One **conversation model** per bot behavior (**flow**), not per channel alone.
- One **message trace** per inbound turn across n8n, backend, AI, and delivery.
- Clear separation: **flow config** (prompt inputs) vs **conversation history** (actual dialogue).
- Debuggable path when any channel fails — without new ports, containers, or workflows in E2.0.

---

## 2. Golden rule

> **One flow = one bot behavior.**

| Layer | Responsibility |
|-------|----------------|
| **Flow** | Identity of a bot scenario (`flow_key`, business-bound) |
| **Channel** | Transport adapter (Telegram, Website Chat, …) |
| **Conversation** | One customer dialogue inside **one flow** |
| **Message** | One event inside **one conversation** |
| **n8n** | Normalize, annotate `flow_key` / `business_id` / `channel`, deliver — **not** behavior brain |
| **Backend** | Orchestration, persistence, AI, tenant safety |

---

## 3. Current state review (E1.9 baseline)

### 3.1 Ingress (unified)

| Item | State |
|------|--------|
| Workflow | `alpstein-customer-ingress` active |
| Telegram | `ALPSTEIN_TELEGRAM_BUSINESS_ID` → `alpstein_ai_demo_001` (ops default) |
| Website | Unified path + kill switch |
| `correlation_id` | Generated in normalize (both branches in E1.8+ build) |
| `operator_business_context` | Set node after normalize — runtime behavior rules |

### 3.2 Database (existing)

| Table | Role in continuity / observability |
|-------|-----------------------------------|
| `conversations` | Session row; has `external_conversation_id` column **unused in lookup** |
| `messages` | History; idempotency `(business_id, external_message_id)` |
| `customers` | Channel-scoped identity |
| `prompt_runs` | AI audit; `metadata` JSON with correlation fields |
| `leads` | Opportunity; tied to `conversation_id` |

**No `flows` or `message_traces` tables yet.**

### 3.3 Backend behavior (gaps driving E2)

```text
ConversationService.get_or_create_open_conversation:
  lookup = (tenant_id, business_id, customer_id, channel)
  — does NOT use external_conversation_id
  — does NOT use flow_id
```

Implication: Website **new session** may reuse wrong open conversation if same `visitor_id` customer row and channel match. Telegram threads rely on customer id + channel, not `tg:{chat_id}` thread key.

### 3.4 Observability (partial)

| Capability | Status |
|------------|--------|
| `correlation_id` resolve | Implemented (`ObservabilityContext`) |
| `prompt_runs.metadata` | JSON-safe lineage |
| Langfuse | Dev wiring; compose path **WARN** in E0 |
| `n8n_execution_id` | Header supported; stored in metadata when present |
| End-to-end stage column | **Missing** |
| Delivery confirmation in DB | **Missing** |

---

## 4. Target architecture (E2)

```text
External channel
    → n8n trigger [received]
    → Normalize [normalized]  (+ correlation_id, channel metadata)
    → Add Business Context    (operator_business_context — runtime rules only)
    → POST Backend            [backend_posted]
         → resolve business + flow
         → get/create conversation (flow_id + channel + external_conversation_id)
         → save inbound message (flow-scoped idempotency)
         → AI orchestration    [ai_completed] → prompt_run
         → save outbound message
    ← webhook response          (correlation_id, conversation_id, message_id, …)
    → channel delivery        [reply_sent]
    → (optional) owner notify  (parallel sub-trace)
```

---

## 5. Unified conversation model (summary)

Full detail: [`unified-conversation-model.md`](../../specs/architecture/unified-conversation-model.md).

### 5.1 Flow (new)

- `flows` table: `flow_key`, `flow_name`, `status`, `tenant_id`, `business_id`.
- n8n passes `flow_key` (optional MVP: default flow per `business_id`).

### 5.2 Conversation

Required: `flow_id`. Primary lookup: `(flow_id, channel, external_conversation_id)`.  
Fields: `identity_confidence`, `first_seen_at`, `last_seen_at`, `source_attribution`, `channel_metadata`.

### 5.3 Message

Required: `conversation_id`. Target idempotency: `(flow_id, channel, external_message_id)`.  
`normalized_payload` for safe subset; `raw_payload` audit-only.

### 5.4 Database Separation & Flow Governance

See spec §4 — examples A–D, anti-patterns, enforcement matrix.

---

## 6. Observability model (summary)

Full detail: [`message-trace-lifecycle.md`](../../specs/observability/message-trace-lifecycle.md).

| Field | Purpose |
|-------|---------|
| `correlation_id` | Single turn correlation |
| `n8n_execution_id` | n8n UI lookup |
| `backend_request_id` | Backend log correlation |
| `prompt_run_id` | AI audit link |
| `flow_id` | Bot behavior filter |
| `conversation_id` / `message_id` | DB lineage |
| Latencies | backend / AI / delivery ms |
| `status` | Lifecycle stage enum |

---

## 7. Database changes (future — not E2.0)

| Migration | Change |
|-----------|--------|
| **E2.1** | `CREATE TABLE flows`; backfill one flow per business |
| **E2.2** | `conversations.flow_id NOT NULL`; indexes; backfill from default flow |
| **E2.3** | `messages.flow_id`; new partial unique on `(flow_id, channel, external_message_id)`; deprecate business-only unique |
| **E2.4** | `CREATE TABLE message_traces` |
| **E2.5** | Optional `conversations` partial unique on open threads |

**Retention / redaction:**

- `raw_payload`: keep in `messages` for audit; exclude from traces/logs.
- `message_traces.metadata`: bounded envelope only.
- `prompt_runs.final_prompt`: dev Langfuse only; production logging truncated.

---

## 8. API contract changes (proposed — future)

### 8.1 Request (`POST /api/v1/webhook/message`)

| Field | Change |
|-------|--------|
| `flow_key` | **Optional** string; resolve to `flow_id`; default flow for business if omitted |
| Existing fields | Unchanged — backward compatible |

No breaking change if `flow_key` optional with safe default.

### 8.2 Response (`data`)

| Field | Today | Proposed |
|-------|-------|----------|
| `correlation_id` | returned | keep |
| `conversation.id` | may be present | **always** on success |
| `message.id` | partial | **inbound** `message_id` always |
| `outbound_message_id` | optional | when AI reply persisted |
| `prompt_run_id` | optional | for Langfuse/debug |
| `is_duplicate` | yes | keep |
| `trace_id` | — | `message_traces.id` when E2.4 live |

n8n can log delivery failures with `correlation_id` + `conversation_id` without parsing prompts.

---

## 9. n8n changes (design only)

| Item | Design |
|------|--------|
| `correlation_id` | Already in unified normalize — **keep** |
| `X-N8n-Execution-Id` | **Required** on POST Backend header |
| `flow_key` | New Set field or env `ALPSTEIN_FLOW_KEY` per branch (Telegram vs Website may differ later) |
| Delivery observability | Function node after Send/Respond: log stage `reply_sent` with correlation only |
| Owner notify | Log `owner_notify_*` with same `correlation_id`; do not merge into customer trace row |
| No new workflow | Extend **`alpstein-customer-ingress`** in E2.1+ implementation task |

**Do not** move AI prompts or flow config into n8n static nodes beyond `operator_business_context`.

---

## 10. Operational debugging

Operator runbook: [`message-debugging-runbook.md`](../ops/message-debugging-runbook.md).

**First checks:**

1. `correlation_id` from widget response / n8n execution / backend JSON.
2. n8n execution `alpstein-customer-ingress` on **`127.0.0.1:15679`** (see runtime-map).
3. Backend health `GET http://backend:8000/api/v1/health/ready`.
4. DB: `messages` + `prompt_runs` by `correlation_id` in metadata (today); `message_traces` (future).

---

## 11. Implementation roadmap (post E2.0)

| Slice | Owner skill | Deliverable |
|-------|-------------|-------------|
| E2.1 | database-architect | `flows` migration + seed |
| E2.2 | backend-engineer | ConversationService lookup + `flow_id` |
| E2.3 | database-architect | Message idempotency migration |
| E2.4 | backend-engineer | `message_traces` write path |
| E2.5 | api-designer | webhooks.md response fields |
| E2.6 | n8n-integration-engineer | `flow_key` + delivery logging |
| E2.7 | ops-release-manager | Gate tests + runbook evidence |

---

## 12. Verdict: PASS WITH NOTES

| Criterion | Result |
|-----------|--------|
| Design complete | **Yes** |
| Respects OPS-H1 (no new ports/containers) | **Yes** |
| Flow governance documented | **Yes** |
| Blockers for implementation | **None** — sequence E2.1→E2.7 |

**Notes:**

1. **`external_conversation_id` not used in code** — E2.2 must fix before Website session semantics match spec.
2. **`flow_id` requires migration** — until then, `business_id` is a weak proxy for flow (acceptable for demo only if one behavior per business).
3. **Langfuse on compose** — operational, not model; track in E2.7 verification.
4. **Optional:** clear Alpstein Telegram message history before E2.2 cutover tests (same scoped DELETE pattern as prior demo cleanup).

---

## 13. Risks and open questions

| ID | Question | Recommendation |
|----|----------|----------------|
| Q1 | Multiple open conversations per `(flow, channel, external_conversation_id)`? | Partial unique on open statuses only |
| Q2 | Default flow when `flow_key` omitted? | Single `default` flow per business |
| Q3 | Migrate idempotency index before or after flow backfill? | Backfill `flow_id` on messages first, then swap index |
| Q4 | Store `reply_sent` from n8n via callback webhook? | Defer — E2.4 optional PATCH or n8n execution log sufficient for MVP |
| Q5 | Per-flow AI profiles vs per-business? | E2.1 keep business-scoped profiles; flow selects profile in E3+ |
