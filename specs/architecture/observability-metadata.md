# Alpstein AI — Observability Metadata Contract (CIP-C / Phase D)

## 1. Purpose

This document defines **deterministic observability metadata semantics** for Alpstein AI before Langfuse wiring (D2+) or additional telemetry volume.

**Status:** D1 **approved** — defaults locked in §16; no runtime wiring until D2  
**Date:** 2026-05-25 (defaults finalized 2026-05-27)  
**Branch context:** `stabilization/runtime-baseline` (operational baseline complete)

**Principle:** Prefer **stable, low-cardinality identifiers** and **explicit lineage fields** over duplicating large payloads in traces.

**Related:**

- Runtime tracing today: [`docs/architecture/langfuse-tracing.md`](../../docs/architecture/langfuse-tracing.md)
- Channel/source ingress: [`channel-source-attribution.md`](channel-source-attribution.md)
- Prompt assembly: [`prompt-builder-rules.md`](prompt-builder-rules.md)
- Intent policy (CIP-B): [`docs/architecture/conversation-intent-policy-mvp.md`](../../docs/architecture/conversation-intent-policy-mvp.md)
- DB audit: `prompt_runs`, `messages.metadata`, `messages.ai_metadata`

**Out of scope (D1):** Kubernetes, metrics agents, log aggregation redesign, n8n workflow changes, frontend, CRM, new product features, Langfuse SDK wiring.

---

## 2. Design brief

| Item | Decision |
|------|----------|
| **Consumers** | Backend engineers (context propagation), Langfuse (dev traces), ops replay, future analytics |
| **Primary correlation** | `correlation_id` per inbound webhook HTTP request |
| **Session lineage** | `conversation_id` (+ `message_id` per turn) |
| **Workflow attribution** | Optional n8n execution metadata at ingress — not business logic |
| **Channel attribution** | Canonical `channel` + safe `source` / `attribution` subset |
| **Prompt lineage** | `prompt_run_id` + template/version + section ids |
| **Risks** | Secret leakage in metadata; tag cardinality explosion; duplicate/conflicting IDs |

---

## 3. Metadata contract envelope

All backend layers SHOULD use one logical envelope per inbound turn, propagated from webhook ingress through AI orchestration.

### 3.1 Schema version

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `obs_schema_version` | yes | string | Contract version; **D1 value:** `"1.0"` |

### 3.2 Required fields (runtime context)

| Field | Type | When set | Description |
|-------|------|----------|-------------|
| `correlation_id` | UUID string | Request ingress | End-to-end id for one `POST /api/v1/webhook/message` handling |
| `tenant_id` | UUID string | After business resolve | Tenant scope |
| `business_id` | UUID string | After business resolve | Internal business PK |
| `business_external_id` | string | After business resolve | n8n `business_id` / `external_id` |
| `channel` | enum string | Ingress | Alpstein canonical channel |
| `conversation_id` | UUID string | After conversation resolve | Session lineage anchor |
| `inbound_message_id` | UUID string | After message save | DB `messages.id` for customer turn |
| `is_duplicate` | boolean | After message save | Idempotency outcome |

### 3.3 Optional fields (high value, bounded)

