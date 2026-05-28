# Message Trace Lifecycle (E2.0 — spec)

**Status:** design-only  
**Date:** 2026-05-28  
**Companion:** [`observability-metadata.md`](../architecture/observability-metadata.md), [`unified-conversation-model.md`](../architecture/unified-conversation-model.md)

---

## 1. Purpose

Define **end-to-end observability** for every inbound customer turn from external channel → n8n → backend → AI → outbound delivery, with a single **`correlation_id`** and explicit **stage status** suitable for ops debugging and Langfuse alignment.

**Out of scope (E2.0):** implementation, new ports, new workflows.

---

## 2. Trace anchor: one inbound turn

Each customer message that triggers `POST /api/v1/webhook/message` gets:

| Anchor | Source of truth |
|--------|-----------------|
| `correlation_id` | n8n-generated UUID (body + `X-Correlation-Id`) or backend-resolved |
| `n8n_execution_id` | n8n HTTP header `X-N8n-Execution-Id` (unified ingress — both channels) |
| `flow_id` / `flow_key` | Resolved after business + flow lookup (future explicit; today implicit per business) |
| `conversation_id` | After conversation resolve |
| `inbound_message_id` | After customer message persist |
| `prompt_run_id` | After AI gateway call |
| `outbound_message_id` | After AI message persist (if not duplicate-only short circuit) |

---

## 3. Lifecycle stages

```text
received → normalized → backend_posted → ai_completed → reply_sent
                ↘ failed (any stage)
```

| Stage | Actor | Meaning | Evidence today | Evidence target (E2+) |
|-------|-------|---------|----------------|------------------------|
| `received` | Provider | Raw webhook hit n8n trigger | n8n execution started | n8n execution + optional provider event id |
| `normalized` | n8n | Canonical ingress object built | Code node output in execution | `message_traces.normalized_at` |
| `backend_posted` | Backend | Webhook accepted, message saved | HTTP 200 + DB rows | `message_traces` + `prompt_runs.metadata` |
| `ai_completed` | Backend | Gateway returned or fallback used | `prompt_runs` row | `message_traces.ai_completed_at` |
| `reply_sent` | n8n | Customer delivery node succeeded | Telegram Send / Website Respond | n8n node success + optional `delivery_status` |
| `failed` | Any | Terminal error | n8n error branch / HTTP 4xx/5xx | `error_code`, `error_message`, `failed_stage` |

**Owner notify** is a **parallel branch**, not a stage in customer reply trace:

| Sub-trace | Trigger | Observability |
|-----------|---------|---------------|
| `owner_notify_attempted` | `data.notify_owner=true` | n8n node execution id + `notification_type` in metadata |
| `owner_notify_sent` / `owner_notify_failed` | Telegram owner bot | Log execution node; no PII in logs |

---

## 4. Proposed `message_traces` table (future migration)

One row per **inbound turn** (correlation_id unique per business scope).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | `message_trace_id` |
| `tenant_id`, `business_id`, `flow_id` | UUID FK | Required |
| `channel` | VARCHAR(50) | |
| `correlation_id` | UUID | **UNIQUE** per tenant or global UUID uniqueness |
| `conversation_id` | UUID FK | nullable until backend resolves |
| `inbound_message_id` | UUID FK | nullable until saved |
| `outbound_message_id` | UUID FK | nullable |
| `prompt_run_id` | UUID FK | nullable |
| `n8n_workflow_id` | VARCHAR(100) | |
| `n8n_execution_id` | VARCHAR(100) | Index for ops lookup |
| `backend_request_id` | VARCHAR(100) | Optional FastAPI request id / uvicorn |
| `status` | VARCHAR(50) | Current lifecycle stage |
| `failed_stage` | VARCHAR(50) | nullable |
| `error_code` | VARCHAR(100) | Stable codes only |
| `error_message` | TEXT | Truncated, no secrets |
| `channel_failure_details` | JSONB | Provider-specific safe subset |
| `backend_total_latency_ms` | INT | Webhook handler wall time |
| `ai_provider_latency_ms` | INT | From `prompt_runs.latency_ms` |
| `channel_delivery_latency_ms` | INT | n8n-reported or computed |
| `is_duplicate` | BOOLEAN | |
| `metadata` | JSONB | Bounded envelope per observability-metadata.md |
| `created_at`, `updated_at` | TIMESTAMP | |

