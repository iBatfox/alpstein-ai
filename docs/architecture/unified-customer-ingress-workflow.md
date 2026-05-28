# Unified customer ingress workflow (E1.7 — design)

**Status:** design-only (no runtime changes)  
**Date:** 2026-05-28  
**Baseline:** `recovery-runtime-stable-2026-05-28` tag; Telegram reference channel (E0)  
**Canonical contracts:** [`normalized-channel-contract.md`](normalized-channel-contract.md), [`specs/api/webhooks.md`](../../specs/api/webhooks.md) §7

---

## 1. Problem statement

Today, customer ingress is implemented as **two separate n8n workflows**:

| Workflow | Trigger | Add Business Context | POST body includes `operator_business_context` |
|----------|---------|----------------------|---------------------------------------------|
| `alpstein-incoming-message-telegram` | Telegram Trigger | **Yes** | **Yes** |
| `alpstein-incoming-message-website-chat` | Website Chat Webhook | **No** | **No** |

Both paths call the same backend endpoint (`POST /api/v1/webhook/message`) and share owner-notification logic, but **normalization output and POST payload are not aligned**. That creates drift risk: Website Chat may run without the same operator context as Telegram, and future channel additions would duplicate pipeline nodes.

**Principle:** Different ingress triggers are allowed; **one shared business pipeline** after channel normalization.

---

## 2. Design goals

| Goal | Detail |
|------|--------|
| Single canonical workflow name | `alpstein-customer-ingress` (new; not deployed in E1.7) |
| Separate channel entry points | Telegram Trigger + Website Chat Webhook (paths unchanged in this design phase) |
| Shared pipeline | Add Business Context → POST Backend → shared reply shaping → channel-specific delivery |
| Telegram remains reference | Behavior and regression baseline for cutover |
| No AI in n8n | All AI/orchestration stays in backend |
| No backend endpoint change | Unless explicitly approved in a later task |

---

## 3. Target topology

```text
┌─────────────────────────┐     ┌──────────────────────────┐
│  Telegram Trigger       │     │  Website Chat Webhook      │
│  (alpsteinai_0001bot)     │     │  /webhook/.../incoming     │
└───────────┬─────────────┘     └────────────┬─────────────┘
            │                                   │
            │                          IF ALPSTEIN_WEBSITE_CHAT_ENABLED == "true"
            │                                   ├── false → Respond 503 WEBSITE_CHAT_DISABLED
            ▼                                   ▼
   Normalize Telegram Incoming          Normalize Website Chat Incoming
            │                                   │
            └───────────────┬───────────────────┘
                            ▼
                 Merge to canonical normalized ingress item
                 (see §4 schema)
                            ▼
                 Add Business Context
                 (operator_business_context)
                            ▼
                      POST Backend
                            ▼
                 Shape Canonical Customer Reply
                            ▼
              Route by channel (IF/Switch)
                   ├─ telegram → Telegram Send Message
                   └─ website_chat → Respond Website Reply
                            ▼
         IF notify_owner (from POST Backend)
                            ▼
              Shape Owner Notification
                            ▼
                 Telegram Owner Notify (AlpsteinAIbot)
```

**Out of scope for this workflow:** test webhook (`alpstein-incoming-message-test`) remains a separate workflow.

---

## 4. Canonical normalized ingress schema (pre–Add Business Context)

All channel normalizers must output a **single object shape** consumed by `Add Business Context` and mapped to `POST /api/v1/webhook/message`.

### 4.1 Required fields (all channels)

| Field | Type | Notes |
|-------|------|--------|
| `business_id` | string | Resolved per channel rules (see §5) |
| `channel` | string | `telegram` \| `website_chat` (MVP transport enum) |
| `customer.external_customer_id` | string | Telegram: `message.from.id`; Website: `visitor_id` |
| `customer.name` | string \| null | Telegram: first+last name; Website: `name` |
| `customer.phone` | string \| null | Website: optional `phone` |
| `customer.email` | string \| null | Website: optional `email` |
| `message.text` | string | Required non-empty for MVP ingress |
| `message.external_message_id` | string | Telegram: `tg:{chat_id}:{message_id}`; Website: `web:{session_id}:{message_id}` |
| `message.timestamp` | string (ISO-8601) | Channel-provided or generated at normalize time |
| `message.raw_payload` | object | Sanitized provider snapshot only; not primary AI input |