| Field | Type | Layer | Description |
|-------|------|-------|-------------|
| `external_message_id` | string | Ingress | Provider idempotency key |
| `external_conversation_id` | string | Ingress | Provider thread/session id |
| `prompt_run_id` | UUID string | After AI | `prompt_runs.id` for this turn |
| `outbound_message_id` | UUID string | After AI save | Outgoing AI `messages.id` if persisted |
| `template_key` | string | AI config | e.g. `customer_reply_v1` |
| `prompt_template_id` | UUID string | AI config | Platform template row |
| `prompt_version` | string | AI config | Template version label |
| `assembled_section_ids` | string[] | Prompt build | Ordered section ids only (not content) |
| `prompt_task` | string | Prompt build | e.g. `reply_to_customer` |
| `gateway_model` | string | LLM call | Resolved model id |
| `gateway_provider` | string | LLM call | e.g. `openai` |
| `ai_success` | boolean | LLM call | Gateway succeeded with text |
| `used_fallback` | boolean | Response | Fallback path taken |
| `greeting_mode` | string | Policy | Greeting policy mode enum value |
| `conversation_intent` | string | Policy (CIP) | Resolved intent label |
| `intent_matched_rule` | string | Policy (CIP) | Rule id / name |
| `intent_used_previous_message` | boolean | Policy (CIP) | History used for intent |
| `operator_business_context_present` | boolean | Ingress | True if non-empty operator context (not full text in traces) |
| `n8n_workflow_id` | string | Ingress | n8n workflow identifier |
| `n8n_execution_id` | string | Ingress | n8n execution id for workflow attribution |
| `source_platform` | string | Ingress | From `source.platform` when present |
| `source_account_id` | string | Ingress | Non-secret account ref |
| `attribution_summary` | string | Ingress | Single-line UTM/marketing summary (max 500 chars) |
| `error_code` | string | Error path | Stable internal code (not stack trace) |

### 3.4 Explicitly excluded from observability envelope

Never attach to Langfuse metadata, `prompt_runs.metadata`, or structured logs at INFO:

- OpenAI / Langfuse / webhook **secrets**
- Full `assembled_prompt` body in production logs (dev Langfuse may retain truncated copy per policy below)
- `message.raw_payload` (audit DB column only)
- Raw IP, full `user_agent` (see channel-source-attribution)
- Customer `message.text` beyond short preview (≤500 chars, existing pattern)
- `final_prompt` in webhook API responses

---

## 4. Field naming convention

| Rule | Example |
|------|---------|
| **snake_case** ASCII keys | `correlation_id`, `prompt_run_id` |
| **Stable semantic names** — no abbreviations except established ids | `conversation_id` not `conv` |
| **Boolean** prefix with `is_` / `used_` / `has_` | `is_duplicate`, `used_fallback` |
| **External** prefix `external_` | `external_message_id` |
| **n8n** prefix `n8n_` | `n8n_execution_id` |
| **Policy** intent fields match [`langfuse_intent_trace.py`](../../backend/app/schemas/langfuse_intent_trace.py) constants | `conversation_intent` |
| **No** nested provider blobs in trace metadata | Use scalar fields or `attribution_summary` |
| **Version** field `obs_schema_version` on envelope only | |

Langfuse: use **same key names** as backend envelope where possible (flat string metadata for Langfuse SDK constraints).

---

## 5. Metadata lifecycle

```text
┌─────────────────────────────────────────────────────────────────┐
│ 1. Request ingress (webhook route)                               │
│    Generate/propagate correlation_id                             │
│    Parse optional n8n_* + source/attribution summary             │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Session handling (customer, conversation, message save)     │
│    Attach conversation_id, inbound_message_id, is_duplicate    │
│    Persist channel + safe attribution → messages.metadata (ATTR) │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Workflow execution (lead, notify, duplicate short-circuit)  │
│    Same correlation_id; branch flags only in metadata              │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Prompt build (PromptBuilderService)                         │
│    Record prompt_task, assembled_section_ids (ids only)          │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. LLM call (AiGatewayService) + Langfuse generation child     │
│    gateway_model, tokens, latency, ai_success                    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Response (PromptRun insert, outbound message, webhook JSON)   │
│    prompt_run_id; ai_metadata on message; NO envelope in response│
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. Error path (validation, AI failure, tracing swallow)          │
│    error_code; correlation_id preserved; used_fallback if applicable│
└─────────────────────────────────────────────────────────────────┘
```

### 5.1 Ingress

