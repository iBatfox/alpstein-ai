# Channel Mapping — Telegram + Website Chat (E1.1)

## Purpose

Refine E1.0 normalized contracts with concrete field mapping for:

- Telegram inbound/outbound (reference channel)
- Website chat inbound/outbound (next planned channel)

This is **spec-only**. No runtime implementation in this document.

Canonical base contract: `docs/architecture/channel-ingress-contract.md`.

**E1.2 API alignment:** locked enums, MVP transport mapping (`POST /api/v1/webhook/message`), idempotency, timestamps, validation — [`specs/architecture/normalized-channel-contract.md`](../../specs/architecture/normalized-channel-contract.md). Tables below remain the channel-specific view; they must match §10 of that spec.

---

## 1) Telegram Mapping (reference)

### 1.1 Inbound payload → `NormalizedInboundMessage`

| Canonical field | Telegram source | Required | Fallback / notes |
|---|---|---:|---|
| `business_id` | Workflow config/static mapping per bot | yes | Must be provided by adapter config |
| `channel` | constant `"telegram"` | yes | Fixed |
| `channel_type` | constant `"messenger"` | yes | Fixed |
| `external_user_id` | `message.from.id` (string) | yes | Reject bot senders (`from.is_bot=true`) |
| `external_conversation_id` | `message.chat.id` (string) | yes | Private chat only in current scope |
| `external_message_id` | `message.message_id` namespaced (`tg:<chat_id>:<message_id>`) | yes | Deterministic telegram key |
| `text` | `message.text` | yes | Non-text updates unsupported now |
| `language` | `message.from.language_code` | no | Null if absent |
| `attachments` | derived from `photo/document/video/...` | no | Unsupported now → empty + metadata flag |
| `received_at` | `message.date` (unix) | yes | Convert to UTC ISO-8601 |
| `tenant_id` | not set by adapter | no | Backend resolves from `business_id` |
| `source_metadata` | safe subset from update/chat/from | no | No token/signature/raw headers |
| `idempotency_key` | `tg:<chat_id>:<message_id>` | yes | Same as normalized external message key |

### 1.2 Inbound payload → `NormalizedContact`

| Canonical field | Telegram source | Required | Notes |
|---|---|---:|---|
| `external_user_id` | `message.from.id` | yes | Channel-scoped user id |
| `display_name` | `first_name + last_name` | no | Build if available |
| `username` | `message.from.username` | no | Null if absent |
| `language` | `message.from.language_code` | no | Optional hint |
| `channel` | `"telegram"` | yes | Fixed |
| `phone` / `email` | n/a in Telegram update | no | Null by default |
| `metadata` | safe sender/chat hints | no | No secrets |

### 1.3 Outbound reply mapping → `NormalizedOutboundMessage`

| Canonical field | Telegram target | Required | Notes |
|---|---|---:|---|
| `channel` | `"telegram"` | yes | Fixed |
| `external_conversation_id` | `chat_id` | yes | Routes delivery |
| `reply_to_message_id` | source message id optional | no | Only when needed |
| `text` | `sendMessage.text` | yes | Adapter enforces Telegram limits |
| `attachments` | media methods | no | Deferred for current runtime |
| `metadata` | parse mode, disable flags | no | Adapter-owned |

### 1.4 Telegram fallback / duplicate / unsupported behavior

- Missing `message.text`: reject as unsupported for now (non-text update types).
- Missing `message.message_id`: treat as invalid payload.
- Duplicate assumptions: `idempotency_key = tg:<chat_id>:<message_id>` is stable for retries.
- Unsupported in E1.1 scope:
  - group/supergroup/channel chat updates
  - callback queries / edited messages / reactions
  - media-only messages

---

## 2) Website Chat Mapping (planned next channel)

Assumed adapter input shape (future widget/webhook):

- `visitor_id`, `session_id`, `message_id`, `text`, `timestamp`, `business_id`
- optional `name`, `email`, `phone`, `language`
- optional `page_url`, `referrer`, `utm_*`, `user_agent`

### 2.1 Website payload → `NormalizedInboundMessage`

| Canonical field | Website source | Required | Fallback / notes |
|---|---|---:|---|
| `business_id` | payload `business_id` | yes | Required |
| `channel` | constant `"website_chat"` | yes | Fixed |
| `channel_type` | constant `"website_chat"` | yes | Fixed |
| `external_user_id` | `visitor_id` | yes | Anonymous allowed with generated visitor id upstream |
| `external_conversation_id` | `session_id` | yes | Session thread key |
| `external_message_id` | namespaced `web:<session_id>:<message_id>` | yes | Required for idempotency |
| `text` | `text` | yes | Empty text rejected in E1.1 policy |
| `language` | payload `language` | no | Optional |
| `attachments` | future widget attachment list | no | Unsupported now |
| `received_at` | `timestamp` | yes | Normalize to UTC ISO-8601 |
| `tenant_id` | not set by adapter | no | Backend resolves by `business_id` |
| `source_metadata` | page/referrer/utm/user_agent safe subset | no | Cap and sanitize |
| `idempotency_key` | `web:<session_id>:<message_id>` | yes | Deterministic |