**Indexes:**

```text
UNIQUE message_traces_correlation_id_unique (correlation_id)
INDEX message_traces_n8n_execution_id_idx (n8n_execution_id)
INDEX message_traces_conversation_id_idx (conversation_id)
INDEX message_traces_flow_id_created_at_idx (flow_id, created_at DESC)
```

**Retention:** 90 days hot in Postgres for dev/demo; archive/truncate policy ops-defined. **Redaction:** no `raw_payload`, no full prompts in `metadata`.

---

## 5. Correlation propagation map

| Layer | Field | Direction |
|-------|-------|-----------|
| Widget / Telegram | — | Provider → n8n |
| n8n normalize | `correlation_id` | generate UUID v4 |
| n8n POST | body `correlation_id`, headers `X-Correlation-Id`, `X-N8n-Execution-Id` | → backend |
| Backend ingress | `ObservabilityContext` | internal |
| `prompt_runs.metadata` | subset of envelope | DB audit |
| Langfuse trace | flat metadata keys | dev only |
| n8n delivery | pass `correlation_id` in logs only | ops |
| Webhook response | return `correlation_id` | → n8n / widget |

**Backend request id:** optional `X-Request-Id` generated at middleware — store on `message_traces` when E2 implemented.

---

## 6. Latency fields

| Metric | Definition |
|--------|------------|
| `backend_total_latency_ms` | `POST /webhook/message` wall clock including DB + AI |
| `ai_provider_latency_ms` | OpenAI round-trip from gateway |
| `channel_delivery_latency_ms` | n8n send node duration (post-backend) |
| End-to-end (ops) | n8n execution finished − trigger time (from n8n UI) |

---

## 7. Error model

| `error_code` | Typical stage | Consumer action |
|--------------|---------------|-----------------|
| `NORMALIZATION_FAILED` | normalized | Fix n8n Code node / payload |
| `WEBHOOK_AUTH_FAILED` | backend_posted | Token alignment |
| `BUSINESS_NOT_FOUND` | backend_posted | `business_id` / flow routing |
| `VALIDATION_ERROR` | backend_posted | Contract field missing |
| `AI_PROVIDER_ERROR` | ai_completed | Gateway / key / model |
| `AI_FALLBACK_USED` | ai_completed | Not failure — flag in metadata |
| `DELIVERY_FAILED` | reply_sent | Telegram/website adapter |
| `WEBSITE_CHAT_DISABLED` | normalized | Kill switch env |

`error_message` — human-readable, ≤500 chars, no stack traces in DB.

---

## 8. Current gaps (E2.0 baseline)

| Gap | Impact |
|-----|--------|
| No `message_traces` table | Ops must join n8n execution + `prompt_runs` + messages manually |
| `ConversationService` ignores `external_conversation_id` | Thread continuity weaker than spec |
| Delivery stage not persisted | Cannot query “reply_sent” from DB |
| `flow_id` absent | Cannot filter traces by bot behavior |
| Langfuse on compose backend | Partial — see E0 audit |
| D3 n8n headers | Implemented on unified workflow; not all archived paths |

---

## 9. Alignment with `prompt_runs`

| Concern | `prompt_runs` | `message_traces` |
|---------|---------------|------------------|
| AI audit | yes (final_prompt, result) | pointer via `prompt_run_id` |
| Full pipeline | partial | yes (stages) |
| n8n execution | metadata JSON only | first-class `n8n_execution_id` column |
| Retention | long (audit) | can be shorter |

Do **not** duplicate `final_prompt` on `message_traces`. Link by FK.

---

## 10. Langfuse mapping

Use same keys as [`observability-metadata.md`](../architecture/observability-metadata.md) §3 plus:

| Field | E2 add |
|-------|--------|
| `flow_id` | UUID string |
| `flow_key` | string |
| `message_trace_id` | UUID string |
| `trace_status` | lifecycle stage |

Trace name suggestion: `webhook_message:{channel}:{correlation_id}` (low cardinality on channel only).