- **Create** `correlation_id` if absent: UUID v4 at start of `post_webhook_message`.
- **Accept** optional incoming ids (D2) — see §16.1:
  - HTTP header `X-Correlation-Id` (preferred when both present)
  - JSON body field `correlation_id` (optional)
  - Invalid or missing values → server-generated UUID v4; invalid values → `VALIDATION_ERROR`.
- **Workflow attribution (D2):** HTTP header `X-N8n-Execution-Id` only — see §16.5. Optional normalized webhook field deferred to D3.

### 5.2 Session handling

- After persistence: `conversation_id`, `inbound_message_id`, `is_duplicate` are authoritative for lineage.
- **Langfuse `session_id`** remains `conversation_id` (existing behavior — do not change to correlation_id).

### 5.3 Workflow execution

- Lead/notify branches add boolean flags to internal context only (`lead_created`, `lead_updated`, `notify_owner`) — already in webhook response; mirror scalars in trace metadata if needed.

### 5.4 Prompt build

- Store **section id list** and `template_key` / `prompt_version` — not full section bodies in `prompt_runs.metadata` (full text remains in redacted `final_prompt` column per T11.10).

### 5.5 LLM call

- Child observation `openai_chat_completion` under parent span `ai_reply_orchestration` (existing shape).

### 5.6 Response

- Webhook JSON unchanged — no observability envelope exposed to n8n.
- `messages.ai_metadata`: `prompt_run_id`, `model`, `provider`, `used_fallback` (existing).

### 5.7 Error path

- Validation errors: log `correlation_id` + `error_code`; no AI span.
- Langfuse failures: swallow, log exception with `correlation_id` (existing).

---

## 6. Correlation ID rules

| Rule | Detail |
|------|--------|
| **Cardinality** | One `correlation_id` per webhook HTTP request |
| **Format** | UUID v4 string (lowercase hex with hyphens) |
| **Propagation** | Same value in structured logs, Langfuse trace metadata, `prompt_runs.metadata` |
| **Source priority** | (1) Valid incoming header/body id (2) server-generated at ingress |
| **Not** equal to `conversation_id` | Conversation spans many requests |
| **Not** equal to `external_message_id` | Provider-scoped, may repeat across businesses |
| **Duplicate webhooks** | Same `external_message_id` may produce **new** `correlation_id` per HTTP retry; `is_duplicate=true` links behavior |

---

## 7. Session lineage rules

| Concept | Canonical id | Langfuse mapping |
|---------|--------------|------------------|
| **Conversation thread** | `conversation_id` | `session_id` |
| **Customer turn** | `inbound_message_id` | metadata + PromptRun `message_id` FK |
| **AI execution** | `prompt_run_id` | metadata; DB join key |
| **Outbound AI text** | `outbound_message_id` | metadata when saved |
| **Provider thread** | `external_conversation_id` | metadata; conversation row when ATTR lands |

**Ordering:** Use `messages.created_at` for history; metadata must not reorder turns.

**Cross-channel:** Same human on two channels ⇒ two `conversation_id` values in MVP (no identity merge).

---

## 8. Workflow attribution rules

| Field | Source | Use |
|-------|--------|-----|
| `n8n_workflow_id` | Optional future header/field | Filter traces by workflow (not required D2) |
| `n8n_execution_id` | **`X-N8n-Execution-Id` header (D2)**; optional webhook field (D3) | Join to n8n UI execution log |

**Rules:**

- Optional; absence must not break processing.
- Backend does **not** interpret workflow ids for business decisions.
- Never store n8n credentials or full workflow JSON in metadata.
- **D2:** `X-N8n-Execution-Id` only — see §16.5.

---

## 9. Channel attribution rules

Align with [`channel-source-attribution.md`](channel-source-attribution.md).

| Field | Observability use |
|-------|-------------------|
| `channel` | Required dimension on every trace |
| `source_platform` | Optional low-cardinality adapter label |
| `source_account_id` | Optional; must be non-secret |
| `attribution_summary` | Optional single line derived from `attribution.*` (UTM keys concatenated) |

