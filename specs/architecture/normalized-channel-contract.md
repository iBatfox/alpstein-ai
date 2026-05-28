# Normalized Channel Contract (E1.2 — canonical API alignment)

## 1. Purpose

Lock the **canonical normalized channel contracts** and their mapping to the MVP transport API `POST /api/v1/webhook/message`.

This document is the **spec source of truth** for:

- `NormalizedInboundMessage`
- `NormalizedContact`
- `NormalizedOutboundMessage`
- `channel` and `channel_type` enums
- idempotency, timestamps, validation, and unsupported-payload handling

**Status:** spec-only (E1.2). **Runtime unchanged** until a dedicated implementation task.

**Related (design lineage):**

- E1.0 overview: [`docs/architecture/channel-ingress-contract.md`](../../docs/architecture/channel-ingress-contract.md)
- E1.1 Telegram + Website Chat mappings: [`docs/architecture/channel-mapping-telegram-website.md`](../../docs/architecture/channel-mapping-telegram-website.md)
- MVP transport API: [`webhooks.md`](../api/webhooks.md) §7
- Source attribution extension: [`channel-source-attribution.md`](channel-source-attribution.md)
- Flow: [`incoming-message-flow.md`](../flows/incoming-message-flow.md)

---

## 2. Design brief

| Item | Decision |
|------|----------|
| **Consumers** | n8n channel adapters (normalize); backend `POST /api/v1/webhook/message` (validate + orchestrate); future dashboard read models |
| **Layers** | **Logical** normalized contracts (adapter output) → **Transport** MVP webhook JSON (this spec §6) |
| **Reference channel** | Telegram (E0 baseline) |
| **Next channel** | Website Chat (mapping in E1.1; runtime deferred) |
| **Auth** | API token n8n → backend (unchanged) |
| **Tenant isolation** | `business_id` → backend resolves `tenant_id`; adapters do not send `tenant_id` in MVP |
| **Risks** | Adapter/API drift if `idempotency_key` ≠ `message.external_message_id`; weak website `message_id`; accepting raw provider payloads at backend |

---

## 3. Contract layers

```text
Provider event
  → Channel adapter (n8n): builds NormalizedInboundMessage + NormalizedContact (logical)
  → Maps to POST /api/v1/webhook/message JSON (transport)
  → Backend: validates transport shape; idempotency via message.external_message_id
  → NormalizedOutboundMessage (logical) ← backend reply_to_customer + conversation ids
  → Adapter: provider send API
```

Adapters **must not** send raw Telegram/WhatsApp/Instagram/widget payloads as the primary contract. `message.raw_payload` is audit/debug only.

---

## 4. Enumerations

### 4.1 `channel` (Alpstein canonical routing key)

Used for conversation reuse, channel settings, lead `source_channel`, and Prompt Builder channel rules.

| Value | `channel_type` (§4.2) | MVP `POST /api/v1/webhook/message` | Notes |
|-------|----------------------|-----------------------------------|--------|
| `telegram` | `messenger` | **accepted** | Reference ingress (E0) |
| `website_chat` | `website_chat` | **accepted** | Next planned; mapping E1.1 |
| `whatsapp` | `messenger` | **accepted** | Deferred runtime; enum reserved |
| `instagram` | `messenger` | **accepted** | Deferred runtime; enum reserved |
| `test` | `other` | **accepted** | Synthetic / regression |
| `crm_webhook` | `crm_webhook` | **not accepted** | Register + implement in future task |
| `form` | `web_form` | **not accepted** | Register + implement in future task |

**MVP backend validation** accepts only: `whatsapp`, `telegram`, `instagram`, `website_chat`, `test` (see [`webhooks.md`](../api/webhooks.md) §7).

Adapters for deferred channels must not POST until enum is added to MVP validation in a separate implementation task.

### 4.2 `channel_type` (ingress family)

Describes **how** the message entered the platform. Set by the adapter when building the logical contract; **not** a separate top-level field on MVP webhook JSON.

