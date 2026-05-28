# Alpstein AI — Webhooks Architecture

## 1. Purpose

This document describes webhook architecture and webhook payload contracts for Alpstein AI MVP.

Webhooks are the entry point of external communication into the system.

The webhook layer is responsible for:

- receiving messages from external providers;
- normalizing external payloads;
- triggering backend processing;
- delivering responses back to customers.

The webhook system must remain provider-independent and scalable.

---

# 2. Webhook Architecture Overview

Main webhook flow:

```text
Customer Message
      ↓
External Provider
(WhatsApp / Website Chat / Telegram / Instagram)
      ↓
n8n Webhook
      ↓
Payload Normalization
      ↓
Backend API
      ↓
AI Processing
      ↓
Backend Response
      ↓
n8n Delivery Workflow
      ↓
Customer Reply
```

---

# 3. Responsibilities

## 3.1 External Providers

External providers are responsible for:

- delivering customer messages;
- sending provider-specific webhook payloads;
- sending delivery events.

Examples:

- WhatsApp Cloud API;
- Telegram Bot API;
- Website Chat Widget;
- Instagram API.

---

## 3.2 n8n Responsibilities

n8n is responsible for:

- receiving provider webhooks;
- validating provider requests;
- normalizing payloads;
- calling backend API;
- sending replies back to providers;
- notifying business owners.

n8n should not contain business logic.

---

## 3.3 Backend Responsibilities

The backend is responsible for:

- validating normalized payload;
- identifying business;
- processing conversation;
- AI processing;
- lead creation;
- structured response generation.

The backend must not depend on raw provider payloads.

---

# 4. Webhook Design Principles

## 4.1 Provider Independence

Backend must never receive raw provider payloads.

n8n converts provider payloads into normalized structures.

This prevents backend dependency on:

- WhatsApp-specific payloads;
- Telegram-specific payloads;
- Instagram-specific payloads.

---

## 4.2 Normalized Contract

All providers must be converted into one common message contract.

This allows:

- reusable backend logic;
- reusable AI processing;
- easier testing;
- future channel expansion.

Optional operator-editable business notes may be sent as top-level `operator_business_context` (see §7). This is **not** a provider field and **does not** replace `tenant_business_profiles` in PostgreSQL.

---

## 4.3 Stateless Processing

Webhook processing should remain stateless where possible.

Conversation state must be stored in PostgreSQL.

n8n workflows should not permanently store conversation state.

---

## 4.4 Security

Webhook endpoints must be protected.

Requirements:

- HTTPS only;
- provider verification where possible;
- API token between n8n and backend;
- request validation;
- rate limiting in future versions.

---

# 5. Incoming Webhook Flow

## Step 1 — Customer Sends Message

Example:

```text
Customer sends WhatsApp message
```

---

## Step 2 — Provider Sends Webhook

Example:

```text
WhatsApp Cloud API → n8n webhook
```

The payload is provider-specific.

---

## Step 3 — n8n Receives Webhook

n8n receives the raw provider payload.

Responsibilities:

- validate provider request;
- extract relevant fields;
- normalize structure.

---

## Step 4 — Payload Normalization

n8n converts the provider payload into normalized structure.

Example:

```json
{
  "business_id": "demo_barbershop_001",
  "channel": "whatsapp",
  "customer": {
    "phone": "+41790000000",
    "name": "John",
    "email": null,
    "external_customer_id": "wa_001"
  },
  "message": {
    "text": "Hello, can I book an appointment tomorrow?",
    "external_message_id": "wamid.example",
    "timestamp": "2026-05-21T10:00:00Z",
    "raw_payload": {}
  }
}
```

Optional `operator_business_context` may be added at the top level before POST (see §7). Backend **T14-OC-2** reads the field and passes it to Prompt Builder (not persisted in MVP).

This normalized payload is sent to backend.

---

## Step 5 — Backend Processing

Backend processes the message.

Responsibilities:

- validate request;
- identify business;
- create/update customer;
- create/update conversation;
- save messages;
- generate AI response;
- create lead if needed.

---

## Step 6 — Backend Response

Backend returns structured response.

