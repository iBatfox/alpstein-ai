**Doc status:** runtime-derived  
**Tier:** ops/production (pending move) — **duplicate cluster** with `n8n-workflow-telegram-customer-ingress.md`

**Doc status:** runtime-derived  
**Tier:** ops/production (pending move) — **duplicate cluster** with `n8n-workflow-telegram-customer-ingress.md`

# Telegram customer ingress — normalize mapping (T14.1)

**Status:** T14.1 complete — mapping approved for implementation planning  
**Date:** 2026-05-25  
**Depends on:** T13.5 Gate 2, [`telegram-channel-credentials.md`](../architecture/telegram-channel-credentials.md)  
**Implementation plan:** [`tasks/todo/t14-telegram-customer-ingress.md`](../../tasks/todo/t14-telegram-customer-ingress.md)

**Scope:** How inbound Telegram Bot API `Update` objects map into the existing `POST /api/v1/webhook/message` contract. **No** bot tokens, secrets, or workflow JSON in this doc.

---

## Goal

n8n **Normalize Telegram Incoming** must produce the same JSON shape as test webhook normalization, with `channel: "telegram"`, stable dedup keys, and customer identity = Telegram **user** (not bot, not chat id).

Backend contract reference: `backend/app/schemas/webhook.py`, [`specs/api/webhooks.md`](../../specs/api/webhooks.md) §7.

---

## Business and tenant resolution (n8n assumptions)

| Field | Source | Notes |
|-------|--------|-------|
| `business_id` | Workflow config / env `ALPSTEIN_TELEGRAM_BUSINESS_ID` or static per deployed workflow | Must match `businesses.external_id` (e.g. `demo_barbershop_001`) |
| Tenant | **Not in payload** | Backend resolves `business_id` → `Business` → `tenant_id` |
| Bot identity | **Not in payload** | One n8n **Telegram Trigger** credential per client bot; maps 1:1 to one `business_id` at workflow design time |
| `channel` | Constant `"telegram"` | Required enum value |

**Rule:** Do not put bot token, bot user id, or webhook secret in normalized JSON or `raw_payload`.

---

## Mapping table — Telegram Update → normalized contract