| Value | Meaning | Typical `channel` values |
|-------|---------|--------------------------|
| `messenger` | Real-time chat on a messaging platform | `telegram`, `whatsapp`, `instagram` |
| `website_chat` | Web widget / on-site session chat | `website_chat` |
| `web_form` | Form submission (batch-style text) | `form` (future) |
| `crm_webhook` | CRM or partner HTTP webhook | `crm_webhook` (future) |
| `other` | Test harness or unspecified | `test` |

**Derivation (MVP):** backend may infer `channel_type` from `channel` using the table above; adapters must document the pair per channel in mapping docs.

---

## 5. Field matrices (logical / canonical)

### 5.1 `NormalizedInboundMessage`

| Field | Required | Type | Rules |
|-------|----------|------|-------|
| `business_id` | **yes** | string | Non-empty; external business key (backend resolves tenant) |
| `channel` | **yes** | enum §4.1 | Canonical routing key |
| `channel_type` | **yes** | enum §4.2 | Must be consistent with `channel` |
| `external_user_id` | **yes** | string | Channel-scoped sender id; maps to `customer.external_customer_id` |
| `external_conversation_id` | **yes** | string | Thread/session/chat id; prefixed per §7.2 |
| `external_message_id` | **yes** | string | Provider message id; **must equal** `idempotency_key` in MVP |
| `text` | **yes** | string | Non-empty for current scope; max **16384** UTF-8 code units (§8) |
| `received_at` | **yes** | datetime | ISO-8601 UTC (§8.2) |
| `idempotency_key` | **yes** | string | Deterministic; **must equal** `external_message_id` for MVP transport |
| `language` | no | string | BCP 47 hint; may map to `source.locale` or adapter metadata |
| `attachments` | no | array | **Unsupported in MVP** — reject or strip at adapter (§9) |
| `source_metadata` | no | object | Safe structured subset only; prefer `source` + `attribution` on transport (§6) |
| `tenant_id` | no | UUID | Backend resolves from `business_id` in MVP |

**Prohibited:** secrets, tokens, system prompts, or channel metadata inside `text`.

### 5.2 `NormalizedContact`

| Field | Required | Type | Rules |
|-------|----------|------|-------|
| `channel` | **yes** | enum §4.1 | Same as inbound message |
| `external_user_id` | **yes** | string | Same value as inbound `external_user_id` |
| `display_name` | no | string | Maps to `customer.name` |
| `phone` | no | string | E.164 preferred when present; maps to `customer.phone` |
| `email` | no | string | Maps to `customer.email` |
| `username` | no | string | Adapter metadata / future field; not top-level in MVP webhook |
| `language` | no | string | Optional hint |
| `consent_status` | no | string | Future-ready; not persisted in MVP |
| `metadata` | no | object | Bounded, non-secret; no CRM identity merge in MVP |

**MVP transport rule:** at least one of `customer.phone` or `customer.external_customer_id` must be present (backend validation). Telegram: `phone` null, `external_customer_id` required.

### 5.3 `NormalizedOutboundMessage`

| Field | Required | Type | Rules |
|-------|----------|------|-------|
| `channel` | **yes** | enum §4.1 | From backend response context |
| `external_conversation_id` | **yes** | string | Routes adapter delivery (Telegram `chat_id`, website `session_id`) |
| `text` | **yes** | string | From `data.reply_to_customer`; adapter enforces provider limits |
| `reply_to_message_id` | no | string | Provider-specific |
| `attachments` | no | array | Deferred |
| `metadata` | no | object | Adapter-owned (parse mode, etc.) |

Backend does not return a separate outbound object in MVP; n8n maps `data.reply_to_customer` + stored conversation/customer ids to `NormalizedOutboundMessage` before provider send.

---

## 6. MVP transport mapping (`POST /api/v1/webhook/message`)

Canonical logical fields map to the existing webhook body defined in [`webhooks.md`](../api/webhooks.md) §7.

