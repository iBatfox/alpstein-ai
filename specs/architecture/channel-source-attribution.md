# Alpstein AI — Channel & Source Attribution Architecture

## 1. Purpose

This document defines how Alpstein AI records **where a customer message came from** across current and future ingress platforms, without mixing transport metadata into `message.text` or using `raw_payload` as primary AI input.

**Status:** architecture / spec design (no implementation in this document)  
**Date:** 2026-05-25  
**Depends on:** [webhooks.md](../api/webhooks.md), [normalized-channel-contract.md](normalized-channel-contract.md) (E1.2), [database-schema.md](../database/database-schema.md), [prompt-builder-rules.md](prompt-builder-rules.md), [incoming-message-flow.md](../flows/incoming-message-flow.md)

**Out of scope here:** cross-channel identity resolution, DB migrations, n8n workflow redesign, Telegram workflow changes.

---

## 2. Design brief

| Item | Decision |
|------|----------|
| **Consumers** | n8n channel adapters → backend webhook; AI Prompt Builder; leads/CRM analytics; future dashboard |
| **Contract** | Extend normalized `POST /api/v1/webhook/message` with structured `source` + `attribution` objects |
| **Canonical routing key** | Existing top-level `channel` (Alpstein enum) + `business_id` |
| **Tenant isolation** | Unchanged — `business_id` → `tenant_id`; all persisted rows include `tenant_id` |
| **MVP** | Document full model; implement minimal slice (see §10) |
| **Risks** | Secret leakage in metadata; prompt injection via attribution strings; duplicate external IDs across channels |

---

## 3. Concepts

### 3.1 `channel` (Alpstein canonical)

**Required** top-level field. Alpstein-controlled vocabulary used for:

- conversation reuse key (`tenant_id` + `business_id` + `customer_id` + **`channel`**);
- `TenantChannelSetting` lookup;
- Prompt Builder `channel_rules`;
- `leads.source_channel` / `customers.source_channel` snapshot.

MVP values (existing):

```text
whatsapp | telegram | instagram | website_chat | test
```

Future values (register in spec before use):

```text
facebook_messenger | email | sms | voice | custom_api
```

`channel` is **not** a free-form operator string. Adapters map provider-specific types → canonical `channel`.

### 3.2 `source_platform` (adapter / provider detail)

Optional finer label for **analytics and adapter versioning**, e.g.:

| `channel` | Example `source_platform` |
|-----------|---------------------------|
| `whatsapp` | `meta_whatsapp_cloud` |
| `telegram` | `telegram_bot_api` |
| `website_chat` | `web_widget_v1` |
| `instagram` | `meta_instagram_dm` |
| `email` | `imap` / `google_workspace` |
| `custom_api` | `partner_crm_webhook` |

May equal `channel` when no sub-platform distinction is needed. **Never** replaces `channel` for routing or conversation keys.

### 3.3 Channel adapter

Per-platform **n8n workflow branch** (or future edge service) that:

1. Receives provider-native webhook/event.
2. Validates signature/auth at the edge (not in backend).
3. Maps to normalized JSON (§4).
4. Sets canonical `channel` + scoped external IDs.
5. Puts provider-native blob in `message.raw_payload` only.

Backend must not import provider SDKs or parse raw Telegram/WhatsApp payloads in MVP.

```text
Provider event
  → Channel Adapter (n8n normalize)
  → POST /api/v1/webhook/message
  → Backend (channel-agnostic)
```

One adapter per ingress family; shared “core normalize” code pattern in n8n, not duplicated business logic.

### 3.4 External ID scoping

All external identifiers are **scoped by `business_id` + `channel`** (and provider namespace where applicable):

| Field | Scope | Uniqueness (MVP) |
|-------|--------|------------------|
| `external_message_id` | per business | partial unique on `messages(business_id, external_message_id)` |
| `external_customer_id` | per business + channel identity | not globally unique across channels |
| `external_conversation_id` | per business + channel thread | stored on `conversations`; adapter-defined format |

Recommended ID formats (document per adapter, prefix by channel):

```text
tg:{chat_id}:{message_id}
wa:{phone_number_id}:{wamid}
web:{session_id}:{message_id}
```

Same human on Telegram and WhatsApp ⇒ **two customers** in MVP (no identity resolution).

---

## 4. Recommended normalized webhook extension

Extend [webhooks.md](../api/webhooks.md) §7 without breaking existing clients.

### 4.1 Top-level shape