### 4.2 Optional fields (channel-specific, not all sent to backend)

| Field | Telegram | Website Chat |
|-------|----------|--------------|
| `correlation_id` | Recommend add (UUID) | **Present today** |
| `source` | Omit or minimal | **Present** (`web_widget_v1`, locale, etc.) |
| `attribution` | Omit | **Present** (UTM, page_url, referrer, …) |
| `message.client` | Omit | **Present** (user_agent, ip_address_hash) |

### 4.3 Channel delivery artifacts (not in POST body)

| Field | Purpose |
|-------|---------|
| `telegram_chat_id` | Telegram Send Message `chatId` |
| `website_chat_context` | Respond Website Reply envelope (`visitor_id`, `session_id`, `message_id`) |

### 4.4 POST Backend transport envelope (shared)

After `Add Business Context`, the HTTP node body must include (aligned with current Telegram workflow + webhooks.md):

```json
{
  "business_id": "...",
  "channel": "telegram|website_chat",
  "customer": { "phone", "name", "email", "external_customer_id" },
  "message": {
    "text": "...",
    "external_message_id": "...",
    "timestamp": "...",
    "raw_payload": { }
  },
  "operator_business_context": "..."
}
```

Optional extensions (design decision for unified v1):

```json
{
  "correlation_id": "uuid",
  "source": { },
  "attribution": { }
}
```

**Website-only today:** `correlation_id`, `X-Correlation-Id`, `X-N8n-Execution-Id` on POST — recommend **standardizing correlation headers on both branches** in implementation.

---

## 5. Business ID resolution

| Channel | Resolution order |
|---------|------------------|
| Telegram | `ALPSTEIN_TELEGRAM_BUSINESS_ID` env → default `alpstein_ai_demo_001` |
| Website Chat | `body.business_id` → `ALPSTEIN_WEBSITE_CHAT_BUSINESS_ID` env → **required** (throws if missing) |

**Design recommendation:** introduce optional single env `ALPSTEIN_CUSTOMER_INGRESS_BUSINESS_ID` as override for both branches in the unified workflow (implementation task), while keeping channel-specific env vars for backward compatibility during migration.

---

## 6. Add Business Context (shared)

**Single Set node** after merge, before POST Backend.

- **Input:** canonical normalized item from either normalizer.
- **Output:** same item + `operator_business_context` string (current Alpstein AI demo text used on Telegram path).
- **Rule:** Website Chat path **must not** skip this node in the unified design.

Current text (from Telegram workflow export):

```text
Alpstein AI demo business.
We help businesses with AI assistants, CRM integrations, workflow automation, Telegram AI assistants, and customer communication systems.
Reply in the customer's language (German, English, Russian, and other supported languages).
Tone: calm, clear, concise, helpful.
Do not ask for the customer's name unless they clearly need identification or want to book.
```

---

## 7. POST Backend (shared)

| Aspect | Unified design |
|--------|----------------|
| URL | `={{ $env.BACKEND_BASE_URL }}/api/v1/webhook/message` |
| Auth | `X-Alpstein-Webhook-Token` |
| Timeout | 30000 ms |
| onError | `continueErrorOutput` → channel-specific error formatters |
| Success fan-out | Shape reply + IF notify_owner (parallel from POST Backend) |

**Owner notification:** identical guard to both workflows today:

- `notify_owner === true`
- `notification` object present
- `message.is_duplicate !== true`

**Owner notify implementation:** unify to one **Shape Owner Notification** node; allow channel-specific prefix in copy (`[Alpstein]` vs `[Alpstein][Website Chat]`) while reading customer context from the merged normalized item (Telegram: message/lead/Conversation; Website: message + attribution fields).

---

## 8. Channel-specific reply routing