| Logical (E1) | Transport (MVP) | Required on wire |
|--------------|-------------------|------------------|
| `business_id` | `business_id` | **yes** |
| `channel` | `channel` | **yes** |
| `channel_type` | *(implicit)* | no — document in adapter; infer server-side if needed |
| `external_user_id` | `customer.external_customer_id` | **yes** (or `customer.phone`) |
| `display_name` | `customer.name` | no |
| `phone` | `customer.phone` | conditional |
| `email` | `customer.email` | no |
| `external_conversation_id` | `message.external_conversation_id` | recommended; **required for website_chat** at adapter |
| `external_message_id` / `idempotency_key` | `message.external_message_id` | strongly recommended; **required at adapter** |
| `text` | `message.text` | **yes** |
| `received_at` | `message.timestamp` | recommended |
| `source_metadata` (safe subset) | `source`, `attribution`, `message.client` | no — see [`channel-source-attribution.md`](channel-source-attribution.md) |
| `language` | `source.locale` or omitted | no |
| `tenant_id` | — | not sent in MVP |
| `idempotency_key` (duplicate) | — | use `message.external_message_id` only on wire |
| — | `operator_business_context` | no |
| — | `correlation_id` | no — observability (D1/D2) |
| — | `message.raw_payload` | no — debug only |

**Adapter obligation:** before POST, set `message.external_message_id` to the canonical `idempotency_key` value (prefixed forms in §7).

---

## 7. Idempotency

### 7.1 Rules

1. Every adapter **must** compute a deterministic `idempotency_key` before calling the backend.
2. For MVP, **`idempotency_key` MUST equal `message.external_message_id`** on the webhook body.
3. Backend deduplication authority: `(business_id, message.external_message_id)` when `external_message_id` is present (see incoming-message flow).
4. Retries (n8n, provider, network) must reuse the **same** key.
5. If a channel cannot supply a stable provider message id, the adapter **must synthesize** one (website chat) and document the algorithm; never POST without a key.

### 7.2 Canonical key formats (locked)

| Channel | `external_message_id` / `idempotency_key` | `external_conversation_id` |
|---------|-------------------------------------------|----------------------------|
| Telegram | `tg:{chat_id}:{message_id}` | `tg:{chat_id}` |
| Website chat | `web:{session_id}:{message_id}` | `web:{session_id}` |
| WhatsApp (future) | `wa:{phone_number_id}:{wamid}` | per adapter spec |
| Instagram (future) | `ig:{thread_id}:{message_id}` | per adapter spec |
| Test | `test:{uuid}` or workflow-defined stable id | optional |

Prefixes must match [`channel-source-attribution.md`](channel-source-attribution.md) §3.4 and backend `EXTERNAL_CONVERSATION_ID_PREFIXES`.

---

## 8. Timestamps and text limits

### 8.1 `received_at` / `message.timestamp`

- **Logical:** `received_at` required on normalized record.
- **Transport:** `message.timestamp` optional but **recommended**; when present must be **ISO-8601 UTC** with `Z` suffix or explicit offset.
- Adapters convert provider epochs (e.g. Telegram `message.date` Unix seconds) to UTC ISO-8601.
- If omitted on wire, backend may use server receive time (implementation detail); adapters should always send provider time when known.

### 8.2 `message.text`

| Rule | Value |
|------|-------|
| Minimum length | **1** character (after trim) for MVP scope |
| Maximum length | **16384** UTF-8 code units |
| Empty / whitespace-only | `VALIDATION_ERROR` at backend |
| Exceeds max | `VALIDATION_ERROR`; adapter may reject earlier per provider cap |

Attachment-first messages (no text) are **unsupported** in MVP (§9).

---

## 9. Validation behavior

### 9.1 Backend (MVP transport)

On `POST /api/v1/webhook/message`:

| Check | Error code |
|-------|------------|
| Missing/invalid JSON envelope | `VALIDATION_ERROR` |
| Unknown `channel` enum | `VALIDATION_ERROR` |
| Missing `business_id` | `VALIDATION_ERROR` |
| `customer` missing both `phone` and `external_customer_id` | `VALIDATION_ERROR` |
| Missing/empty `message.text` | `VALIDATION_ERROR` |
| `message.text` length > 16384 | `VALIDATION_ERROR` |
| `operator_business_context` > 8192 chars | `VALIDATION_ERROR` |
| Secret-like strings in `source` / `attribution` | `VALIDATION_ERROR` |
| Unknown `business_id` | `BUSINESS_NOT_FOUND` |
| Invalid/missing API token | `UNAUTHORIZED` |