```json
{
  "business_id": "demo_barbershop_001",
  "channel": "telegram",
  "operator_business_context": null,
  "source": {
    "platform": "telegram_bot_api",
    "account_id": "8123456789",
    "account_name": "@DemoBarbershopBot",
    "locale": "de-CH",
    "country": "CH",
    "region": null,
    "timezone": "Europe/Zurich"
  },
  "attribution": {
    "marketing_source": null,
    "campaign_id": null,
    "landing_page_url": null,
    "referrer_url": null,
    "utm_source": null,
    "utm_medium": null,
    "utm_campaign": null,
    "utm_content": null,
    "utm_term": null
  },
  "customer": {
    "phone": null,
    "name": "John",
    "email": null,
    "external_customer_id": "123456789"
  },
  "message": {
    "text": "Hello, can I book tomorrow?",
    "external_message_id": "tg:987654321:42",
    "external_conversation_id": "tg:987654321",
    "timestamp": "2026-05-21T10:00:00Z",
    "client": {
      "user_agent": null,
      "ip_address_hash": null
    },
    "raw_payload": {}
  }
}
```

### 4.2 Field catalog

| Field | Location | Required | Type | Purpose |
|-------|----------|----------|------|---------|
| `channel` | top | **yes** | enum string | Alpstein routing, AI channel rules, DB `*.channel` |
| `source.platform` | `source` | no | string | Adapter/provider id (`source_platform`) |
| `source.account_id` | `source` | no | string | Business-owned account on platform (bot id, WA phone_number_id, page id) |
| `source.account_name` | `source` | no | string | Human-readable account label (@bot, display phone) |
| `source.locale` | `source` | no | string | BCP 47 (`de-CH`) for AI language hints |
| `source.country` | `source` | no | string | ISO 3166-1 alpha-2 |
| `source.region` | `source` | no | string | Region/state when known |
| `source.timezone` | `source` | no | string | IANA TZ; fallback business timezone |
| `customer.external_customer_id` | `customer` | conditional | string | Provider user id (existing) |
| `message.external_message_id` | `message` | no | string | Idempotency key (existing) |
| `message.external_conversation_id` | `message` | no | string | Thread/session/chat id on provider |
| `message.timestamp` | `message` | no | datetime | Provider event time (existing) |
| `attribution.marketing_source` | `attribution` | no | string | Coarse bucket: `organic`, `paid`, `referral`, `direct` |
| `attribution.campaign_id` | `attribution` | no | string | Internal or ad platform campaign id |
| `attribution.landing_page_url` | `attribution` | no | string | First-touch URL (website chat) |
| `attribution.referrer_url` | `attribution` | no | string | HTTP Referer |
| `attribution.utm_*` | `attribution` | no | string | Standard UTM parameters |
| `message.client.user_agent` | `message.client` | no | string | **Website chat only** — browser UA |
| `message.client.ip_address_hash` | `message.client` | no | string | Privacy-safe hashed IP (see §8) |
| `message.raw_payload` | `message` | no | object | Debug/audit only — **never** primary AI input |

**Rules:**

- **Must not** embed attribution or platform ids in `message.text`.
- **Must not** put tokens, secrets, or full OAuth responses in `source`, `attribution`, or `message.client`.
- Omit optional objects/keys when unknown (preferred over empty strings).
- Extra top-level keys: ignored until explicitly added to spec (Pydantic `extra=ignore` in MVP).

### 4.3 Channel-specific expectations

| Channel | `customer.phone` | Typical `source.account_id` | Attribution block |
|---------|------------------|----------------------------|-------------------|
| `telegram` | often null | bot user id | usually empty |
| `whatsapp` | E.164 when available | Meta `phone_number_id` | usually empty |
| `website_chat` | optional | widget/site id | **often populated** (UTM, referrer) |
| `instagram` | null | IG business account id | optional |
| `email` | null / email in `customer.email` | mailbox id | optional campaign headers (future) |
| `sms` | E.164 | sender number id | optional |
| `voice` | E.164 | trunk/line id | optional call metadata (future) |

---

## 5. Channel adapter model

### 5.1 Responsibilities

| Layer | Owns |
|-------|------|
| **Channel adapter (n8n)** | Provider auth, normalize, canonical `channel`, external IDs, `raw_payload`, optional `source`/`attribution` |
| **Backend webhook** | Validate normalized contract, persist, orchestrate AI/leads |
| **AI Configuration** | `TenantChannelSetting` per `channel` |
| **Prompt Builder** | Safe subset of `source` + `attribution` as reference data (§7) |

### 5.2 Adapter registry (conceptual)

| Adapter id | `channel` | Ingress (MVP / future) |
|------------|-----------|-------------------------|
| `telegram_bot` | `telegram` | MVP (live) |
| `whatsapp_cloud` | `whatsapp` | MVP planned |
| `website_widget` | `website_chat` | future |
| `instagram_dm` | `instagram` | future |
| `meta_messenger` | `facebook_messenger` | future |
| `email_inbound` | `email` | future |
| `sms_gateway` | `sms` | future |
| `voice_pbx` | `voice` | future |
| `custom_webhook` | `custom_api` | future |

