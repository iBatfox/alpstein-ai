**Doc status:** runtime-derived  
**Tier:** architecture/runtime (pending move)  
**Canonical anchor:** [`canonical-runtime-architecture.md`](canonical-runtime-architecture.md) §8 — dual-bot model **implemented**

# Telegram channel credentials — production model (design)

**Status:** architecture / planning only (post–T13.5 Gate 2)  
**Date:** 2026-05-25  
**Scope:** Credential ownership, storage boundaries, onboarding, multi-client — **no implementation** in this document.

**Related:** [`specs/flows/notification-flow.md`](../../specs/flows/notification-flow.md) §6.1, [`docs/ops/n8n-env-credential-checklist.md`](../ops/n8n-env-credential-checklist.md), [`docs/ops/post-t13-5-stabilization.md`](../ops/post-t13-5-stabilization.md)

---

## Decision summary

| Role | Bot ownership | Token storage | n8n usage |
|------|---------------|---------------|-----------|
| **Owner notification** (T13.5) | **Alpstein-owned** ops bot | n8n encrypted credential + `TELEGRAM_CHAT_ID` env (per deployment / owner) | `Telegram Owner Notify` on `notify_owner` |
| **Customer ingress + reply** (T14+) | **Client-owned** bot per business | Client provides token at onboarding; Alpstein stores **reference only** in backend metadata; **token only** in n8n encrypted credential store | `Telegram Trigger` / `Telegram Send` via **credential reference** — never literal token in JSON |

**Hard rule:** Customer-facing Telegram bots **must not** reuse Alpstein owner-notify credentials.

---

## 1. Production credential model (target)

### Client owns the bot