**Rules:**

- Do **not** copy full `message.text` into attribution fields.
- Do **not** use `raw_payload` as trace input.
- Website chat may populate `attribution_summary`; messengers usually omit.

---

## 10. Prompt lineage rules

| Artifact | Lineage recorded | Where |
|----------|------------------|-------|
| Platform template | `prompt_template_id`, `prompt_version`, `template_key` | `prompt_runs` columns + metadata |
| Assembly | `assembled_section_ids`, `prompt_task` | metadata + Langfuse |
| Execution | `prompt_run_id`, tokens, `latency_ms`, `gateway_model` | `prompt_runs` + Langfuse generation |
| Full prompt text | Redacted `final_prompt` in DB; truncated dump in dev Langfuse only | Existing caps: 16k DB, 24k Langfuse |

**Section ids** must match [`assembled_prompt.py`](../../backend/app/schemas/assembled_prompt.py) `CANONICAL_SECTION_ORDER` vocabulary.

**Intent / greeting overlays** (CIP, HF-1): record policy outputs as scalars, not full prompt slices.

---

## 11. Replay and debug requirements

### 11.1 Minimum replay chain (ops)

Given any of:

- `correlation_id`
- `inbound_message_id` / `external_message_id` + `business_id`
- `prompt_run_id`
- `conversation_id` + timestamp window

Ops MUST be able to locate:

1. Inbound `messages` row (and `is_duplicate`)
2. Related `prompt_runs` row(s)
3. Outbound AI `messages` row (via `ai_metadata.prompt_run_id`)
4. Langfuse trace (dev) via `session_id=conversation_id` + metadata filter on `correlation_id` (D2)

### 11.2 Debug modes

| Mode | Behavior |
|------|----------|
| **Production default** | Scalar metadata only; no full prompt in logs |
| **Dev Langfuse** | Truncated `assembled_prompt` in metadata (existing); add CIP intent fields |
| **DB audit** | `prompt_runs.final_prompt` redacted; `messages.raw_payload` for provider forensics only |

### 11.3 Not required in D1/D2

- Full request/response replay UI
- Automatic n8n ↔ backend bidirectional link (manual `n8n_execution_id` sufficient for MVP)

---

## 12. Langfuse metadata mapping proposal

**Do not wire until D2** — mapping targets current [`LangfuseTracingService`](../../backend/app/services/langfuse_tracing_service.py) shape.

### 12.1 Trace / span level (`ai_reply_orchestration`)

| Envelope field | Langfuse target | Notes |
|----------------|-----------------|-------|
| `correlation_id` | `metadata.correlation_id` | **New (D2)** |
| `conversation_id` | `session_id` + `metadata.conversation_id` | session_id unchanged |
| `business_external_id` | `metadata.business_id` | Keep existing key name for compat |
| `business_id` | `metadata.business_uuid` | Existing |
| `channel` | `metadata.channel` + tag `channel:{channel}` optional | Limit tag cardinality |
| `inbound_message_id` | `metadata.inbound_message_id` | **New** |
| `is_duplicate` | `metadata.is_duplicate` | **New** |
| `greeting_mode` | `metadata.greeting_mode` | Existing |
| `customer_language` | `metadata.customer_language` | Existing (from greeting policy) |
| `operator_business_context_present` | `metadata.operator_business_context_present` | **Always** when tracing (§16.2) |
| `operator_business_context` | `metadata.operator_business_context` | Truncated preview **non-production only** (§16.2) |
| `conversation_intent` | `metadata.conversation_intent` | CIP-C — use constant key |
| `intent_matched_rule` | `metadata.intent_matched_rule` | CIP-C |
| `intent_used_previous_message` | `metadata.intent_used_previous_message` | CIP-C stringified bool |
| `n8n_execution_id` | `metadata.n8n_execution_id` | **New** |
| `source_platform` | `metadata.source_platform` | When ATTR ingress present |
| `attribution_summary` | `metadata.attribution_summary` | Optional |
| `assembled_section_ids` | `metadata.assembled_section_ids` | Comma-separated or JSON string |
| `assembled_prompt` | `metadata.assembled_prompt` | Dev only; keep truncation |