Optional fields (`source`, `attribution`, `message.external_conversation_id`, `correlation_id`) validate when present per attribution spec.

### 9.2 Adapter (pre-POST)

Adapters **reject** (do not call backend) when:

- Required logical fields (§5.1) cannot be populated.
- Unsupported update type (Telegram non-text, bot sender, group chat — see E1.1).
- Website chat missing `visitor_id` / `session_id`.
- Attachment-only payload without text (MVP).
- Raw provider payload would be mistaken for `message.text`.

Adapter-level errors are **n8n workflow errors** (log + stop branch). When an adapter chooses to forward a structured failure, use n8n error handling; do not invent new backend error codes for adapter-only failures in E1.2.

**Unsupported payload handling (locked):**

| Layer | Behavior |
|-------|----------|
| Adapter | Reject or route to dead-letter branch; no silent drop of customer text |
| Backend | `VALIDATION_ERROR` for schema violations; no partial AI processing on invalid ingress |
| `message.raw_payload` | Never required for business logic; backend ignores for AI |

---

## 10. Channel-specific alignment (Telegram + Website Chat)

Mappings are unchanged from E1.1; this section confirms API alignment only.

### 10.1 Telegram (reference)

| Logical | Transport example |
|---------|-------------------|
| `channel=telegram`, `channel_type=messenger` | `"channel": "telegram"` |
| `external_user_id` | `"customer": { "external_customer_id": "123456789", "phone": null }` |
| `external_conversation_id` | `"message": { "external_conversation_id": "tg:987654321", ... }` |
| `idempotency_key` | `"message": { "external_message_id": "tg:987654321:42", ... }` |
| `received_at` | `"message": { "timestamp": "2026-05-21T10:00:00Z" }` |

Ops detail: [`docs/ops/telegram-customer-ingress.md`](../../docs/ops/telegram-customer-ingress.md).

### 10.2 Website Chat (planned)

| Logical | Transport example |
|---------|-------------------|
| `channel=website_chat`, `channel_type=website_chat` | `"channel": "website_chat"` |
| `external_user_id` = `visitor_id` | `customer.external_customer_id` |
| PII optional | `customer.phone`, `name`, `email` optional |
| Session | `message.external_conversation_id`: `web:{session_id}` |
| Idempotency | `message.external_message_id`: `web:{session_id}:{message_id}` |

If widget omits `message_id`, adapter synthesizes stable `message_id` before forming `web:…` key (E1.1).

---

## 11. Resolved E1.0 open questions

| # | E1.0 question | E1.2 resolution |
|---|---------------|---------------|
| 1 | Enum values for `channel` / `channel_type` | §4.1–4.2 |
| 2 | Nullable `text` for attachment-first | **No** in MVP; §9 |
| 3 | Attachment schema | Deferred; reject attachment-only §9 |
| 4 | `source_metadata` vs first-class | Use `source` + `attribution` + `message.client` on transport; logical `source_metadata` maps there |
| 5 | CRM/form required fields | Deferred channels; minimum logical set in §5.1 when implemented |

Remaining (non-blocking):

- Exact adapter error taxonomy in n8n (workflow convention, not backend API).
- Website `visitor_id` fallback policy: **strict** — upstream/widget must provide; adapter-generated fallback only if documented per deployment (E1.1 question 4).

---

## 12. Out of scope (E1.2)

- Backend / Pydantic / route changes
- n8n workflow edits
- Database migrations
- Website widget implementation
- New channel runtime (WhatsApp, Instagram, CRM, form)
- Top-level `channel_type` or `idempotency_key` webhook fields (future optional extension)

---

## 13. Handoff

| Consumer | Action |
|----------|--------|
| **Backend engineer** | Optional: align `webhook.py` max length on `message.text` to 16384; document `channel_type` inference (no breaking change) |
| **n8n / adapters** | Ensure `external_message_id` matches §7.2; website chat prefix discipline before go-live |
| **Database** | No E1.2 schema change |

---

## 14. Document history

| Version | Task | Notes |
|---------|------|-------|
| E1.2 | T-e1.2 | Canonical API/spec alignment; supersedes informal enum/idempotency gaps in E1.0 § Open Questions |