Example:

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "Hello! Sure. What service would you like to book and what time works best for you?",
    "lead_created": true,
    "lead_updated": false,
    "notify_owner": true,
    "lead": {
      "id": "8a6a3a5e-6c02-4b87-b8d4-12d10c86c111",
      "status": "new",
      "priority": "normal"
    },
    "notification": {
      "should_notify_owner": true,
      "notification_type": "new_lead",
      "reason": "lead_created",
      "priority": "normal"
    },
    "conversation": { "id": "...", "status": "open" },
    "message": { "id": "...", "is_duplicate": false }
  }
}
```

When no lead was touched, omit `lead`. When `notify_owner` is false, omit `notification`. `lead_updated` is always present (boolean).

---

## Step 7 — n8n Sends Customer Reply

n8n sends the AI-generated response back through the correct provider API.

Example:

```text
n8n → WhatsApp Cloud API
```

---

## Step 8 — Owner Notification

If required:

```json
{
  "notify_owner": true
}
```

n8n triggers notification workflow.

Possible channels:

- Telegram;
- email;
- WhatsApp;
- internal workflow.

---

# 6. Supported Channels

## MVP Channels

```text
WhatsApp Cloud API
Test Webhook
```

---

## Future Channels

```text
Telegram
Instagram Direct
Website Chat Widget
Facebook Messenger
```

---

# 7. Incoming Normalized Payload Contract

## Purpose

This is the main backend contract.

All providers must normalize into this format.

**Canonical channel contract (E1.2):** logical field matrices, `channel` / `channel_type` enums, idempotency rules, timestamps, validation, and unsupported-payload handling — [normalized-channel-contract.md](../architecture/normalized-channel-contract.md). This section documents the **MVP transport JSON** for `POST /api/v1/webhook/message`; adapters build the logical contract first, then map per §6 of that spec.

**Multi-channel source attribution:** optional structured `source`, `attribution`, `message.client`, and `message.external_conversation_id` — see [channel-source-attribution.md](../architecture/channel-source-attribution.md). **ATTR-2:** Pydantic validation active (optional fields; Telegram payloads without attribution remain valid). Persistence and Prompt Builder: ATTR-3+.

---

## E1.2 summary (transport vs logical)

| Topic | Rule |
|-------|------|
| **MVP `channel` values** | `whatsapp`, `telegram`, `instagram`, `website_chat`, `test` |
| **`channel_type`** | Not a top-level webhook field in MVP; adapter sets `messenger` / `website_chat` / `other` on logical record — see canonical spec §4.2 |
| **Idempotency** | Adapter `idempotency_key` **must equal** `message.external_message_id` on POST; formats `tg:…`, `web:…` — canonical spec §7 |
| **`received_at`** | Maps to `message.timestamp` (ISO-8601 UTC, recommended) |
| **Customer id** | `customer.external_customer_id` and/or `customer.phone` (Telegram: phone may be null) |
| **`message.text`** | Required, non-empty, max **16384** UTF-8 code units (canonical spec §8.2) |
| **Deferred channels** | `crm_webhook`, `form` documented in canonical spec; **not** accepted by MVP backend validation |

Channel-specific tables: [channel-mapping-telegram-website.md](../../docs/architecture/channel-mapping-telegram-website.md).

---

## Payload Structure

```json
{
  "business_id": "demo_barbershop_001",
  "channel": "whatsapp",
  "operator_business_context": "Pop-up hours this week: Sat 10:00–14:00 only. Mention 10% student discount.",
  "customer": {
    "phone": "+41790000000",
    "name": "John",
    "email": null,
    "external_customer_id": "wa_001"
  },
  "message": {
    "text": "Hello, can I book an appointment tomorrow?",
    "external_message_id": "wamid.example",
    "timestamp": "2026-05-21T10:00:00Z",
    "raw_payload": {}
  }
}
```

Omit `operator_business_context` or set it to `null` when no operator notes apply.

---

## Field Definitions

### business_id

External business identifier.

Used to identify which business should process the message.

Example:

```text
demo_barbershop_001
```

---

### channel

Message source channel (canonical routing key).

**MVP allowed values** (backend validation):

```text
whatsapp
telegram
instagram
website_chat
test
```

**Catalog (future — not accepted on wire until implementation task):** `crm_webhook`, `form` — see [normalized-channel-contract.md](../architecture/normalized-channel-contract.md) §4.1.

Each value pairs with a logical `channel_type` (`messenger`, `website_chat`, `web_form`, `crm_webhook`, `other`) at the adapter; not sent as a separate top-level field in MVP.

---

### customer.phone

Customer phone when known (E.164 preferred).

**MVP validation:** at least one of `customer.phone` or `customer.external_customer_id` must be present. Telegram ingress may send `phone: null` with `external_customer_id` set.

---

### customer.external_customer_id

Channel-scoped sender identifier (logical `external_user_id`).

Examples:

```text
Telegram user id (from.id)
Website visitor_id
WhatsApp ID (future)
```

---

### message.text

Customer message text.

| Rule | Value |
|------|-------|
| Required | **yes** |
| Min length | 1 (non-empty after trim) |
| Max length | **16384** UTF-8 code units |

Must not contain operator business notes, system prompts, or channel metadata (those belong in `operator_business_context` or `source` / `attribution`).

Attachment-only ingress without text is **unsupported** in MVP.

---

### message.external_message_id

Provider-scoped message id and **MVP idempotency key**.

| Rule | Value |
|------|-------|
| Adapter | **Required** — adapter must not POST without a stable key |
| Backend | Used for deduplication when present |
| Canonical | Must equal logical `idempotency_key` |

**Locked formats:**

```text
tg:{chat_id}:{message_id}      # Telegram
web:{session_id}:{message_id}  # Website chat
```

Full rules: [normalized-channel-contract.md](../architecture/normalized-channel-contract.md) §7.

---

### message.external_conversation_id

Optional on wire; **required at adapter** for website chat and recommended for Telegram.

Thread/session/chat id with channel prefix, e.g. `tg:{chat_id}`, `web:{session_id}`. See [channel-source-attribution.md](../architecture/channel-source-attribution.md).

---

### message.timestamp

Provider event time (`received_at` in logical contract).

**Format:** ISO-8601 UTC (`…Z` or explicit offset). Adapters convert Unix epochs to UTC. Recommended on every POST; backend may fall back to server time if omitted (implementation detail).

---

### message.raw_payload

Optional original provider payload.

Useful for:

- debugging;
- provider troubleshooting;
- future provider-specific features.

Backend should not depend on this field.

Backend must **not** use `raw_payload` as the primary path for operator business notes or Prompt Builder business context. Use `operator_business_context` instead when operators edit facts in n8n.

---

### operator_business_context

**Status:** specified (T14-OC-1); **runtime:** implemented (T14-OC-2).

| Property | Rule |
|----------|------|
| Type | `string` or `null` |
| Required | **No** — omit or `null` when unused |
| Location | Top-level field on `POST /api/v1/webhook/message` body (sibling of `business_id`, `channel`, `customer`, `message`) |
| Max length | **8192 characters** (8 KiB text budget) |
| Response | **Never** echoed in webhook success `data` |
| Persistence | **Not** stored as a dedicated column in MVP; not written to `message.text` |

**Purpose:** Short, operator-editable business facts from n8n (e.g. weekly hours, promos, tone reminders) passed to backend as **reference notes** for Prompt Builder. Enables per-workflow edits without moving OpenAI or prompt assembly into n8n.

**Precedence (when T14-OC-2 is live):**

1. Platform system prompt and task instructions (**always win**).
2. `TenantBusinessProfile` from PostgreSQL (**primary** business facts).
3. `operator_business_context` from webhook (**additive** notes appended after DB profile text inside Prompt Builder section `tenant_business_context`).
4. Tenant AI profile, channel rules, knowledge, history, current customer message (reference data only).

Operator notes must **not** override platform safety, escalation, or task rules. Conflicting instructions in operator text are ignored in favor of platform layers.

**Security boundaries — must never appear in this field:**

- API keys, bot tokens, passwords, or other secrets;
- Provider API parameters or raw Telegram/WhatsApp payloads (use `message.raw_payload` for debug only);
- System prompts, “ignore previous instructions”, role overrides, or tool definitions;
- Content intended to replace `message.text` (customer utterance stays in `message.text`).

Treat as **reference notes**, not system instructions. Same data-class rules as tenant profile text in [prompt-builder-rules.md](../architecture/prompt-builder-rules.md) §4.5 and §5.

**n8n placement (after T14-OC-2 deployed — T14-OC-3 workflow change):**

```text
Telegram Trigger (or other provider)
  → Normalize Telegram Incoming
  → Add Business Context          ← Set node: static multiline operator_business_context
  → POST Backend                  ← /api/v1/webhook/message
  → Shape Customer Reply
  → Send via provider API
