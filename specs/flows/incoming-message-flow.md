# Alpstein AI — Incoming Message Flow

## 1. Purpose

This document describes the full incoming message flow for Alpstein AI MVP.

The incoming message flow is the core process of the platform.

It defines what happens when a customer sends a message to a business through:

- WhatsApp;
- Website Chat;
- Telegram;
- Instagram;
- future supported channels.

The flow must support:

- normalized webhook processing;
- tenant-aware business logic;
- configurable AI behavior;
- AI knowledge retrieval;
- prompt generation;
- lead creation;
- prompt execution logging;
- scalable SaaS architecture.

---

# 2. High-Level Flow

```text
Customer sends message
      ↓
External channel receives message
      ↓
n8n receives webhook
      ↓
n8n normalizes payload
      ↓
n8n sends request to backend
      ↓
backend validates payload
      ↓
backend identifies tenant
      ↓
backend identifies business
      ↓
backend identifies or creates customer
      ↓
backend creates or updates conversation
      ↓
backend saves incoming message
      ↓
AI Configuration Service loads AI context
      ↓
Knowledge Retrieval Service loads relevant knowledge
      ↓
Prompt Builder Service builds final prompt
      ↓
AI Gateway sends request to AI provider
      ↓
AI response is received
      ↓
prompt_runs record is created
      ↓
backend saves AI response
      ↓
backend detects lead intent
      ↓
backend creates or updates lead
      ↓
backend returns structured response to n8n
      ↓
n8n sends reply to customer
      ↓
n8n notifies business owner if needed
```

---

# 3. Main Actors

## Customer

The end user who sends a message.

Example:

```text
Hello, can I book a haircut tomorrow?
```

---

## External Channel

Communication channel.

Examples:

* WhatsApp;
* Telegram;
* Website Chat;
* Instagram.

---

## n8n

Responsible for:

* receiving webhooks;
* payload normalization;
* backend communication;
* sending replies;
* notifications.

n8n must not contain business logic.

---

## Backend

Responsible for:

* validation;
* customer handling;
* conversation handling;
* AI orchestration;
* lead creation;
* database operations.

---

## AI Configuration Service

Responsible for loading:

* business profile;
* AI profile;
* channel settings;
* prompt template configuration.

---

## Knowledge Retrieval Service

Responsible for loading relevant business knowledge.

---

## Prompt Builder Service

Responsible for assembling the final AI prompt.

---

## AI Gateway Service

Responsible for communicating with OpenAI or future providers.

---

## PostgreSQL

Responsible for storing:

* tenants;
* businesses;
* customers;
* conversations;
* messages;
* leads;
* AI configuration;
* prompt runs.

---

## Business Owner

Receives notifications when:

* lead is created;
* AI escalation is required;
* manual attention is needed.

---

# 4. Step-by-Step Flow

## Step 1 — Customer Sends Message

Customer sends a message.

Example:

```text
Hi, can I reserve a table tomorrow evening?
```

---

## Step 2 — Provider Sends Webhook

The provider sends a webhook to n8n.

Example:

```text
WhatsApp Cloud API → n8n webhook
```

Provider payloads are provider-specific.

Backend must never receive raw provider payload directly.

---

## Step 3 — n8n Receives Webhook

n8n receives the webhook.

Responsibilities:

* validate provider request;
* extract relevant fields;
* identify business;
* prepare normalized payload.

---

## Step 4 — n8n Normalizes Payload

n8n converts the payload into normalized structure via a **channel adapter** (provider-specific normalize → shared backend contract). Adapters set canonical `channel`, scoped external IDs, and optional `source` / `attribution` metadata — never mixed into `message.text`. See [channel-source-attribution.md](../architecture/channel-source-attribution.md).

Example:

```json
{
  "business_id": "demo_barbershop_001",
  "channel": "whatsapp",
  "customer": {
    "phone": "+41790000000",
    "name": "John",
    "external_customer_id": "wa_001"
  },
  "message": {
    "text": "Hello, can I book tomorrow?",
    "external_message_id": "wamid.example",
    "timestamp": "2026-05-21T10:00:00Z",
    "raw_payload": {}
  }
}
```

### Optional — operator business context (n8n)

Operators may attach editable business notes **after** normalize and **before** POST (T14-OC-3 n8n node). Spec: [webhooks.md](../api/webhooks.md) (`operator_business_context`).

```text
Normalize provider incoming
  → Add Business Context (n8n Set — static multiline text)
  → POST /api/v1/webhook/message
```

Field rules: top-level optional string, max 8192 characters, not in `message.text`, not primary via `raw_payload`, never secrets or system-instruction overrides. **T14-OC-2** backend work required before this field affects AI replies.

---

## Step 5 — n8n Sends Request To Backend

n8n sends request to:

```http
POST /api/v1/webhook/message
```

Authentication should use:

```text
API token
```

---

## Step 6 — Backend Validates Payload

Backend validates:

* required fields;
* channel;
* customer identity;
* timestamp;
* message text;
* business identifier;
* optional `operator_business_context` length ≤ 8192 characters when present (T14-OC-2).

Validation errors must return structured responses.

---

## Step 7 — Backend Identifies Tenant

Backend identifies tenant through:

```text
business.external_id
→ business
→ tenant_id
```

Tenant isolation is mandatory.

All future operations must filter by:

```text
tenant_id
```

---

## Step 8 — Backend Identifies Business

Backend loads business entity.

Backend also loads:

* storage mode;
* timezone;
* channel configuration;
* active AI configuration.

---

## Step 9 — Backend Identifies Or Creates Customer

Customer is identified by:

```text
business_id + phone
```

If customer does not exist:

* create customer;
* assign tenant_id;
* assign business_id;
* assign source channel.

---

## Step 10 — Backend Resolves Conversation (Reuse Or Create)

Before saving the incoming message, the backend must attach it to exactly one conversation for the same communication thread.

### Lookup scope

A conversation is a candidate for reuse only when all of the following match the incoming webhook:

```text
tenant_id
business_id
customer_id
channel
```

`channel` must match the normalized webhook value (`whatsapp`, `telegram`, `instagram`, `website_chat`, `test`).

For **Telegram customer ingress** (n8n): normalize Bot API `Update` → backend contract per [`docs/ops/telegram-customer-ingress.md`](../../docs/ops/telegram-customer-ingress.md) (T14.1). MVP: private text messages; `external_message_id` = `tg:{chat_id}:{message_id}`; `external_customer_id` = Telegram user id (`from.id`).

Tenant isolation is mandatory: lookup and creation must always filter by `tenant_id`.

### Reusable statuses (incoming messages)

If a conversation exists with one of these statuses, the backend **must reuse** it and must **not** create a new conversation for the same lookup scope:

```text
open
waiting_for_customer
waiting_for_owner
```

| Status | Meaning for reuse |
|--------|-------------------|
| `open` | Active thread; customer and AI/owner may continue exchanging messages. |
| `waiting_for_customer` | Business or AI has replied; thread stays open until the customer responds again. |
| `waiting_for_owner` | Escalated or manual follow-up; customer messages still belong to the same thread. |

When reusing:

* append the incoming message to the existing `conversation_id`;
* update conversation activity fields (for example `last_message_at`, `updated_at`) as part of the same transaction;
* do not create a second active conversation for the same `tenant_id` + `business_id` + `customer_id` + `channel`.

### Non-reusable statuses (incoming messages)

If the only matching conversations have one of these statuses, the backend **must not** reuse them:

```text
closed
archived
```

| Status | Meaning for reuse |
|--------|-------------------|
| `closed` | Thread ended intentionally; a new customer message starts a **new** conversation. |
| `archived` | Long-term retention; never attach new customer messages to an archived row. |

When no reusable conversation exists (including when only `closed` or `archived` rows exist):

* create a new conversation;
* set `status = open`;
* set `is_ai_active = true` (unless business rules later disable AI for that conversation).

Historical `closed` and `archived` conversations remain in the database for history, leads, and `PromptRun` linkage; they are not deleted when a new conversation is created.

### Multiple reusable matches

Normally there should be at most one reusable conversation per lookup scope. If more than one row exists (data repair or legacy state), the backend must select **one** conversation deterministically:

1. Prefer the row with the latest `last_message_at` (non-null values first).
2. If still tied, prefer the latest `created_at`.

All other reusable rows for that scope should be treated as a data-quality issue and resolved outside the hot path (admin/repair), not by creating another parallel conversation.

### Relationship to later steps

Conversation **status transitions** after AI reply, owner handoff, or explicit close (for example `open` → `waiting_for_customer`) are defined in orchestration and notification flows. This step only defines **which existing row** receives the incoming customer message.

See also: [entities.md](../database/entities.md) (Conversation entity) and [database-schema.md](../database/database-schema.md) (`conversations.status` values).

---

## Step 11 — Backend Saves Incoming Message

Backend saves customer message.

Message fields include:

* tenant_id;
* business_id;
* conversation_id;
* sender_type = customer;
* direction = incoming;
* message_text;
* raw_payload;
* external_message_id;
* created_at.

Duplicate protection should use:

```text
external_message_id
```

---

# 5. AI Configuration Flow

## Step 12 — AI Configuration Service Loads Context

AI Configuration Service loads:

* TenantBusinessProfile;
* TenantAIProfile;
* TenantChannelSetting;
* PromptTemplate.

The platform safety layer must always stay above tenant configuration.

Optional webhook `operator_business_context` (when T14-OC-2 is implemented) is passed separately into Prompt Builder and appended after `TenantBusinessProfile` text as operator reference notes — not loaded from PostgreSQL and not merged into `message.text`. See [prompt-builder-rules.md](../architecture/prompt-builder-rules.md) §4.5.

---

## Step 13 — Knowledge Retrieval Service Loads Knowledge

Knowledge Retrieval Service searches:

```text
tenant_knowledge_sources
```

Examples:

* FAQ;
* pricing;
* policies;
* service descriptions;
* instructions.

MVP may use:

```text
PostgreSQL full-text search
```

Future versions may use vector retrieval.

---

## Step 14 — Backend Loads Conversation History

Backend loads recent messages.

Recommended MVP history:

```text
last 10-20 messages
```

---

## Step 15 — Prompt Builder Builds Final Prompt

Prompt Builder combines:

```text
Core system prompt
Tenant business context
Tenant AI profile
Channel rules
Relevant knowledge
Conversation history
Latest customer message
```

---

## Step 16 — AI Gateway Sends Request To AI Provider

AI Gateway sends request to:

```text
OpenAI API
```

Future providers may include:

* Anthropic;
* Gemini;
* local models.

AI Gateway is the only module allowed to communicate directly with AI providers.

---

## Step 17 — AI Response Is Received

AI generates response.

AI must:

* stay within business context;
* avoid hallucinations;
* avoid unsupported promises;
* ask clarifying questions;
* escalate when uncertain.

---

## Step 18 — PromptRun Is Created

Every AI execution must create a:

```text
PromptRun
```

PromptRun stores:

* tenant_id;
* business_id;
* conversation_id;
* message_id;
* prompt_template_id;
* prompt_version;
* model;
* input_tokens;
* output_tokens;
* latency;
* result;
* error.

This is critical for:

* debugging;
* analytics;
* token tracking;
* quality control.

---

## Step 19 — Backend Saves AI Message

Backend stores AI response as message.

Required values:

* sender_type = ai;
* direction = outgoing;
* message_text;
* ai_metadata;
* timestamps.

---

# 6. Lead Flow

## Step 20 — Backend Detects Lead Intent

Backend analyzes whether customer shows business intent.

Examples:

* booking;
* order;
* consultation;
* pricing inquiry;
* reservation.

---

## Step 21 — Backend Creates Or Updates Lead

If lead intent exists:

* create lead;
* update lead;
* assign status;
* assign priority.

Possible statuses:

```text
new
in_progress
contacted
closed
lost
```

---

# 7. Backend Response Flow

## Step 22 — Backend Returns Structured Response

Example:

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "Sure. What time would you prefer?",
    "lead_created": true,
    "notify_owner": true
  }
}
```

---

## Step 23 — n8n Sends Reply To Customer

n8n sends response through original provider API.

Example:

```text
n8n → WhatsApp Cloud API
```

Backend must not communicate directly with providers.

---

## Step 24 — n8n Sends Owner Notification

If:

```json
{
  "notify_owner": true
}
```

n8n triggers owner notification workflow.

Possible channels:

* Telegram;
* email;
* WhatsApp.

---

# 8. AI Safety Rules

The AI system must enforce:

* no hallucinated availability;
* no fake promises;
* no unauthorized legal/medical advice;
* no system prompt exposure;
* no tenant override of platform safety rules;
* escalation when uncertain.

---

# 9. Error Handling Flow

## Validation Error

```text
backend returns VALIDATION_ERROR
n8n logs error
```

---

## Business Not Found

```text
BUSINESS_NOT_FOUND
```

Should trigger admin investigation.

---

## AI Provider Failure

Backend should return safe fallback response.

Example:

```text
Sorry, something went wrong. A team member will contact you soon.
```

---

## Database Failure

Backend returns:

```text
DATABASE_ERROR
```

n8n logs the issue.

---

# 10. Idempotency

Webhook providers may send duplicate events.

Backend must prevent duplicate processing using:

```text
external_message_id
```

Duplicate messages must not:

* create duplicate leads;
* create duplicate messages;
* trigger duplicate AI executions.

---

# 11. Security Requirements

The flow must enforce:

* HTTPS only;
* API token between n8n and backend;
* tenant isolation;
* no direct DB writes from n8n;
* no raw secrets in logs;
* protected AI configuration;
* protected prompt templates.

---

# 12. MVP Simplifications

MVP may simplify:

* AI retrieval;
* prompt management UI;
* vector search;
* advanced AI routing;
* async workers;
* analytics.

Allowed MVP simplifications:

```text
single OpenAI model
PostgreSQL full-text search
simple prompt templates
manual AI profile setup
```

---

# 13. What Is NOT Included

Not included in MVP:

* voice calls;
* advanced dashboard;
* billing;
* semantic vector memory;
* multi-agent orchestration;
* AI self-learning;
* enterprise RBAC;
* automatic workflow generation.

---

# 14. Success Criteria

The flow is successful if:

* customer messages reach backend;
* tenant isolation works;
* AI behavior is configurable;
* prompts are dynamically assembled;
* PromptRuns are logged;
* AI responses are stored;
* leads are created correctly;
* replies reach customers;
* owners receive notifications;
* backend remains provider-independent;
* incoming customer messages reuse the correct active conversation per channel thread;
* `closed` and `archived` conversations never receive new customer messages.