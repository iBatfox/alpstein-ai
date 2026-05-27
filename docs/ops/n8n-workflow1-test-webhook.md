**Doc status:** runtime-derived  
**Tier:** ops/production (pending move)  
**Canonical anchor:** [`../architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md) §7

# Workflow 1 — Test Webhook (T13.2–T13.5)

**Workflow file:** [`n8n/workflows/t13_workflow1_test_webhook_skeleton.json`](../../n8n/workflows/t13_workflow1_test_webhook_skeleton.json)  
**Workflow name:** `alpstein-incoming-message-test`  
**Design:** [`docs/project-status/t13-n8n-workflow-plan.md`](../project-status/t13-n8n-workflow-plan.md) §3  
**Env checklist:** [`n8n-env-credential-checklist.md`](n8n-env-credential-checklist.md)

**T13.2:** webhook → normalize.  
**T13.3:** POST backend with auth.  
**T13.4:** shape customer-facing JSON (`reply_to_customer` only).  
**T13.5:** owner Telegram branch when `notify_owner` + `notification` (reads `$('POST Backend')` only). **Gate 2 passed** (2026-05-25).

**Before T14 customer Trigger:** [`post-t13-5-stabilization.md`](post-t13-5-stabilization.md).  
**Credentials:** [`telegram-channel-credentials.md`](../architecture/telegram-channel-credentials.md) — owner bot ≠ customer bot.

---

## Active node chain (T13.5)

```text
Test Webhook (POST)
    → Normalize Test Payload (Code)
    → POST Backend (HTTP)
         ├─ (success) → Shape Customer Reply → Respond Customer Reply
         │                    └─ (after respond) → IF Notify Owner
         │                              └─ (true) → Shape Owner Notification → Telegram Owner Notify
         └─ (error)   → Format Backend Error → Respond Backend Error
```

**Note:** Owner notify runs **after** `Respond Customer Reply` so the test webhook gets a body immediately (n8n 1.95 + `respondToWebhook`). IF conditions and **Shape Owner Notification** still use `$('POST Backend')` — never **Shape Customer Reply**. Parallel fan-out from POST Backend was avoided (downstream nodes did not run).

No retries (T13.6). Repo export: `"active": false`.

---

## Required environment variables

Set on the **n8n** host/container before execution. Values are **not** in repo — names only.

| Variable | Required | Purpose |
|----------|----------|---------|
| `BACKEND_BASE_URL` | **Yes** | Base URL for backend (no trailing slash), e.g. `http://172.20.0.1:8010` |
| `N8N_BACKEND_API_TOKEN` | **Yes** | Sent as `X-Alpstein-Webhook-Token`; must match backend `.env` |
| `ALPSTEIN_TEST_BUSINESS_ID` | No | Default `business_id` when inbound payload omits it (else `demo_barbershop_001`) |
| `TELEGRAM_CHAT_ID` | **T13.5** | Owner alert destination chat ID |
| Telegram API credential | **T13.5** | n8n credential type `telegramApi` (bot token — not in workflow JSON) |

**Backend** must also have `N8N_BACKEND_API_TOKEN` set to the same value. See [`n8n-env-credential-checklist.md`](n8n-env-credential-checklist.md) §3.

---

## Import steps

1. Open n8n admin (port **5678**, basic auth per deployment).
2. **Workflows** → **Import from File** → `n8n/workflows/t13_workflow1_test_webhook_skeleton.json`.
3. Set n8n env vars: `BACKEND_BASE_URL`, `N8N_BACKEND_API_TOKEN` (and optional `ALPSTEIN_TEST_BUSINESS_ID`).
4. Confirm backend health: `GET {BACKEND_BASE_URL}/api/v1/health`.
5. **Test workflow** or activate for production webhook path (see activation note below).
6. **Do not activate** for production until T13.7 review gate (repo export keeps `"active": false`).

Re-import updates nodes; activate in UI/CLI if runtime webhook should answer on `/webhook/...`.

---

## Webhook endpoint

| Setting | Value |
|---------|--------|
| Method | `POST` |
| Path | `alpstein/test/incoming` |
| Response mode | `Using Respond to Webhook Node` |
| Channel | `test` (normalization sets `channel: "test"`) |

Test URL (editor):

```text
POST https://n8n.alpstein-ai.ch/webhook-test/alpstein/test/incoming
```

Production URL (workflow **active**):

```text
POST https://<n8n-host>/webhook/alpstein/test/incoming
```

Local bind (dev on host):

```text
POST http://127.0.0.1:15679/webhook/alpstein/test/incoming
```

---

## Sample test payload

```json
{
  "business_id": "demo_barbershop_001",
  "customer": {
    "phone": "+41790000000",
    "name": "Test Customer"
  },
  "message": {
    "text": "Hello, can I book today?",
    "external_message_id": "test-msg-001"
  }
}
```

Use a **new** `external_message_id` per happy-path test; resend the same id to verify duplicate metadata.

### curl — n8n webhook (replace host as needed)

```bash
MSG_ID="test-$(date +%s)"
curl -sS -X POST "http://127.0.0.1:15679/webhook/alpstein/test/incoming" \
  -H "Content-Type: application/json" \
  -d "{
    \"business_id\": \"demo_barbershop_001\",
    \"customer\": {\"phone\": \"+41790000000\", \"name\": \"Test Customer\"},
    \"message\": {\"text\": \"Hello, can I book today?\", \"external_message_id\": \"'$MSG_ID'\"}
  }"
```

No token in the curl — n8n adds `X-Alpstein-Webhook-Token` when calling the backend.

---

## Expected successful webhook response (HTTP 200) — T13.4

**Respond Customer Reply** returns a **shaped** body only:

```json
{
  "success": true,
  "reply_to_customer": "Hello! Sure. What service would you like to book and what time works best for you?"
}
```

When backend reports duplicate idempotency:

```json
{
  "success": true,
  "reply_to_customer": "...",
  "message": {
    "is_duplicate": true
  }
}
```

**Not exposed** to the test webhook caller: `data.lead`, `data.notification`, `data.conversation`, internal UUIDs, `notify_owner`, raw backend envelope, prompts.

Backend contract at `POST /api/v1/webhook/message` is **unchanged** — shaping happens only in n8n after **POST Backend**.

---

## Expected backend auth / HTTP failure (HTTP 502 from n8n)

When backend returns **non-2xx** (e.g. missing/wrong token → backend `401`), **POST Backend** routes to the error branch. The webhook caller receives:

**HTTP 502**

```json
{
  "success": false,
  "error": {
    "code": "N8N_BACKEND_REQUEST_FAILED",
    "message": "Backend request failed"
  }
}
```

Unchanged from T13.3 — n8n does **not** forward backend `401`/`403` bodies, URLs, tokens, or stack traces.

---

## POST Backend node (T13.3)

| Setting | Value |
|---------|--------|
| Method | `POST` |
| URL | `={{ $env.BACKEND_BASE_URL }}/api/v1/webhook/message` |
| Header | `X-Alpstein-Webhook-Token: {{ $env.N8N_BACKEND_API_TOKEN }}` |
| Body | JSON from **Normalize Test Payload** |
| Timeout | 30s |
| On error | `continueErrorOutput` → **Format Backend Error** (not `continueOnFail`) |

---

## Shape Customer Reply node (T13.4)

| Input | Source |
|-------|--------|
| `reply_to_customer` | `backend.data.reply_to_customer` |
| `message.is_duplicate` | `backend.data.message.is_duplicate` when boolean |

| Output field | Rule |
|--------------|------|
| `success` | `true` when backend `success === true` and `data` present |
| `reply_to_customer` | Required on success path |
| `message.is_duplicate` | Optional; only when backend sends boolean |

On backend logical failure (`success: false` in JSON body with HTTP 200), node returns `{ success: false, error: { code, message } }` — still via **Respond Customer Reply** (same as prior passthrough HTTP 200 for logical errors).

---

## Normalize mapping (T13.2 — unchanged)

| Normalized field | Source |
|------------------|--------|
| `business_id` | Inbound or `$env.ALPSTEIN_TEST_BUSINESS_ID` or `demo_barbershop_001` |
| `channel` | Always `"test"` |
| `customer.phone` / `customer.external_customer_id` | At least one required |
| `message.text` | Required |
| `message.external_message_id` | Preserved for idempotency |

---

## Owner notification (T13.5)

### IF Notify Owner

All expressions use **`$('POST Backend').first().json`**:

| Condition | Field |
|-----------|--------|
| Notify | `data.notify_owner === true` |
| Payload | `data.notification` not empty |
| Not duplicate | `data.message.is_duplicate === false` |

### Shape Owner Notification (copy only)

Telegram text includes: `notification_type`, `priority`, `reason`, customer name/message (from **Normalize Test Payload**), lead `status`/`priority`, conversation `status`. **Omits** UUIDs, `reply_to_customer`, raw backend envelope.

### Telegram Owner Notify

| Setting | Value |
|---------|--------|
| Operation | `sendMessage` |
| Chat ID | `={{ $env.TELEGRAM_CHAT_ID }}` |
| Text | `={{ $json.telegram_text }}` |
| Credential | n8n credential name **`Telegram account`** (`telegramApi`) — **Alpstein owner bot only**; bind in UI on import |
| On failure | `continueOnFail: true` (customer webhook already responded) |

**Not for customer ingress:** use a separate per-client credential (`telegram_customer_<business_external_id>`) per [`telegram-channel-credentials.md`](../architecture/telegram-channel-credentials.md).

### Test payloads

| Scenario | `message.text` (example) | Backend typically |
|----------|--------------------------|-------------------|
| Normal follow-up | `Do you do beard trims?` | `notify_owner: false` |
| Urgent | `URGENT: need an appointment ASAP` | `notify_owner: true`, `notification_type: urgent_lead` |
| Handoff | `Please let me speak to someone on your team.` | `notify_owner: true`, `notification_type: human_handoff` |
| Duplicate | Resend same `external_message_id` | `is_duplicate: true`, `notify_owner: false` |

---

## Intentionally not implemented

| Item | Task |
|------|------|
| Telegram **customer** Trigger + Send | **T14.3** — [`n8n-workflow-telegram-customer-ingress.md`](n8n-workflow-telegram-customer-ingress.md); live test **T14.4** |
| Detailed error branches (401 vs 404 vs 5xx) | **T13.6** |
| HTTP retries | **T13.6** |
| E2E checklist sign-off | **T13.7** |
| WhatsApp Cloud | **T13-W*** (deferred) |

---

## Security

- No secret values in workflow JSON — `$env` expressions only.
- Do not log `X-Alpstein-Webhook-Token` in n8n execution exports shared externally.
- Error branch returns generic message only.
- Customer response omits lead/notification/internal ids.
- No PostgreSQL, AI, or lead decision logic in n8n.

---

## Manual verification checklist (T13.5)

**Gate 1 / T13.4:** **Passed** (2026-05-25).  
**T13.5 runtime (2026-05-25):** **Passed** — branch topology + Telegram delivery on active workflow `2qfhWKtgbDy6YeTh`.

### Runtime evidence summary (final)

| Scenario | Exec ID | HTTP | Customer JSON | Notify branch | Telegram delivered |
|----------|---------|------|---------------|---------------|-------------------|
| A — normal follow-up | 52 | 200 | `success`, `reply_to_customer` | Skipped | — |
| B — urgent | 50 | 200 | `success`, `reply_to_customer` | Full post-Respond chain | **Yes** |
| C — duplicate | 51 | 200 | `is_duplicate: true` | IF only | **Suppressed** |

Post-Respond chain on urgent (exec **50**): `Respond Customer Reply` → `IF Notify Owner` → `Shape Owner Notification` → `Telegram Owner Notify` (started/finished; Telegram API returned `message_id`).

**Runtime setup (no secrets in repo):** `TELEGRAM_CHAT_ID` in `n8n/.env` (gitignored); n8n credential **Telegram account** (`telegramApi`); workflow node bound by credential **name**.

### Prerequisites

- [x] `BACKEND_BASE_URL` and `N8N_BACKEND_API_TOKEN` set on n8n.
- [x] Dev seed for `demo_barbershop_001`.

### Happy path — shaped response

- [x] POST with **new** `external_message_id`.
- [x] HTTP **200**.
- [x] Body: `success: true`, non-empty `reply_to_customer`.
- [x] No `data` wrapper, no `lead`, no `notification`, no conversation UUIDs in response.

### Idempotency — shaped duplicate metadata

- [x] Resend **same** `external_message_id`.
- [x] HTTP **200**, `success: true`, `reply_to_customer` present.
- [x] `message.is_duplicate: true` (optional metadata).

### Owner notify (T13.5)

- [x] `TELEGRAM_CHAT_ID` + `Telegram account` credential configured (2026-05-25 final run).
- [x] Urgent message → IF true → Shape + Telegram execute (exec **50**).
- [x] Normal follow-up → IF false → no Shape/Telegram (exec **52**).
- [x] Duplicate resend → `is_duplicate: true`, no Shape/Telegram (exec **51**).
- [x] Owner chat receives Telegram message (exec **50**, API `message_id` present).

### Auth failure (via n8n) — unchanged

- [ ] Wrong/missing `N8N_BACKEND_API_TOKEN` → HTTP **502**, `N8N_BACKEND_REQUEST_FAILED`.

### Hygiene

- [x] Workflow export contains no literal bot tokens.

---

## Review gate

**Gate 1:** **Passed** — backend reachable via n8n HTTP node.  
**T13.4:** **Passed** — customer-facing reply shape.  
**T13.5 / Gate 2:** **Passed** (2026-05-25) — owner Telegram delivery verified. **Next:** live Telegram **customer** ingress (production channel); then T13.6 when scheduled (not started).
