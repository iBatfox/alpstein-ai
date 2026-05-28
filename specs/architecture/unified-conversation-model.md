# Unified Conversation Model (E2.0 — spec)

**Status:** design-only (approved direction; no runtime)  
**Date:** 2026-05-28  
**Depends on:** E1 unified ingress (`alpstein-customer-ingress`), [`normalized-channel-contract.md`](normalized-channel-contract.md), [`multi-channel-identity-strategy.md`](../../docs/architecture/multi-channel-identity-strategy.md)  
**Runtime map:** [`docs/ops/runtime-map.md`](../../docs/ops/runtime-map.md) — no new ports/containers in E2

---

## 1. Purpose

Define the **canonical data model** for multi-channel conversation continuity under the golden rule:

> **One flow = one bot behavior.**

A **flow** is a configured business scenario (persona, rules, knowledge scope). A **channel** is transport (Telegram, Website Chat, WhatsApp). A **conversation** is one customer dialogue **inside exactly one flow**. A **message** is one inbound/outbound/system event **inside exactly one conversation**.

This spec extends MVP tables (`conversations`, `messages`, `customers`) with **`flows`** and stricter scoping. Implementation is deferred to E2.1+ migrations.

---

## 2. Terms

| Term | Definition |
|------|------------|
| **Flow** | Bot behavior configuration bound to `tenant_id` + `business_id`; has `flow_key` stable for n8n/backend |
| **Channel** | Transport enum: `telegram`, `website_chat`, `whatsapp`, `test`, … |
| **Conversation** | Customer dialogue instance scoped to **one flow** + **one channel** thread |
| **Customer identity** | `customers` row (channel-scoped contact); **not** equal to conversation |
| **Flow config** | Prompt/operator/knowledge inputs — **not** stored as conversation history |
| **Conversation history** | Persisted `messages` only (what customer/AI/owner/system actually said) |

---

## 3. Entity model

### 3.1 Flow (new table — future)

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID PK | yes | Internal id |
| `tenant_id` | UUID FK | yes | Tenant isolation |
| `business_id` | UUID FK | yes | Business isolation |
| `flow_key` | VARCHAR(100) | yes | Stable external key, e.g. `alpstein_assistant`, `barbershop_booking` |
| `flow_name` | VARCHAR(255) | yes | Operator label |
| `status` | VARCHAR(50) | yes | `active` \| `inactive` \| `archived` |
| `default_channel_settings` | JSONB | no | Optional defaults; channel overrides in `tenant_channel_settings` remain |
| `metadata` | JSONB | no | Non-secret tags only |
| `created_at` / `updated_at` | TIMESTAMP | yes | Standard |

**Uniqueness:** `UNIQUE (business_id, flow_key)`

**MVP bridge (E2.1 backfill):** one default flow per existing `businesses` row:

| `business.external_id` | Suggested `flow_key` |
|------------------------|----------------------|
| `alpstein_ai_demo_001` | `alpstein_assistant` |
| `demo_barbershop_001` | `barbershop_default` |

n8n unified ingress resolves `business_id` + **`flow_key`** (or implicit default flow for business until explicit flow routing exists).

### 3.2 Conversation (extended)

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID PK | yes | `conversation_id` in APIs/traces |
| `tenant_id` | UUID FK | yes | |
| `business_id` | UUID FK | yes | |
| **`flow_id`** | UUID FK → `flows` | **yes (E2)** | **Required** — prevents cross-flow merge |
| `customer_id` | UUID FK | yes | |
| `channel` | VARCHAR(50) | yes | Canonical channel |
| `external_conversation_id` | VARCHAR(255) | recommended | `tg:{chat_id}`, `web:{session_id}` |
| `status` | VARCHAR(50) | yes | `open`, `waiting_for_customer`, `waiting_for_owner`, `closed`, `archived` |
| `is_ai_active` | BOOLEAN | yes | |
| `identity_confidence` | VARCHAR(50) | no | `high` \| `medium` \| `low` \| `anonymous` (E1.4 aligned) |
| `first_seen_at` | TIMESTAMP | no | First inbound in conversation |
| `last_seen_at` | TIMESTAMP | no | Mirrors `last_message_at` semantics |
| `source_attribution` | JSONB | no | Safe subset from webhook `source`/`attribution` (ATTR-3) |
| `channel_metadata` | JSONB | no | Non-secret channel facts (locale, widget version) |
| `crm_external_contact_id` | VARCHAR(255) | no | Future CRM link — **no auto-merge** |
| `created_at` / `updated_at` | TIMESTAMP | yes | |

