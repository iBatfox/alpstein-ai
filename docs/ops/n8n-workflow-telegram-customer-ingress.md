**Doc status:** runtime-derived  
**Tier:** ops/production (pending move)  
**Canonical anchor:** [`../architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md) §7–§8

# Workflow — Telegram customer ingress (T14.3)

**Workflow file:** [`n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json`](../../n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json)  
**Workflow name:** `alpstein-incoming-message-telegram`  
**Mapping:** [`telegram-customer-ingress.md`](telegram-customer-ingress.md)  
**Credentials:** [`telegram-channel-credentials.md`](../architecture/telegram-channel-credentials.md)  
**Export parity:** [`n8n-runtime-export-parity.md`](n8n-runtime-export-parity.md) · Registry: [`n8n/workflows/runtime-registry.md`](../../n8n/workflows/runtime-registry.md)

**Status:** T14.3 + **T14-OC-3** + **Alpstein AI greeting switch** in repo export — **repo `active: false`**. Runtime id after latest import: `2lMuaSWD1XFOXLEK` (**deactivated** post E0 2026-05-28).

### E0 continuation (2026-05-28) — portable stack

| Check | Result |
|-------|--------|
| Audit | [`e0-telegram-regression-2026-05-28.md`](../audits/e0-telegram-regression-2026-05-28.md) — **PASS WITH WARNINGS** |
| Portable n8n → backend | **PASS** — `alpstein_n8n_compose` `wget` `/health/ready` **200** |
| Telegram-shaped POST from `alpstein_internal` | **PASS** — **200**, `success: true` (simulates POST Backend node) |
| Portable n8n execution IDs | **None** — Telegram Trigger not registered on `WEBHOOK_URL=http://127.0.0.1:15680/` |
| Prompt runs (portable backend) | `11b52702-addd-4cf3-9f02-e967082c21d8`, `96686c6c-2a59-4dda-a2cb-c80b6cce310e` |
| Post-test activation | `2lMuaSWD1XFOXLEK` **deactivated**; legacy `alpstein_n8n` restored on **15679** |

**Reference channel:** **Not signed off** — see [`T-e0-telegram-reference-channel-remediation.md`](../../tasks/todo/T-e0-telegram-reference-channel-remediation.md).

---

## Topology

```text
Telegram Trigger (alpsteinai_0001bot, updates: message)
    → Normalize Telegram Incoming (private text only; drops other update types)
    → Add Business Context (T14-OC-3: operator_business_context)
    → POST Backend
         ├─ (success) → Shape Telegram Customer Reply → Telegram Send Message
         ├─ (success) → IF Notify Owner ($('POST Backend'))
         │                    └─ (true) → Shape Owner Notification → Telegram Owner Notify (AlpsteinAIbot)
         └─ (error)   → Format Telegram Backend Error → Telegram Send Message
```

**Parallel fan-out:** On POST Backend **success**, customer reply and owner notify are **sibling** branches — not `Telegram Send Message → IF Notify Owner`.

**Customer path:** `telegram_chat_id` from normalize — **not** `TELEGRAM_CHAT_ID`.  
**Owner path:** T13.5 pattern; reads `$('POST Backend')` only; `AlpsteinAIbot` + `TELEGRAM_CHAT_ID`.

---

## Nodes

| Node | Purpose |
|------|---------|
| Telegram Trigger | Customer bot credential `alpsteinai_0001bot`; Trigger On = `message` |
| Normalize Telegram Incoming | `channel: telegram`, `business_id: alpstein_ai_demo_001`, dedup `tg:{chat}:{msg}` |
| Add Business Context | Set node: Alpstein AI `operator_business_context` (facts only; see OC-3 doc) |
| POST Backend | Contract fields + `operator_business_context`; excludes `telegram_chat_id` |
| Shape Telegram Customer Reply | `reply_to_customer` only for Send |
| Format Telegram Backend Error | Generic safe text on HTTP failure |
| Telegram Send Message | Same customer credential; `chatId` = `telegram_chat_id` |
| IF Notify Owner | Optional; same conditions as T13.5 |
| Telegram Owner Notify | `AlpsteinAIbot` + `TELEGRAM_CHAT_ID` |

---

## Normalize rules (MVP)

| Rule | Action |
|------|--------|
| `message.from.is_bot` | Drop |
| `chat.type !== private` | Drop |
| No `message.text` | Drop |
| `edited_message`, `channel_post`, … | Drop |
| `external_customer_id` | `String(message.from.id)` |
| `external_message_id` | `tg:{chat_id}:{message_id}` |
| `customer.phone` | `null` |

Dropped updates return no items (workflow stops quietly).

---

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `BACKEND_BASE_URL` | Yes | Backend base URL (no trailing slash) |
| `N8N_BACKEND_API_TOKEN` | Yes | `X-Alpstein-Webhook-Token` |
| `ALPSTEIN_TELEGRAM_BUSINESS_ID` | No | Default `alpstein_ai_demo_001` |
| `TELEGRAM_CHAT_ID` | Owner branch only | Not used on customer Send |

---

## Import

```bash
docker cp /opt/alpstein-ai/n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json alpstein_n8n:/tmp/t14-import.json
docker exec alpstein_n8n n8n import:workflow --input=/tmp/t14-import.json
```

Re-bind credentials in n8n UI if import shows missing creds: `alpsteinai_0001bot`, `AlpsteinAIbot`.

**Do not activate** until T14.4 controlled test. Only one Telegram Trigger per bot (Telegram API limit).

---

## T14-OC-3 — Operator business context (2026-05-25)

**Task:** [`tasks/done/T14-OC-3-add-business-context-node.md`](../../tasks/done/T14-OC-3-add-business-context-node.md)  
**Design:** [`operator-business-context-n8n.md`](../architecture/operator-business-context-n8n.md)

| Check | Result |
|-------|--------|
| Set node after normalize | Pass (`keepOnlySet: false`) |
| POST includes top-level field | Pass |
| Owner branch unchanged | Pass (exec **70** urgent; **71** duplicate skip) |
| Secret-free export | Pass |

**Executions (webhook inject):** **68** RU hours, **69** RU booking, **70** urgent+owner, **71** duplicate.

**Note (pre–Greeting Orchestration):** Cyrillic replies were sometimes English — backend greeting orchestration now addresses first-contact language (see Alpstein switch below).

---

## Alpstein AI business context + greeting smoke test (2026-05-25)

**Task:** [`tasks/done/T14-switch-alpstein-ai-greeting-n8n.md`](../../tasks/done/T14-switch-alpstein-ai-greeting-n8n.md)  
**Runtime workflow id:** `2lMuaSWD1XFOXLEK`  
**Export versionId:** `t14-alpstein-ai-greeting-v1`

| Change | Result |
|--------|--------|
| `business_id` / default | `alpstein_ai_demo_001` |
| Barbershop context removed | Pass (no haircut/beard/CHF) |
| Alpstein AI operator context | Pass (AI assistants, CRM, automation, Telegram, multilingual tone) |
| Customer bot | `alpsteinai_0001bot` (unchanged) |
| Owner notify bot | `AlpsteinAIbot` (unchanged) |

### Greeting smoke tests (webhook inject, fresh synthetic users)

| Test | Message | Exec ID | POST Backend | Reply checks | Owner notify |
|------|---------|---------|--------------|--------------|--------------|
| **A** — RU first contact | `Привет. Чем занимается Alpstein AI?` | **89** | `success: true`, `business_id=alpstein_ai_demo_001`, `operator_business_context` present | Russian; Alpstein AI assistant intro; no barbershop/CHF; no language restriction; no name ask | Executed (`notify_owner: true`) |
| **B** — RU follow-up | `Как вы можете помочь с CRM и Telegram?` | **90** | Same business/context | Russian; practical CRM/Telegram help; no full intro repeat | Skipped |
| **C** — DE first contact | `Hallo, was macht Alpstein AI?` | **91** | Same business/context | German greeting + Alpstein AI assistant intro | Executed (`notify_owner: true`) |

**Telegram Send Message:** `Bad Request: chat not found` on all three — expected for synthetic chat IDs; n8n chain through POST Backend + Shape completed successfully.

**Direct backend parity check** (same payload contract): Russian/German greeting assertions pass; Test B `repeats_full_intro=false`.

**Real DM:** Re-activate workflow → message `@alpsteinai_0001bot` from a fresh/cleared chat for live Telegram delivery confirmation.

**Post-test:** Runtime workflow deactivated (`active=false`).

---

## T14.4 — Live verification (2026-05-25)

**Runtime workflow id:** `zeE8EiOPVjhtiCz1` (latest import; credential bindings correct in DB).  
**Task record:** [`tasks/done/T14.4-telegram-live-dm-verification.md`](../../tasks/done/T14.4-telegram-live-dm-verification.md)

### Checklist

| Step | Result |
|------|--------|
| Single active Telegram Trigger for customer bot | Pass during test window |
| Activate `alpstein-incoming-message-telegram` | Pass (`zeE8EiOPVjhtiCz1`) |
| Normal message webhook test | Exec **55** — success |
| Urgent message | Exec **56** — success; owner branch ran |
| Duplicate `tg:{chat}:{msg}` | Exec **57** — `is_duplicate: true`; owner notify skipped |
| Deactivate after test | Pass (`active=false`; webhook cleared) |

### Execution summary

| Scenario | Exec ID | POST Backend | Customer Send | Owner notify |
|----------|---------|--------------|---------------|--------------|
| Normal appointment question | **55** | `success: true` | Attempted (`chat not found` — synthetic chat) | Telegram API **ok** |
| URGENT appointment | **56** | `success: true`, `notify_owner` | Attempted (synthetic chat) | Branch executed |
| Duplicate same `external_message_id` | **57** | `success: true`, `is_duplicate` | Attempted (synthetic chat) | **Skipped** |

**Synthetic webhook tests** validate the full n8n + backend + AI loop. **Real DM delivery** to a user’s phone requires a private message to `@alpsteinai_0001bot` after re-activation (public webhook: `n8n.alpstein-ai.ch`).

### Operator confirmation (optional)

```text
Hi, do you have an appointment today?
```

Send to `@alpsteinai_0001bot` → expect AI reply in the same chat. Re-activate workflow in n8n before testing.

---

## T14.3 verification (2026-05-25)

| Check | Result |
|-------|--------|
| Workflow JSON valid | Pass |
| Import into `alpstein_n8n` | Pass |
| Repo `active: false` | Pass |
| Customer credential on Trigger/Send only | Pass (export) |
| Owner credential separate | Pass (export) |
| Backend health | Pass (200) |
| Live DM E2E | **Pipeline pass (T14.4)** — real-user DM confirm after re-activate |

---

## Related

- T13 test webhook: [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md)
- T14.2 credentials: [`tasks/done/T14.2-telegram-customer-credential-verification.md`](../../tasks/done/T14.2-telegram-customer-credential-verification.md)