| Channel | Delivery node | Success response | Error response |
|---------|----------------|------------------|----------------|
| `telegram` | Telegram Send Message | `reply_to_customer` + `telegram_chat_id` | Format Telegram Backend Error → same Send |
| `website_chat` | Respond Website Reply | Widget JSON envelope (`success`, `correlation_id`, `session_id`, `visitor_id`, `message.text`) | HTTP 502 + safe error body |

**Shape Canonical Customer Reply** (shared Code node):

- Input: `POST Backend` JSON.
- Output branch A (telegram): `{ reply_to_customer, telegram_chat_id }` from `$('Normalize Telegram Incoming')` or stored reference on merged item.
- Output branch B (website_chat): widget envelope from `$('Normalize Website Chat Incoming').website_chat_context`.

Implementation note: use **IF/Switch on `$json.channel`** after POST Backend success branch, not separate workflow files per channel.

---

## 9. Website Chat kill switch (Website branch only)

Keep existing semantics from E1.6.6:

- **Placement:** immediately after Website Chat Webhook, **before** `Normalize Website Chat Incoming`.
- **Condition:** `$env.ALPSTEIN_WEBSITE_CHAT_ENABLED` equals exact string `"true"`.
- **False branch:** `Respond Website Chat Disabled` → HTTP **503**, body:

```json
{
  "success": false,
  "error": {
    "code": "WEBSITE_CHAT_DISABLED",
    "message": "Website chat is temporarily disabled."
  }
}
```

- **No POST Backend** on disabled path.
- Telegram branch is unaffected by this flag (Telegram ingress controlled by workflow activation + separate ops policy).

---

## 10. Error handling

| Failure | Telegram path | Website path | Unified approach |
|---------|----------------|--------------|------------------|
| Normalize validation throw | Format Telegram Backend Error → Send | N/A (before normalize if enabled) | Channel-specific error nodes after normalize |
| POST transport/HTTP error | Format Telegram Backend Error → Send | Format Website Backend Error → Respond 502 | Shared error Code templates per channel |
| POST `success: false` | Format Telegram Backend Error → Send | Shape error from backend envelope | Shared backend-failure handler |

---

## 11. Observability

| Item | Telegram (today) | Website (today) | Unified target |
|------|------------------|-----------------|------------------|
| `X-Alpstein-Webhook-Token` | Yes | Yes | Yes |
| `X-Correlation-Id` | No | Yes (from body/header) | Both channels |
| `X-N8n-Execution-Id` | No | Yes | Both channels |
| Execution logging | n8n execution id | n8n execution id | Unchanged |

---

## 12. Current workflow drift risks (summary)

| Risk | Severity | Mitigation in unified design |
|------|----------|------------------------------|
| Missing `operator_business_context` on Website path | **High** | Mandatory shared Add Business Context |
| Different POST payloads | **High** | Single POST body template |
| Website has source/attribution/client; Telegram does not | Medium | Optional fields on canonical schema; map in POST when product requires |
| Owner notify copy differs | Low | Single Shape Owner Notification with channel-aware labels |
| Two workflow IDs / webhook registrations | Medium | Single workflow; migrate webhooks on cutover |
| Telegram active toggle unreliable (E1.6.6 lesson) | Medium | Website kill switch explicit; do not rely on `active=false` alone |
| Test workflow separate | Low | Keep test workflow out of unified ingress |

---

## 13. Proposed node inventory (unified workflow)

| Node | Type | Role |
|------|------|------|
| Telegram Trigger | telegramTrigger | Ingress |
| Website Chat Webhook | webhook | Ingress |
| IF Website Chat Enabled | if | Kill switch (website only) |
| Respond Website Chat Disabled | respondToWebhook | Kill switch response |
| Normalize Telegram Incoming | code | Channel normalize |
| Normalize Website Chat Incoming | code | Channel normalize |
| Merge Normalized Ingress | code or merge | Single item for downstream (implementation choice) |
| Add Business Context | set | Shared operator context |
| POST Backend | httpRequest | Shared backend call |
| IF POST Success | if | Branch success/error |
| Shape Canonical Customer Reply | code | Map backend → channel delivery input |
| Route Reply by Channel | if/switch | telegram vs website Chat |
| Telegram Send Message | telegram | Outbound |
| Respond Website Reply | respondToWebhook | Outbound |
| Format Telegram Backend Error | code | Telegram transport errors |
| Format Website Backend Error | code | Website transport errors |
| IF Notify Owner | if | Owner branch guard |
| Shape Owner Notification | code | Owner message text |
| Telegram Owner Notify | telegram | Owner delivery |