Telegram paths use Bot API [Update](https://core.telegram.org/bots/api#update) object. n8n Telegram Trigger typically exposes the update as JSON on the item.

**Primary path (MVP):** `update.message` — private chat text from a human user.

| Telegram source | Normalized target | Rule |
|-----------------|-------------------|------|
| _(workflow config)_ | `business_id` | External business id string; not from Telegram payload |
| _(constant)_ | `channel` | `"telegram"` |
| `message.from.id` | `customer.external_customer_id` | **Required primary id** — string, e.g. `"123456789"`; identifies Telegram **user**, never the bot |
| `message.from.username` | _(optional)_ `raw_payload` only | Do not use as sole customer id (can change); may inform display name |
| `message.from.first_name` + `message.from.last_name` | `customer.name` | Trimmed join; omit if empty |
| `message.from` | `customer.phone` | **`null`** — Telegram private chats do not provide E.164 phone for backend MVP |
| `message.from` | `customer.email` | **`null`** |
| `message.chat.id` | **n8n internal** `telegram_chat_id` (Send node) | **Not** in current backend schema — see [T14.1 findings](#t14.1-contract-findings) |
| `message.chat.id` | `external_conversation_id` (logical) | Value = string(chat id); MVP: persist intent via `raw_payload` only unless contract extended |
| `message.text` | `message.text` | Required for backend; see [missing text](#edge-case-missing-text) |
| `message.message_id` + `message.chat.id` | `message.external_message_id` | Composite — see [idempotency](#idempotency-rules) |
| `message.date` | `message.timestamp` | Unix seconds → ISO 8601 UTC (e.g. `2026-05-21T10:00:00Z`) |
| `update_id` | `raw_payload.update_id` | Debug/trace only; **do not** use as sole `external_message_id` |
| Full update (redacted) | `message.raw_payload` | Optional; strip secrets; truncate size in logs |

### Fields explicitly not mapped to backend

| Telegram field | MVP handling |
|----------------|--------------|
| `update_id` alone as `external_message_id` | **Reject** — not stable across logical duplicates of same `message_id` in all retry scenarios |
| Bot `message.from.id` when `from.is_bot === true` | **Drop** update (no customer message) |
| `message.chat.id` as `external_customer_id` | **Forbidden** — would merge/group wrong customers |

---

## Recommended `external_message_id` format

**Canonical (MVP):**

```text
tg:{chat_id}:{message_id}
```

Example: `tg:123456789:42` where `123456789` is `message.chat.id` and `42` is `message.message_id`.

| Property | Rationale |
|----------|-----------|
| Stable across n8n/backend retries | Same Telegram message → same pair |
| Unique per chat | `message_id` is unique within a chat |
| Global across chats | `chat_id` prefix avoids cross-chat collision |
| Idempotent with backend T5/T6 | Matches partial unique index on `external_message_id` per business |

**Alternative (not MVP):** `str(update_id)` only when operating in strict webhook-replay mode — weaker alignment with “same message” semantics on Telegram retries that reuse `message_id`.

---

## Recommended `external_customer_id`

```text
customer.external_customer_id = String(message.from.id)
```

| Rule | Detail |
|------|--------|
| Identify | Telegram **user** who sent the message |
| Never | `message.chat.id`, bot id, or `update_id` |
| Lookup | Backend `CustomerService` scoped by `business_id` + `source_channel` + `external_customer_id` |
| Phone | Omit; backend accepts `external_customer_id` without phone |

---

## Recommended `external_conversation_id` (logical)

```text
external_conversation_id = String(message.chat.id)
```

| Chat type | `chat.id` typical shape | Conversation semantics |
|-----------|-------------------------|-------------------------|
| Private | Positive integer | 1:1 customer ↔ business bot thread |
| Group / supergroup | Negative integer | Shared thread; multiple `from.id` in same conversation |

**MVP backend today:** `NormalizedWebhookMessageRequest` has **no** top-level conversation external id. `ConversationService` reuses open conversation by `(tenant, business, customer, channel)` only.

| Layer | MVP behavior |
|-------|----------------|
| Backend POST body | Do **not** send `external_conversation_id` until contract extended |
| n8n workflow | Keep `telegram_chat_id` on item for **Telegram Send Message** (T14.4) |
| `raw_payload` (optional) | May include `"chat_id": "<id>"` for debugging — backend does not branch on it |

---

## Example Telegram Update (sanitized)

Structure only — values are illustrative.

```json
{
  "update_id": 900001,
  "message": {
    "message_id": 42,
    "date": 1716283200,
    "chat": {
      "id": 123456789,
      "type": "private",
      "first_name": "John"
    },
    "from": {
      "id": 987654321,
      "is_bot": false,
      "first_name": "John",
      "last_name": "Doe",
      "username": "johndoe"
    },
    "text": "Hello, can I book tomorrow?"
  }
}
```

---

## Example normalized payload (POST /api/v1/webhook/message)

Matches existing backend validator — **no contract change required for MVP text path.**

```json
{
  "business_id": "demo_barbershop_001",
  "channel": "telegram",
  "customer": {
    "phone": null,
    "name": "John Doe",
    "email": null,
    "external_customer_id": "987654321"
  },
  "message": {
    "text": "Hello, can I book tomorrow?",
    "external_message_id": "tg:123456789:42",
    "timestamp": "2026-05-21T10:00:00Z",
    "raw_payload": {
      "provider": "telegram",
      "update_id": 900001,
      "chat_id": "123456789",
      "chat_type": "private",
      "message_id": 42
    }
  }
}
```

**n8n item fields to retain after normalize (not sent to backend):**

```text
telegram_chat_id = "123456789"   // for Telegram Send Message (T14.4)
```

---

## Idempotency rules

| Scenario | Behavior |
|----------|----------|
| Same `message_id` + `chat_id` resent (n8n retry, Telegram redelivery) | Same `external_message_id` → backend `is_duplicate: true`; no new lead; no owner notify (T12/T13) |
| n8n HTTP retry to backend | **Identical** normalized body including same `external_message_id` |
| New Telegram message in same private chat | New `message_id` → new `external_message_id` → normal processing |
| Edited message | See [edge case](#edge-case-edited-messages) — same `message_id` risk |

---

## Edge cases

### Edge case: missing text

| Update type | MVP |
|-------------|-----|
| No `message.text` (photo, sticker, voice, document, location) | **Drop** at normalize; log `skip_reason: non_text_message` |
| `message.caption` only | **Optional P1:** map caption to `message.text` if product approves — not in T14.2 unless spec updated |

Backend requires `message.text` with `min_length=1`.

### Edge case: edited messages

| Field | MVP |
|-------|-----|
| `edited_message` instead of `message` | **Drop** or **separate slice (defer)** — same `message_id` as original would collide on dedup if treated as new inbound |

**Recommendation:** Defer `edited_message` to post-MVP; document in runbook.

### Edge case: group chats

| Topic | MVP |
|-------|-----|
| `chat.type` = `group` / `supergroup` | **Defer** unless product enables group bots — risk of wrong customer/conversation semantics |
| Bot must be added to group | Filter: only `private` in T14.2 normalize Code node |
| @mention required in groups | Out of scope for first slice |

### Edge case: forwarded messages

| Topic | MVP |
|-------|-----|
| `forward_origin` / `is_forwarded` | **Process only `message.text`** as customer intent (if text present) — do not treat forward source as `external_customer_id` |
| Forward from channel | Same rule — `from.id` is still the user who forwarded in private; in groups defer |

### Edge case: bot commands

| Topic | MVP |
|-------|-----|
| `/start`, `/help`, etc. | `message.text` is non-empty → **process** like normal text (backend/AI handles content) |
| `entities` bot_command | No special n8n branch — no business logic in n8n |

### Edge case: duplicate updates

| Topic | Behavior |
|-------|----------|
| Telegram redelivers same `update_id` | Normalize identically → backend dedup |
| Two updates, same `message_id` | Should not happen in one chat; if seen, second is duplicate |

### Edge case: channel posts

| Topic | MVP |
|-------|-----|
| `channel_post` / `edited_channel_post` | **Drop** — not customer DM to business bot |

---

## T14.1 contract findings (no implementation in T14.1)

| ID | Finding | Severity | MVP workaround |
|----|---------|----------|----------------|
| **F1** | `external_conversation_id` not in `NormalizedWebhookMessageRequest` | Low for private 1:1 chats | Reuse conversation by customer + channel; store `chat_id` in n8n for Send only |
| **F2** | `customer.phone` null for Telegram | None | Use `external_customer_id` only — already supported |
| **F3** | Non-text messages cannot reach backend | Expected | Drop at normalize |
| **F4** | `edited_message` not defined | Low | Defer |
| **F5** | Group/supergroup semantics | Medium if enabled later | Private chats only in T14.2–T14.4 |

**No backend code change required** to start T14.2 for **private text messages** with mapping above.

**Spec gap (approval if persisting chat thread in DB):** optional field e.g. `conversation.external_id` on webhook body — track in api-designer before backend change.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Using `chat.id` as `external_customer_id` | Mapping table forbids; code review T14.3 |
| Using `update_id` as `external_message_id` | Use composite `tg:{chat_id}:{message_id}` |
| Losing `chat_id` after HTTP node | Set/explicitly pass `telegram_chat_id` on item before POST Backend |
| Group chat enabled accidentally | Filter `chat.type === "private"` in normalize |
| Caption-only media looks like “no reply” | Document drop; optional caption mapping later |
| `raw_payload` leaks secrets | Strip tokens; minimal snapshot only |
| Username change breaks wrong id | Use numeric `from.id` only for `external_customer_id` |

---

## Open questions (product / ops)

| # | Question | Default if unanswered |
|---|----------|------------------------|
| Q1 | Private chats only for T14.2? | **Yes** — enforce in normalize |
| Q2 | Map `caption` to `message.text`? | **No** for T14.2 |
| Q3 | Process `edited_message`? | **No** — defer |
| Q4 | Add webhook field for `external_conversation_id`? | **Defer** — n8n holds `telegram_chat_id` |
| Q5 | One workflow per business vs multi-tenant routing? | **One bot credential per business** (MVP) |

---

## T14.2 — Customer credential verification (runtime)

**Status:** **passed** (2026-05-25)  
**Task:** [`tasks/done/T14.2-telegram-customer-credential-verification.md`](../../tasks/done/T14.2-telegram-customer-credential-verification.md)

### n8n credentials (names only)

| n8n credential name | Role | Telegram `getMe` username |
|---------------------|------|---------------------------|
| `AlpsteinAIbot` | Owner notify (T13.5) | `@AlpsteinAibot` |
| `alpsteinai_0001bot` | Customer ingress (T14) | `@alpsteinai_0001bot` |

`TELEGRAM_CHAT_ID` in `n8n/.env` remains **owner-only** — not used for customer Send.

### `getMe` results (no tokens)

| Credential | getMe | `bot_id` (masked) | `username` |
|------------|-------|-------------------|------------|
| `AlpsteinAIbot` | ok | `***4264` | `@AlpsteinAibot` |
| `alpsteinai_0001bot` | ok | `***8404` | `@alpsteinai_0001bot` |

### Separation

```text
SEPARATION_VERIFIED=yes
```

Re-check: `/opt/alpstein-ai/n8n/scripts/t14-verify-telegram-bots.sh`

### T14.2 gate

| Criterion | Status |
|-----------|--------|
| Owner + customer credentials in n8n | Yes |
| `getMe` ok for both | Yes |
| Different `bot_id` / `username` | Yes |
| No Trigger workflow added | Yes |

**Verdict: T14.2 COMPLETE**

**T14.3 COMPLETE (accepted skeleton)** — export + ops doc; POST Backend success fans out in **parallel** to customer Send and owner IF (not Send → IF). See [`n8n-workflow-telegram-customer-ingress.md`](n8n-workflow-telegram-customer-ingress.md).

**T14.4 COMPLETE (pipeline)** — exec **55–57**; see [`T14.4-telegram-live-dm-verification.md`](../../tasks/done/T14.4-telegram-live-dm-verification.md). **T14.5 is next.**

---

## Related docs

- [`telegram-channel-credentials.md`](../architecture/telegram-channel-credentials.md)
- [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md) — T13.5 baseline topology
- [`specs/api/webhooks.md`](../../specs/api/webhooks.md) §7.1 Telegram appendix