Each adapter document (ops/docs) must define: external ID format, required customer identifiers, and example `raw_payload` shape.

### 5.3 Normalization pipeline (n8n)

```text
Provider Trigger
  → Validate provider signature (adapter)
  → Map to normalized body (§4)
  → Optional: operator_business_context (see operator-business-context doc)
  → POST Backend
```

Adapters **must not** call OpenAI or PostgreSQL.

---

## 6. Database field placement

No migration in this task. Recommended **target** mapping when implemented.

### 6.1 Summary matrix

| Field group | `customers` | `conversations` | `messages` | `leads` | `tenant_channel_settings` | `raw_payload` only |
|-------------|-------------|---------------|------------|---------|----------------------------|-------------------|
| `channel` | `source_channel` (first touch) | `channel` | `channel` | `source_channel` | key = `channel` | — |
| `source.platform` | optional future `metadata` | snapshot in `metadata` or column | per-message `metadata` | snapshot on create | `metadata` | provider version strings |
| `source.account_id` | — | `metadata` or future column | `metadata` | — | `metadata` (credential **ref**, not secret) | provider account blobs |
| `source.account_name` | — | `metadata` | `metadata` | — | display name | — |
| `external_customer_id` | `external_customer_id` | — | — | — | — | provider user object |
| `external_conversation_id` | — | `external_conversation_id` | copy on first message | — | — | full chat/thread object |
| `external_message_id` | — | — | `external_message_id` | — | — | provider message envelope |
| `attribution.*` | — | first-touch `metadata` | `metadata` (esp. website) | copy at lead create | — | ad network raw responses |
| `locale`, `country`, `region`, `timezone` | `language` / future `metadata` | `metadata` | `metadata` | — | — | geo IP databases |
| `user_agent` | — | — | `metadata` | — | — | full browser headers |
| `ip_address_hash` | — | — | `metadata` | — | — | raw IP addresses |
| Provider tokens / secrets | **never** | **never** | **never** | **never** | secret **reference** only | always |

### 6.2 Table notes

**customers**

- Keep `source_channel` = canonical `channel` at **first creation** (existing MVP).
- `external_customer_id` is channel-scoped provider user id; do not reuse across channels without future identity service.
- Do not store UTM columns on customer in MVP; optional first-touch JSON in future `customers.metadata`.

**conversations**

- `channel` + `external_conversation_id` define thread reuse (with status rules in incoming-message-flow).
- Store adapter snapshot (`source.account_*`, locale) in `conversations.metadata` at create if needed for analytics.

**messages**

- `channel` duplicated for query performance (existing).
- Use `messages.metadata` JSONB for per-message attribution (website first message) and `message.client` fields.
- `raw_payload` for audit only; backend must not depend on it for business logic.

**leads**

- `source_channel` = conversation `channel` at lead creation (existing).
- On create, copy non-empty `attribution` fields into `leads` columns or `metadata` for CRM/export (future migration).

**tenant_channel_settings**

- One row per (`tenant`, `business`, `channel`) for AI behavior.
- `metadata` holds non-secret connection refs (e.g. n8n credential name, `phone_number_id`, bot id) — see [telegram-channel-credentials.md](../../docs/architecture/telegram-channel-credentials.md).

### 6.3 Indexes (future)

- Keep idempotency index on `messages(business_id, external_message_id)`.
- Optional: `conversations(business_id, channel, external_conversation_id)` unique where not null.
- Analytics: `leads(source_channel)`, `messages.metadata` GIN only if query patterns justify (post-MVP).

---

## 7. Prompt Builder usage

Align with [prompt-builder-rules.md](prompt-builder-rules.md). Source metadata is **reference data**, not system instructions.

### 7.1 What may enter the assembled prompt

When present and validated (post-implementation), a labeled block under or adjacent to **section 5 (`channel_rules`)**:

```text
CHANNEL SOURCE CONTEXT (reference only)
Channel: telegram
Platform: telegram_bot_api
Account: @DemoBarbershopBot
Locale: de-CH
Country: CH
```

Website chat may additionally include **sanitized** attribution summary:

```text
Attribution: utm_source=google; utm_campaign=spring; landing=/booking
```

### 7.2 What must never enter the prompt

- `message.raw_payload`
- `ai_metadata`, tokens, API keys
- Raw IP addresses (hashed only if product approves; **omit in MVP AI slice**)
- Full `user_agent` strings longer than budget — trim or omit in MVP
- UTM/content that looks like instruction injection — apply same precedence as tenant text (platform wins)

### 7.3 Precedence