**Conversation lookup (target — replaces customer-only reuse):**

```text
PRIMARY: (flow_id, channel, external_conversation_id)
  WHERE external_conversation_id IS NOT NULL
  AND status IN reusable set

FALLBACK (no external_conversation_id yet):
  (flow_id, channel, customer_id) + reusable status
  — same as today but scoped by flow_id
```

**Index (recommended):**

```text
INDEX conversations_flow_channel_external_idx
  ON conversations(flow_id, channel, external_conversation_id)
  WHERE external_conversation_id IS NOT NULL

UNIQUE conversations_flow_channel_external_open_unique
  ON conversations(flow_id, channel, external_conversation_id)
  WHERE external_conversation_id IS NOT NULL
    AND status IN ('open','waiting_for_customer','waiting_for_owner')
```

*Note:* Exact partial unique definition subject to product decision on multiple open threads per external id.

### 3.3 Customer / CustomerIdentity

**Today:** `customers` table with `UNIQUE (business_id, source_channel, external_customer_id)`.

**E2 alignment:**

| Concept | Storage | Scope |
|---------|---------|-------|
| Channel contact | `customers` | `business_id` + `source_channel` + `external_customer_id` |
| CustomerIdentity (logical) | Same row + optional `identity_confidence` on conversation | Not cross-channel merged in MVP |

Same human in flow A vs flow B → **different conversations**, may share `customers` row only if same channel identity key (Telegram user id) — still **separate conversations** per flow.

### 3.4 Message (extended semantics)

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | UUID PK | yes | `message_id` |
| `tenant_id`, `business_id` | UUID FK | yes | Denormalized for tenant-safe queries |
| **`flow_id`** | UUID FK | yes (E2) | Denormalized from conversation |
| `conversation_id` | UUID FK | **yes** | **No message outside conversation** |
| `sender_type` | enum | yes | `customer`, `ai`, `owner`, `system` |
| `direction` | enum | yes | `incoming`, `outgoing`, `system` |
| `channel` | enum | yes | Copy from conversation at write time |
| `message_text` | TEXT | yes | Customer-visible text |
| `message_type` | enum | yes | `text` MVP |
| `external_message_id` | VARCHAR(255) | no | Idempotency key |
| `idempotency_key` | VARCHAR(255) | no | Alias = `external_message_id` when set; future explicit key |
| `normalized_payload` | JSONB | no | Safe normalized subset (not full provider blob) |
| `raw_payload` | JSONB | no | Audit only — redacted in traces |
| `ai_metadata` | JSONB | no | Model metadata |
| `metadata` | JSONB | no | Attribution/client subset |
| `created_at` | TIMESTAMP | yes | |

**Idempotency (target — flow-scoped):**

```text
UNIQUE messages_flow_channel_external_unique
  ON messages(flow_id, channel, external_message_id)
  WHERE external_message_id IS NOT NULL
```

Deprecate business-only unique index after backfill + dual-write validation.

**Duplicate handling:** unchanged semantics — second POST with same key returns existing message, `is_duplicate: true`, no second AI turn unless product defines otherwise.

---

## 4. Database Separation & Flow Governance

### 4.1 Relationship diagram (text)