```

Do **not** put operator business facts in `message.text`, fake `customer.*` fields, or rely on `raw_payload` for AI context.

**Validation (T14-OC-2):** present non-null value longer than 8192 characters → `VALIDATION_ERROR`. Empty string may be normalized to `null` (implementation detail).

---

## Telegram Bot API mapping (n8n — T14.1)

Canonical normalize mapping for customer ingress: [`docs/ops/telegram-customer-ingress.md`](../../docs/ops/telegram-customer-ingress.md).

Summary:

| Normalized field | Telegram source |
|----------------|-----------------|
| `channel` | `"telegram"` |
| `business_id` | Workflow config (per client bot) |
| `customer.external_customer_id` | `message.from.id` (string; human user, not bot) |
| `customer.name` | `from.first_name` + `from.last_name` |
| `customer.phone` | `null` (MVP) |
| `message.text` | `message.text` (text-only MVP) |
| `message.external_message_id` | `tg:{chat.id}:{message.message_id}` |
| `message.external_conversation_id` | `tg:{chat.id}` |
| `message.timestamp` | `message.date` (Unix → ISO UTC) |

`message.chat.id` is used in n8n for outbound `sendMessage` and may appear in `raw_payload` only — not a separate top-level webhook field in MVP.

Full E1.2 alignment: [normalized-channel-contract.md](../architecture/normalized-channel-contract.md) §10.1.

No bot token in normalized payload.

---

# 8. Backend Response Contract

Backend returns normalized response to n8n.

---

## Response Structure

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "Hello! Sure. What service would you like to book and what time works best for you?",
    "lead_created": true,
    "lead": {
      "id": "8a6a3a5e-6c02-4b87-b8d4-12d10c86c111",
      "status": "new"
    },
    "conversation": {
      "id": "b62cfe3c-7b7e-4dd3-9c91-2eb35d2de901",
      "status": "open"
    },
    "notify_owner": true
  }
}
```