**Sticky note:** document that `active: false` remains in repo export; production enablement uses env kill switch + ops runbook, not workflow active toggle alone.

---

## 14. Migration strategy (no runtime in E1.7)

Phases:

| Phase | Action | Production impact |
|-------|--------|---------------------|
| **M0 — Design freeze** | This document + runbook approved | None |
| **M1 — Build unified workflow** | Import `alpstein-customer-ingress` JSON; **inactive** in n8n | None |
| **M2 — Parity test** | Test channel against current workflows (test webhook + synthetic inject) | None if inactive |
| **M3 — Shadow mode** | Optional: run unified inactive alongside current; compare execution payloads | None |
| **M4 — Cutover** | Activate unified; point Telegram webhook to unified workflow registration; keep Website kill switch env | Requires maintenance window |
| **M5 — Archive** | Deactivate + archive `alpstein-incoming-message-telegram` and `alpstein-incoming-message-website-chat` after successful soak | Old workflows inactive only |

**Do not** deactivate current production workflows until M4 approval.

---

## 15. Rollback plan

| Scenario | Action |
|----------|--------|
| Unified workflow misbehaves after cutover | Deactivate `alpstein-customer-ingress`; reactivate previous Telegram + Website workflows; restore webhook registrations from registry |
| Wrong operator context after cutover | Hotfix `operator_business_context` in Set node (no channel change) |
| Website kill switch stuck off | Set `ALPSTEIN_WEBSITE_CHAT_ENABLED=true` and restart n8n |
| POST payload regression | Revert unified workflow export to last known good versionId in git |

**Rollback does not require** backend or DB migration.

---

## 16. Open questions

| # | Question | Recommendation |
|---|----------|----------------|
| 1 | Single `ALPSTEIN_CUSTOMER_INGRESS_BUSINESS_ID` vs per-channel env vars? | Add unified override env in implementation; keep channel env during migration |
| 2 | Add `correlation_id` on Telegram branch? | **Yes** — parity with Website and backend correlation handling |
| 3 | Include `source` / `attribution` in MVP POST for Telegram? | Optional in v1; add when product needs channel attribution in backend |
| 4 | Merge node vs two parallel wires into Add Business Context? | Prefer explicit **Merge** Code node for clarity and testing |
| 5 | Keep test workflow separate forever? | **Yes** for MVP; unified ingress covers production channels only |
| 6 | Owner notify: read merged normalize vs channel-specific node reference? | Merged item with `channel` field; notification text builder branches on `channel` |
| 7 | WhatsApp/Instagram in unified file as disabled stubs? | No — keep out of unified workflow until enum + adapter tasks exist |

---

## 17. Related documents

| Document | Purpose |
|----------|---------|
| [`channel-mapping-telegram-website.md`](channel-mapping-telegram-website.md) | Field-level mapping reference |
| [`n8n-workflow-telegram-customer-ingress.md`](../ops/n8n-workflow-telegram-customer-ingress.md) | Current Telegram ops |
| [`n8n-workflow-website-chat-mvp.md`](../ops/n8n-workflow-website-chat-mvp.md) | Current Website Chat ops |
| [`n8n-runtime-export-parity.md`](../ops/n8n-runtime-export-parity.md) | Export governance |
| [`tasks/done/T-e1.7-unified-customer-ingress-workflow-design.md`](../../tasks/done/T-e1.7-unified-customer-ingress-workflow-design.md) | Task record |

---

## 18. Out of scope (E1.7)

- Implementing unified workflow JSON in n8n
- Changing webhook paths (`/webhook/.../incoming`)
- Backend code or schema changes
- Removing Telegram or Website Chat workflows from production
- WhatsApp / Instagram / CRM ingress
- Merging test webhook into unified ingress