```text
tenants
  └── businesses
        └── flows (1:N)
              ├── tenant_business_profiles / tenant_ai_profiles / knowledge (per business; flow may select subset later)
              └── conversations (N) ── belongs to exactly one flow
                    ├── customers (contact identity)
                    └── messages (N) ── belongs to exactly one conversation

message_traces (future) ── links correlation_id, n8n_execution_id, prompt_run_id, message_id, flow_id
prompt_runs ── AI execution audit; references conversation_id, message_id
```

### 4.2 Separation rules (enforced)

| Rule | Enforcement |
|------|-------------|
| Conversation ∈ one flow | `conversations.flow_id NOT NULL` + FK |
| Message ∈ one conversation | `messages.conversation_id NOT NULL` + FK |
| No cross-flow history | Queries filter `flow_id`; PromptBuilder history scoped to `conversation_id` |
| No cross-tenant merge | `tenant_id` on all client tables |
| Flow config ≠ memory | Profiles/knowledge in config tables; **never** append full profile text into `messages` |
| n8n selects flow | Normalizer sets `flow_key` / `flow_id`; n8n does not store dialogue memory |
| Channel ≠ conversation | `external_conversation_id` thread key; never use `channel_user_id` alone as `conversation_id` |

### 4.3 Examples

**Example A — Same Telegram user, same flow**

- `flow_key=alpstein_assistant`, `channel=telegram`, `external_customer_id=12345`, `external_conversation_id=tg:987654321`
- Second message reuses same `conversation_id` via `(flow_id, channel, external_conversation_id)`.

**Example B — Same Telegram user, different flow**

- Flow `alpstein_assistant` vs `alpstein_sales_demo` on same business (future) or different businesses
- **Two conversation rows** — no shared message history.

**Example C — Same website visitor, different session**

- `external_conversation_id=web:session-A` vs `web:session-B`
- **Two conversations** even if `visitor_id` repeats.

**Example D — Same customer, Telegram + Website (do not auto-merge)**

- Telegram `tg:chat` and Website `web:session` → **separate conversations** by channel + external thread id even if email/phone later matches.
- Cross-channel merge requires explicit future workflow (out of MVP).

### 4.4 Anti-patterns

| Anti-pattern | Why forbidden |
|--------------|----------------|
| Using `channel_user_id` as `conversation_id` | Collapses thread semantics; breaks session boundaries |
| Global `external_message_id` uniqueness | Collides across flows/channels |
| Storing prompt rules in `messages.message_text` | Pollutes history; confuses model |
| Merging conversations because phone/email match | Violates E1.4 conservative identity |
| n8n storing chat history in workflow static data | Bypasses backend audit and tenant isolation |
| One open conversation per customer regardless of flow | Mixes bot behaviors (violates golden rule) |

---

## 5. Current vs target gap (as-of E2.0 design)

| Area | Current (E1.9) | Target (E2+) |
|------|----------------|--------------|
| Flow entity | Implicit via `business_id` only | Explicit `flows` table |
| Conversation lookup | `(business_id, customer_id, channel)` | `(flow_id, channel, external_conversation_id)` primary |
| `external_conversation_id` on row | Column exists; **not used in lookup** | Used for thread continuity |
| Message idempotency | `(business_id, external_message_id)` | `(flow_id, channel, external_message_id)` |
| Trace table | `prompt_runs` + Langfuse only | `message_traces` lifecycle table |
| n8n `flow_key` | Not in webhook body | Optional field → resolve `flow_id` |

---

## 6. CRM relation (future)

- `leads` remain tied to `conversation_id` (hence `flow_id` derivable).
- `crm_external_contact_id` on conversation is **write-only from CRM sync** — not used for automatic conversation merge in MVP.
- Lead creation rules unchanged; flow appears in observability metadata for owner notifications.

---

## 7. Spec references

- [`database-schema.md`](../database/database-schema.md) — update when E2.1 migrations approved
- [`entities.md`](../database/entities.md) — add Flow entity
- [`channel-source-attribution.md`](channel-source-attribution.md) — `external_conversation_id` formats
- [`observability-metadata.md`](observability-metadata.md) — add `flow_id`, `flow_key` to envelope