```text
platform_system + task_instructions
  → tenant_business_context (+ operator_business_context)
  → tenant_behavior
  → channel_rules
  → channel_source_context (new, optional, small)
  → knowledge
  → history
  → current_customer_message
```

`channel_source_context` is truncated first within variable budget (same tier as `channel_rules` / section 5–6).

### 7.4 When to omit

- Messenger channels with only `channel` + `locale`: optional one-line channel label.
- Empty `attribution` object: omit attribution lines entirely.
- Do not fabricate marketing data.

---

## 8. Privacy & security

| Topic | Rule |
|-------|------|
| **Secrets** | No bot tokens, WA tokens, API keys, webhook secrets in normalized `source`/`attribution`/`metadata` sent to backend |
| **PII** | `message.text` and `customer.*` follow existing retention rules; attribution URLs may contain query PII — treat as confidential business data |
| **IP** | Store **hashed** IP only (`ip_address_hash`); algorithm and salt documented in implementation; raw IP only in `raw_payload` if at all, with retention limit |
| **user_agent** | Website chat only; truncate before persistence and before AI |
| **raw_payload** | Audit/debug; not exposed in customer API; not fed to Prompt Builder |
| **Cross-tenant** | Adapter must set correct `business_id`; backend validates business → tenant |
| **Injection** | `source`/`attribution` strings are data blocks; platform safety precedes them |

GDPR note: document lawful basis and retention for attribution fields in a future privacy appendix; MVP stores minimum fields needed for lead source reporting.

---

## 9. Relationship to existing contracts

| Document | Change in this task |
|----------|---------------------|
| [webhooks.md](../api/webhooks.md) | Pointer to this doc; full §4 schema deferred to implementation slice |
| [incoming-message-flow.md](../flows/incoming-message-flow.md) | Adapters normalize `source`/`attribution` at Step 4 (future note) |
| [database-schema.md](../database/database-schema.md) | No column changes; §6 describes target use of `metadata` |
| [prompt-builder-rules.md](prompt-builder-rules.md) | Optional `channel_source_context` noted in §7 above |
| Telegram workflow | **Unchanged** — continues `channel=telegram` + existing external id rules |

---

## 10. MVP implementation slice proposal

Implement in order; each slice is independently reviewable.

| ID | Task | Scope | Depends |
|----|------|-------|---------|
| **ATTR-1** | **This architecture spec** | Design only | — |
| **ATTR-2** | Pydantic `ChannelSource`, `MessageAttribution`, `MessageClientContext` on `NormalizedWebhookMessageRequest`; validate lengths; `extra=ignore` on nested models | Backend schema | ATTR-1 |
| **ATTR-3** | Persist: copy `external_conversation_id` to conversation; write safe subset to `messages.metadata` on inbound save | MessageService / ConversationService | ATTR-2 |
| **ATTR-4** | Prompt Builder: optional `channel_source_context` block (channel, platform, locale, country; website UTM one-liner) | AI integration | ATTR-2, prompt-builder-rules |
| **ATTR-5** | Lead create: snapshot `source_channel` + attribution fields into lead `metadata` or columns | LeadService + migration if columns | ATTR-3 |
| **ATTR-6** | Adapter docs: WhatsApp + website chat field mapping tables in `docs/ops/` | n8n / ops | ATTR-1 |
| **ATTR-7** | Analytics export API or admin list filters by `source_channel` / UTM | API designer + backend | ATTR-5 |

**Explicitly post-MVP**

- Cross-channel identity resolution (merge customers)
- `email` / `sms` / `voice` adapters
- Dedicated attribution columns on `leads` (optional before ATTR-5 if CRM export is urgent)
- AI use of `ip_address_hash`

**Parallel safe work**

- Telegram ingress continues without `source`/`attribution` objects until ATTR-2 (optional fields).

---

## 11. Open questions (for approval)

1. **Nested vs flat webhook JSON:** This spec uses `source` + `attribution` objects; confirm n8n Set nodes prefer nesting over flat top-level `utm_source`.
2. **`facebook_messenger` vs `instagram`:** Separate channels or Instagram family with different `source.platform`?
3. **`messages.metadata` schema:** Free-form JSON vs versioned `metadata.schema_version` field.
4. **Lead attribution storage:** JSONB snapshot vs dedicated `utm_source` columns for reporting.
5. **IP hash:** Required for website chat in CH/EU MVP, or defer entirely?
6. **Identity graph:** When to introduce `customer_identities` table — post-MVP milestone.

---

## 12. Success criteria

Architecture is approved when:

- every listed field has a defined place (DB, prompt, or raw_payload-only);
- channel adapters have a clear boundary from backend business logic;
- AI and CRM can answer “which channel did this lead come from?” without reading `raw_payload`;
- MVP slices are ordered without blocking current Telegram production path.