### 12.2 Generation level (`openai_chat_completion`)

| Field | Langfuse target |
|-------|-----------------|
| `prompt_run_id` | `metadata.prompt_run_id` (post-create update if needed) |
| `gateway_model` | `model` |
| `input_tokens` / `output_tokens` | `usage_details` |
| `latency_ms` | `metadata.latency_ms` |
| `ai_success` | `level` DEFAULT vs ERROR |

### 12.3 Tags (low cardinality)

Keep existing: `greeting_orchestration`, `telegram`.

**Demo business tag (§16.4):** apply `alpstein_ai_demo_001` **only** when `business_external_id == alpstein_ai_demo_001`. Do not tag `demo_barbershop_001` with the Alpstein demo tag (D2 corrects current drift).

**Avoid:** per-customer tags, full UTM values as tags.

---

## 13. Persistence mapping (DB)

| Envelope subset | Table.column | Notes |
|-----------------|--------------|-------|
| Scalar envelope subset (§16.3) | `prompt_runs.metadata` JSONB | Primary audit extension (D2); max 4096 bytes |
| `prompt_run_id` + model | `messages.ai_metadata` | Existing |
| Channel + attribution | `messages.metadata` | Per ATTR-3 |
| Provider blob | `messages.raw_payload` | Not observability primary |
| — | `conversations.metadata` | Session snapshot when ATTR lands |

---

## 14. Files likely changed in D2 (implementation)

| File | Change |
|------|--------|
| `backend/app/schemas/observability.py` | **New** — `ObservabilityContext` dataclass / typed dict |
| `backend/app/middleware/` or `api/routes/webhook.py` | Generate/propagate `correlation_id` |
| `backend/app/core/observability_context.py` | ContextVar holder (optional) |
| `backend/app/services/webhook_message_service.py` | Build context at ingress; pass to coordinator |
| `backend/app/services/ai_reply_orchestration_service.py` | Pass context to PromptRun + tracing |
| `backend/app/services/langfuse_tracing_service.py` | `_build_metadata` uses envelope; CIP-C intent fields |
| `backend/app/services/prompt_run_service.py` | Accept observability metadata dict |
| `backend/app/schemas/langfuse_intent_trace.py` | Wire constants (CIP-C) |
| `docs/architecture/langfuse-tracing.md` | Sync with contract |
| `specs/architecture/observability-metadata.md` | Mark sections implemented |

**Not D2 unless approved:** n8n workflow export changes (D3 ops), ATTR DB writes (ATTR-3 parallel).

---

## 15. Implementation slices (after D1)

| Step | Task | Owner |
|------|------|-------|
| **D1** | This contract | api-designer ✓ |
| **D2** | `ObservabilityContext` + webhook propagation + Langfuse + `prompt_runs.metadata` | backend-engineer |
| **D2b** | Structured logging filter (`correlation_id` on all webhook logs) | backend-engineer |
| **D3** | n8n pass `X-Correlation-Id` / `n8n_execution_id` | n8n-integration-engineer |
| **D4** | ATTR-3 persistence alignment for `messages.metadata` | backend-engineer |
| **D5** | Ops runbook: replay queries | project-archivist |

---

## 16. Risks and approved defaults (D1)

| Risk | Mitigation |
|------|------------|
| Metadata volume / cost | Scalar-first; cap previews; section ids not bodies |
| Langfuse import failure | Keep swallow; optional lazy import (separate hardening) |
| Key drift Langfuse vs DB | Single builder from `ObservabilityContext` |
| Secret leakage | Reuse `prompt_run_service` redaction patterns |
| Tag cardinality | Channel tags only; no UTM as tags |