### 2.2 Website payload → `NormalizedContact`

| Canonical field | Website source | Required | Notes |
|---|---|---:|---|
| `external_user_id` | `visitor_id` | yes | May represent anonymous browser identity |
| `display_name` | `name` | no | Optional |
| `email` | `email` | no | Optional |
| `phone` | `phone` | no | Optional |
| `username` | n/a | no | Null |
| `language` | `language` | no | Optional |
| `channel` | `"website_chat"` | yes | Fixed |
| `metadata` | anon flags, source hints | no | PII-minimized |

### 2.3 Outbound reply mapping → `NormalizedOutboundMessage`

| Canonical field | Website target | Required | Notes |
|---|---|---:|---|
| `channel` | `"website_chat"` | yes | Fixed |
| `external_conversation_id` | `session_id` | yes | Widget session routing |
| `reply_to_message_id` | optional original `message_id` | no | Optional |
| `text` | chat response text | yes | Adapter/widget constraint |
| `attachments` | future | no | Deferred |
| `metadata` | frontend rendering hints | no | Adapter-owned |

### 2.4 Website chat handling notes

- Anonymous visitor support is first-class (`visitor_id` required, PII optional).
- Session lineage is session-centric (`external_conversation_id=session_id`).
- UTM/referrer/page metadata are optional and bounded; no secrets/tokens.
- Missing `message_id`: adapter must synthesize stable id before normalization.

---

## 3) Telegram vs Website Chat Comparison

| Dimension | Telegram | Website Chat |
|---|---|---|
| Identity strength | medium (`from.id`, often no phone/email) | variable (anonymous `visitor_id`, optional PII) |
| Conversation id quality | strong (`chat.id`) | medium (`session_id`, widget-defined) |
| Message id quality | strong (`message_id`) | variable (widget/system-generated) |
| Delivery guarantees | provider API semantics, usually strong | depends on widget/backend transport |
| Attachment support | broad in platform, currently deferred | widget-dependent, currently deferred |
| Reply routing | `chat_id` | `session_id` / widget socket/session mapping |
| Owner notify support | already established baseline | same backend flags, delivery path later |
| Observability support | mature baseline in E0 | needs metadata discipline from start |
| Main operational risks | non-text updates, bot/user confusion | anonymous identity churn, weak message IDs |

---

## 4) Adapter Responsibilities (channel-specific)

### Telegram Adapter

- parse Telegram update payload
- enforce private text-message scope
- compute canonical IDs + idempotency key
- map outbound target to `chat_id`
- preserve safe metadata only

### Website Chat Adapter

- parse widget payload
- support anonymous visitors
- map session/message IDs deterministically
- map outbound target to session channel
- preserve safe page/referrer/utm metadata

### Adapter prohibitions (both)

- no direct OpenAI calls
- no business prompt logic
- no sales-strategy decisions
- no direct CRM mutation (unless future explicit scope)

---

## 5) Validation Rules

**Authoritative (E1.2):** [`specs/architecture/normalized-channel-contract.md`](../../specs/architecture/normalized-channel-contract.md) §8–9.

Summary (unchanged intent from E1.1):

- Logical required: `business_id`, `channel`, `channel_type`, `external_user_id`, `external_conversation_id`, `text`, `received_at`, `idempotency_key`
- MVP POST: map to [`webhooks.md`](../../specs/api/webhooks.md) §7; `idempotency_key` **=** `message.external_message_id`
- `text`: non-empty, max **16384** UTF-8 code units
- `received_at` → `message.timestamp` (ISO-8601 UTC)
- Telegram: reject unsupported update types (non-text, bot sender, missing ids)
- Website chat: reject missing `visitor_id` / `session_id`; synthesize `message_id` if absent before `web:…` key
- Unsupported attachments: reject at adapter; no attachment-only MVP ingress

---

## 6) Out of Scope (E1.1)

- WhatsApp runtime implementation
- Instagram runtime implementation
- Website widget runtime implementation
- CRM automation redesign
- Cross-channel identity merge
- Billing/admin UI expansion
- Event-bus/queue architecture redesign
- Backend orchestration rewrites

---

## 7) Risks and Open Questions

Risks:

- website widgets emitting weak/unstable `message_id`
- anonymous visitor churn reducing contact continuity
- over-broad source metadata causing privacy drift

Open questions:

1. ~~exact max text length~~ — **resolved E1.2:** 16384 UTF-8 code units on `message.text`
2. minimal normalized attachment schema — deferred (E1.2 §9)
3. adapter-level error taxonomy in n8n — workflow convention, not backend API
4. website `visitor_id` fallback — strict upstream preferred; deployment-specific adapter fallback only if documented

## 8) Next recommended task

Website chat adapter/runtime implementation or backend `message.text` max-length enforcement — after human review of E1.2 (`tasks/done/T-e1.2-api-spec-alignment-channel-contract.md`).