- Client creates a Telegram bot via [@BotFather](https://t.me/BotFather).
- Client grants Alpstein operational use of the bot token for automation (contract/onboarding).
- Bot username and business branding remain client-visible to end customers.

### Client provides token at onboarding

1. Client submits bot token through a **secure channel** (not email, not chat logs, not workflow export).
2. Operator or future admin UI stores token in **n8n credentials** (encrypted at rest by `N8N_ENCRYPTION_KEY`).
3. Backend records **metadata only** in `tenant_channel_settings` (or future dedicated table):
   - `channel = telegram`
   - `business_id`, `tenant_id`
   - `metadata.n8n_credential_name` or `metadata.credential_ref` (opaque label, e.g. `telegram_customer_demo_barbershop`)
   - optional: `metadata.telegram_bot_username` (public, non-secret)
   - **Never** `metadata.bot_token` or raw token string

### Token must never appear in

| Forbidden surface | Why |
|-------------------|-----|
| Workflow JSON in git | Export portability + leak risk |
| Repo docs, screenshots, tickets | Operational leak |
| n8n execution logs (when avoidable) | Telegram nodes should use credentials, not inline secrets |
| Plaintext PostgreSQL columns | `database-architecture.md` — sensitive credentials not plain text |
| Backend `.env` for per-client tokens | Backend does not call Telegram in MVP architecture |
| Customer API responses | Transport isolation |

### n8n sends/receives via credential reference only

- Workflow nodes: `telegramApi` credential selected by **name** in UI (survives as credential ID in export — **strip or re-bind on import** per T13.8).
- Runtime binding happens in **n8n UI / server env**, not in repo.
- Per-business mapping: Code node reads `business_id` → looks up `credential_ref` from backend config (future) or static workflow sub-workflow parameter set at activation time (MVP interim).

### Rotation and revocation

| Event | Action |
|-------|--------|
| Client rotates token in BotFather | Update n8n credential only; update `credential_ref` label if name changes; no backend token field to migrate |
| Compromise suspected | Revoke token in BotFather; disable workflow; rotate `N8N_ENCRYPTION_KEY` only with volume recovery plan |
| Offboarding | Delete n8n credential; archive `tenant_channel_settings` row; disable Telegram trigger |

### Workflow exports

- Repo export remains **source of truth for topology** (nodes, expressions, branches).
- Export must use **placeholder** credential names or empty `credentials` blocks reviewed in T13.8.
- After import to new n8n host: operator re-binds credentials in UI before activation.

---

## 2. MVP-safe credential model (interim, before full onboarding UI)

Acceptable for **first live Telegram customer ingress** slice (T14):

| Item | MVP approach |
|------|----------------|
| Customer bot token | One test client bot; token in n8n **Telegram API** credential (e.g. `Telegram customer demo`) |
| Owner bot token | Separate credential **`Telegram account`** (existing T13.5) |
| Backend | `channel: "telegram"` in normalized payload; `tenant_channel_settings.metadata` may document `credential_ref` string only |
| Multi-client | Manual: duplicate workflow or sub-workflow per business with different credential binding — **not** dynamic multi-tenant credential loader in n8n yet |
| Onboarding | Manual runbook: BotFather → n8n credential → verify `getMe` → bind workflow → test message |

**Not MVP:** Self-service token upload UI, centralized secrets vault (Vault/AWS SM) sync to n8n, automatic credential provisioning API.

---

## 3. Recommended onboarding flow (Telegram customers)

```text
1. Sales / ops agrees Telegram as customer channel for business X.
2. Client creates bot (BotFather) and shares token via secure handoff.
3. Alpstein operator:
   a. Creates n8n Telegram API credential (name: telegram_customer_<business_external_id>).
   b. Sets webhook on Telegram Trigger (HTTPS n8n URL) or uses polling per n8n node choice.
   c. Ensures tenant_channel_settings row: channel=telegram, metadata.credential_ref only.
   d. Maps business external_id in Normalize node.
4. Test: client sends message to bot → n8n → backend → reply in Telegram chat.
5. Owner notify path unchanged (Alpstein bot, notify_owner branch).
6. Document credential_ref in internal ops sheet (no token column).
```

---

## 4. Owner notify vs customer ingress (separation)

| Dimension | Owner notification (T13.5) | Customer Telegram (T14) |
|-----------|----------------------------|-------------------------|
| Purpose | Alert business owner of leads/urgent/handoff/AI failure | Receive customer messages; send AI replies |
| Trigger | Backend `notify_owner` flag | Telegram Trigger (client bot updates) |
| Direction | Outbound only to owner `chat_id` | Inbound + outbound to customer chat |
| Bot | Alpstein ops / deployment bot | Client bot |
| Credential | `Telegram account` + `TELEGRAM_CHAT_ID` | Per-client `telegram_customer_*` credential |
| Backend channel | N/A (does not send Telegram) | `channel: "telegram"` in normalized webhook |
| Business logic | None in n8n (copy from `notification`) | None in n8n (normalize only) |

---

## 5. Secret-management boundaries

```text
┌─────────────────────────────────────────────────────────────┐
│ Backend (PostgreSQL)                                         │
│  • business_id, channel rules, AI config                     │
│  • credential_ref / bot_username metadata ONLY               │
│  • NO bot tokens, NO owner chat secrets                      │
└───────────────────────────┬─────────────────────────────────┘
                            │ normalized HTTP only
┌───────────────────────────▼─────────────────────────────────┐
│ n8n (encrypted credential store + env)                       │
│  • N8N_BACKEND_API_TOKEN (Alpstein ↔ backend)               │
│  • Per-client Telegram bot tokens (customer)                 │
│  • Alpstein Telegram bot token (owner notify)                │
│  • TELEGRAM_CHAT_ID (owner destination — lower sensitivity)  │
└───────────────────────────┬─────────────────────────────────┘
                            │ Telegram Bot API
┌───────────────────────────▼─────────────────────────────────┐
│ Telegram (Meta)                                              │
└─────────────────────────────────────────────────────────────┘
```

**Future (spec gap — approval needed):** Dedicated `channel_credentials` table with envelope encryption or external vault; sync **reference** to n8n via API — not in MVP implementation scope.

---

## 6. Operational risks (customer bot tokens)

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token leak via workflow export | Client account takeover | T13.8 export hygiene; no literals in JSON |
| Token in support ticket / screenshot | Same | Ops runbook; redact in exports |
| Shared credential across clients | Cross-tenant message bleed | One credential per business; naming convention |
| Reusing owner bot for customers | Wrong identity; owner DM flooded | Separate credentials (this doc) |
| n8n volume loss + wrong encryption key | All credentials lost | Backup volume; document key rotation |
| Client revokes token without notice | Silent failure | Monitoring on Telegram send errors; ops alert |
| Storing token in `tenant_channel_settings.metadata` | DB breach exposes tokens | **Forbidden** — reference only |
| Multi-tenant n8n instance | Credential sprawl | Naming: `telegram_customer_<external_id>`; access control on n8n admin |

---

## 7. Multi-client implications

| Concern | MVP | Production target |
|---------|-----|-------------------|
| Credentials per business | Manual bind | Same; optional credential-per-tenant policy |
| Webhook URL | One n8n HTTPS host; path or workflow per business | Subdomain or path routing; `business_id` in normalize |
| `external_message_id` | Telegram `update_id` + `message_id` composite | Document in T14 normalize spec |
| Owner notify | Single `TELEGRAM_CHAT_ID` per deployment | Per-business owner chat in future `tenant_notification_settings` |
| Backend | Already multi-tenant via `business_id` | Unchanged |

---

## 8. Next implementation slice (reference only)

See [`tasks/todo/t14-telegram-customer-ingress.md`](../../tasks/todo/t14-telegram-customer-ingress.md).

**Topology (do not implement here):**

```text
Telegram Trigger (client bot credential)
  → Normalize Telegram Incoming
  → POST Backend
       ├─ (success) → Shape Telegram Customer Reply → Telegram Send Message (same client bot credential)
       ├─ (success) → IF notify_owner → Shape Owner Notification → Telegram Owner Notify (Alpstein credential)
       └─ (error)   → safe customer error text → Telegram Send Message
```

Owner notify is parallel from POST Backend success — not after customer Send.

**Prerequisite:** Complete [`post-t13-5-stabilization.md`](../ops/post-t13-5-stabilization.md) before T14.1.