---

# 9. Error Response Contract

Error responses must be structured.

Example:

```json
{
  "success": false,
  "error": {
    "code": "BUSINESS_NOT_FOUND",
    "message": "Business was not found"
  }
}
```

---

# 10. Webhook Security

## Provider Verification

Where supported, providers should be verified.

Examples:

- WhatsApp verification token;
- Telegram webhook secret;
- signed webhook headers.

---

## Internal API Protection

n8n → backend communication should use:

```text
API token
```

Future options:

- JWT;
- internal network restriction;
- signed requests.

---

## HTTPS

All production webhook traffic must use HTTPS.

---

## Database Protection

Webhook systems must never access PostgreSQL directly.

Only backend may write to database.

---

# 11. Idempotency

Webhook systems must handle duplicate events safely.

Important fields:

```text
external_message_id
```

Backend should avoid storing the same provider message multiple times.

---

# 12. Logging

Webhook layer should log:

- incoming requests;
- failed validations;
- backend errors;
- provider API failures;
- notification failures.

Sensitive data must not appear in logs.

---

# 13. Timeout Handling

Webhook workflows should avoid long blocking operations.

Recommended future strategy:

```text
Webhook received
      ↓
Store event
      ↓
Background processing
```

MVP may process synchronously for simplicity.

---

# 14. Retry Strategy

Future versions should support retries for:

- backend unavailable;
- provider API unavailable;
- temporary network failures.

MVP may rely on provider retry behavior.

---

# 15. Future Webhook Features

Possible future features:

- delivery status webhooks;
- read receipts;
- typing indicators;
- media processing;
- audio transcription;
- webhook queues;
- async workers;
- event streaming.

These are not required for MVP.

---

# 16. What Is NOT Allowed

n8n workflows must not:

- contain business decision logic;
- directly write to PostgreSQL;
- permanently store conversation state;
- replace backend services;
- implement AI prompt logic.

These responsibilities belong to backend.

---

# 17. MVP Requirements

The MVP webhook system must support:

- receiving WhatsApp/test webhook messages;
- normalizing payloads;
- backend API communication;
- customer replies;
- owner notifications;
- duplicate-safe processing.

---

# 18. Success Criteria

Webhook architecture is successful if:

- providers can send messages into the system;
- n8n can normalize payloads;
- backend receives stable payload contracts;
- replies reach customers;
- owner notifications work;
- duplicate messages are handled safely;
- backend remains provider-independent;
- future channels can be added without backend rewrite.