### 16.1 Correlation ID ingress (approved)

| Source | Rule |
|--------|------|
| `X-Correlation-Id` header | Optional; **wins** over body when both are valid UUIDs |
| JSON `correlation_id` | Optional body field on webhook request (D2 schema) |
| Server | Generate UUID v4 when both absent |
| Validation | Malformed UUID → `VALIDATION_ERROR`; do not process message |

Body field is for n8n Set-node convenience; header is preferred for cross-service propagation.

### 16.2 Operator context in Langfuse traces (approved)

| Field | When emitted |
|-------|----------------|
| `operator_business_context_present` | **Always** in Langfuse metadata when tracing is active |
| `operator_business_context` (truncated text) | **Only** when tracing active **and** `ALPSTEIN_AI_ENVIRONMENT` is `development`, `dev`, `local`, or `test` |
| Production | Boolean only — **no** operator text in Langfuse metadata |

Existing truncation cap (4000 chars) remains for dev preview.

### 16.3 `prompt_runs.metadata` payload (approved)

Persist **scalar envelope subset** only:

- All §3.2 required fields and §3.3 optional fields that are set for the turn
- **Exclude** §3.4 forbidden content and **exclude** full prompt bodies / `assembled_prompt` text

**Max size:** 4096 bytes after JSON serialization. If over limit, drop optional keys in order: `attribution_summary` → `assembled_section_ids` → `n8n_execution_id` → remaining §3.3 optionals until within cap. Required §3.2 fields must remain.

### 16.4 Demo Langfuse tag (approved)

| Condition | Tag |
|-----------|-----|
| `business_external_id == alpstein_ai_demo_001` | `alpstein_ai_demo_001` |
| Any other business (including `demo_barbershop_001`) | **No** Alpstein demo tag |

D2 implementation replaces current drift (`demo_barbershop_001` incorrectly receiving Alpstein demo tag).

### 16.5 n8n workflow execution attribution (approved)

| Phase | Mechanism |
|-------|-----------|
| **D2** | HTTP header **`X-N8n-Execution-Id`** → `n8n_execution_id` in observability envelope / Langfuse metadata |
| **D3 (optional)** | Normalized webhook field `n8n_execution_id` for Set-node ergonomics — **header remains canonical** if both sent |

Backend does not branch on workflow id for business logic.

### 16.6 Production Langfuse policy (approved — no change)

| Environment | Tracing |
|-------------|---------|
| `development` / `dev` / `local` / `test` | Auto-enable when Langfuse public + secret keys are set (current) |
| Production / staging (other) | **Off** unless `LANGFUSE_TRACING_ENABLED=true` **and** keys set (current) |

No change to existing [`langfuse_tracing_active`](../../backend/app/core/config.py) behavior in D2 unless explicitly required for bugfix.

---

## 17. D1 review checklist

- [ ] `correlation_id` rules distinct from `conversation_id` and `external_message_id`
- [ ] Session lineage uses existing DB FKs (`conversation_id`, `message_id`, `prompt_run_id`)
- [ ] Channel attribution aligned with `channel-source-attribution.md` without `raw_payload` in AI/trace primary path
- [ ] CIP intent fields mapped to Langfuse keys in §12.1
- [ ] Webhook response remains free of observability envelope
- [ ] No secrets / raw IP / full prompts in production metadata policy
- [ ] Prompt lineage uses section ids + template ids, not duplicate unbounded text
- [ ] D2 file list agreed; no architecture redesign, K8s, or n8n workflow scope in D2 backend slice
- [x] Approved defaults in §16 locked (D1 finalize)

---

## 18. Suggested commit message

```text
docs(spec): finalize CIP-C D1 observability defaults

Lock §16 approved defaults for correlation, Langfuse operator context,
prompt_runs.metadata cap, demo tag, n8n execution header, and production policy.
```
