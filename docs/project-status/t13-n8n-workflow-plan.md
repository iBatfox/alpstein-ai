**Doc status:** archived  
**Tier:** project-status/historical (pending move)  
**Note:** T13.1–T13.5 complete; T13.6–T13.7 deferred

# T13 — n8n workflow plan (design only)

**Status:** accepted — workflow implementation in progress (T13.1–T13.3 done); **T13.0 deployment plan** added for project-local n8n  
**Date:** 2026-05-24  
**Depends on:** T10 webhook + auth, T11 AI path, T12 lead/notification backend slice (complete)

**Deployment (T13.0):** [`docs/ops/n8n-deployment-plan.md`](../ops/n8n-deployment-plan.md) — separate `alpstein_n8n` container; **do not** touch `integrationhubspot_n8n`.

**Goal:** Plan n8n workflows that complete the MVP loop: external/test message → normalized backend call → customer reply → owner notification when flagged.

**MVP success (when implemented):** Test webhook hits n8n → backend returns `200` + contract fields → customer receives `reply_to_customer` → owner receives Telegram alert when `notify_owner=true`; duplicate retries do not double-notify; no business logic in n8n.

**Task breakdown:** [`tasks/done/t13-n8n-workflow-slice.md`](../../tasks/done/t13-n8n-workflow-slice.md)  
**Ops checklist (T13.1):** [`docs/ops/n8n-env-credential-checklist.md`](../ops/n8n-env-credential-checklist.md)  
**Workflow 1 skeleton (T13.2):** [`docs/ops/n8n-workflow1-test-webhook.md`](../ops/n8n-workflow1-test-webhook.md) · [`n8n/workflows/t13_workflow1_test_webhook_skeleton.json`](../../n8n/workflows/t13_workflow1_test_webhook_skeleton.json)  
**n8n deployment plan (T13.0):** [`docs/ops/n8n-deployment-plan.md`](../ops/n8n-deployment-plan.md)

---

## Spec alignment

| Item | Verdict |
|------|---------|
| In MVP | **Yes** — `specs/mvp/mvp-scope.md` §4.1, §4.9, §4.10 |
| Primary specs | `n8n-architecture.md`, `webhooks.md`, `api-endpoints.md`, `incoming-message-flow.md`, `notification-flow.md`, `lead-creation-flow.md` |
| Out of scope (T13) | WhatsApp Cloud production workflow (future step only), CRM/spreadsheet routing, n8n→PostgreSQL, async queues, workflow JSON in repo until review gate, production deployment changes |

---

## 1. n8n ownership boundaries

### What n8n does

| Responsibility | MVP workflow |
|----------------|--------------|
| Receive external / test webhooks | Workflow 1 trigger |
| Validate provider signatures where supported (Meta verify token, etc.) | Provider-specific nodes — **WhatsApp deferred** |
| Normalize provider payload → backend contract | Code / Set node in Workflow 1 |
| Call `POST /api/v1/webhook/message` with API token | HTTP Request node |
| Parse `success` / `data` / `error` envelope | IF / Switch nodes |
| Send customer reply via channel API | Test: respond to webhook; WhatsApp: Cloud API send (**future**) |
| Branch on `notify_owner` | Workflow 2 branch (same workflow or sub-workflow) |
| Format and deliver owner notification (Telegram MVP) | Workflow 2 |
| Retry failed HTTP / notification delivery | n8n retry settings — **same normalized body**, preserve `external_message_id` |
| Log executions (redact secrets / PII) | n8n execution log discipline |

### What n8n must NOT do

- Create, update, or deduplicate leads  
- Decide `notify_owner` (only read `data.notify_owner` and `data.notification`)  
- Run AI, prompts, or lead qualification heuristics  
- Write to PostgreSQL  
- Store authoritative conversation state  
- Override backend duplicate handling  
- Recompute urgency or handoff from raw message text for business decisions (may use `notification_type` / `reason` **for copy only**)  
- Expose or log `N8N_BACKEND_API_TOKEN`, provider secrets, or system prompts  

---

## 2. Required backend contract

### Endpoint

```http
POST {BACKEND_BASE_URL}/api/v1/webhook/message
Content-Type: application/json
X-Alpstein-Webhook-Token: <N8N_BACKEND_API_TOKEN>
```

**Canonical auth (implemented T10-F1):** header `X-Alpstein-Webhook-Token` — **not** Bearer auth. Value must match backend env `N8N_BACKEND_API_TOKEN`.

`GET /api/v1/health` — unauthenticated; use for connectivity checks only.

### Normalized request JSON

Must match `NormalizedWebhookMessageRequest` / `specs/api/webhooks.md`:

```json
{
  "business_id": "demo_barbershop_001",
  "channel": "test",
  "customer": {
    "phone": "+41790000000",
    "name": "Test User",
    "email": null,
    "external_customer_id": "test_customer_001"
  },
  "message": {
    "text": "Hello, can I book tomorrow?",
    "external_message_id": "test-msg-001",
    "timestamp": "2026-05-21T10:00:00Z",
    "raw_payload": {}
  }
}
```

| Field | Rule |
|-------|------|
| `business_id` | Business `external_id` string — map in n8n from config / webhook context |
| `channel` | One of: `whatsapp`, `telegram`, `instagram`, `website_chat`, **`test`** |
| `customer.phone` or `customer.external_customer_id` | At least one required |
| `message.text` | Non-empty |
| `message.external_message_id` | **Required for idempotency** when provider supplies an ID; preserve across retries |
| `message.raw_payload` | Optional; omit secrets; do not log in production |

### Success response (`HTTP 200`)

Envelope from `app/schemas/webhook_response.py`:

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "...",
    "lead_created": true,
    "lead_updated": false,
    "notify_owner": true,
    "conversation": { "id": "...", "status": "open" },
    "message": { "id": "...", "is_duplicate": false },
    "lead": { "id": "...", "status": "new", "priority": "normal" },
    "notification": {
      "should_notify_owner": true,
      "notification_type": "new_lead",
      "reason": "lead_created",
      "priority": "normal"
    }
  }
}
```

| Field | n8n usage |
|-------|-----------|
| `data.reply_to_customer` | Always send to customer channel |
| `data.lead_created` / `data.lead_updated` | Logging / future CRM branch only — **no business decisions** |
| `data.notify_owner` | **Gate** Workflow 2 |
| `data.lead` | Present when lead touched; optional CRM copy |
| `data.notification` | Present when `notify_owner=true`; drives message template |
| `data.message.is_duplicate` | Log; expect `notify_owner=false` |

**Omitted when null:** `lead`, `notification` (backend uses `exclude_none`).

### Notification types & reasons (backend-owned — n8n reads only)

| `notification_type` | Typical `reason` | MVP owner message intent |
|---------------------|------------------|--------------------------|
| `new_lead` | `lead_created` | New customer contact |
| `urgent_lead` | `urgent_detected` | Urgent request |
| `human_handoff` | `handoff_requested` | Customer wants human |
| `ai_failure` | `ai_failed` | AI/fallback path — owner awareness |

When `notify_owner=false`, `notification` is omitted. Do not infer notify from `lead_created` alone if backend says false.

### Error response handling

All errors: `{ "success": false, "error": { "code": "...", "message": "..." } }`

| HTTP | `error.code` | n8n action |
|------|--------------|------------|
| 401 | `UNAUTHORIZED` | Fail workflow; fix token; **do not retry** with wrong creds |
| 403 | `FORBIDDEN` | Backend auth not configured; alert ops |
| 404 | `BUSINESS_NOT_FOUND` | Fail; check `business_id` mapping |
| 400 | `VALIDATION_ERROR` | Fail; log body shape; fix normalization |
| 422 | FastAPI validation | Fail; fix normalized payload |
| 5xx | `INTERNAL_ERROR` / gateway | Retry with **identical body** + same `external_message_id` |

**On error:** do not send customer reply from stale data; optional ops alert (no owner “new lead” template).

---

## 3. Workflow 1 — Incoming message (test path)

**Name:** `alpstein-incoming-message-test`  
**Export (T13.2):** [`n8n/workflows/t13_workflow1_test_webhook_skeleton.json`](../../n8n/workflows/t13_workflow1_test_webhook_skeleton.json)  
**Ops guide:** [`docs/ops/n8n-workflow1-test-webhook.md`](../ops/n8n-workflow1-test-webhook.md)

### T13.2 status (skeleton)

**T13.2 done:** Webhook → Normalize.

### T13.3 status (backend HTTP)

**T13.3 implementation done:** Normalize → **POST Backend** (auth via `$env.N8N_BACKEND_API_TOKEN`) → Respond (backend envelope passthrough) or safe error branch on non-2xx. **No HTTP retries** in T13.3 (retries → **T13.6**).

**Gate 1 (runtime):** run manual verification in [`docs/ops/n8n-workflow1-test-webhook.md`](../ops/n8n-workflow1-test-webhook.md) § Manual verification (T13.3) before **T13.4** — n8n webhook → HTTP 200 + `success: true` + `data.reply_to_customer`. Implementation complete ≠ Gate 1 signed off until that checklist is executed in your environment.

**Next:** **T13.4** — reshape test-channel response to `reply_to_customer` (after Gate 1).

### Full target steps (T13.2–T13.6)

```text
1. Webhook trigger (test URL)
2. Normalize payload (Code / Set) → canonical JSON
3. HTTP POST → backend /api/v1/webhook/message
4. IF success === true
     4a. Extract data.reply_to_customer
     4b. Respond to Webhook OR Send Test Reply node (MVP test channel)
     4c. IF data.notify_owner === true → Workflow 2 branch
   ELSE
     error branch (§2)
```

### Test webhook input (manual / curl)

Minimal body n8n receives; normalization node adds `business_id`, `channel: "test"`, wraps `customer` / `message`:

```json
{
  "phone": "+41790000000",
  "text": "Hello, first message",
  "external_message_id": "manual-test-001"
}
```

Normalization must output full contract including stable `external_message_id`.

### Customer reply (MVP test channel)

| Channel | MVP behavior |
|---------|----------------|
| `test` | **Respond to Webhook** node with `{ "reply": "<reply_to_customer>" }` or plain text |
| `whatsapp` | **Deferred** — see §5 |

---

## 4. Workflow 2 — Owner notification branch

**Trigger:** Same execution as Workflow 1 after successful backend response — **not** a separate business decision.

```text
IF data.notify_owner === true AND data.notification exists
  → Select template by data.notification.notification_type
  → Format using data.notification.reason, data.notification.priority
  → Include data.lead (if present), customer phone from **request** context (not re-fetched)
  → Send Telegram message (MVP)
ELSE
  → No-op (log "notify skipped")
```

### Template mapping (copy only — not business logic)

| `notification_type` | Suggested Telegram headline |
|---------------------|----------------------------|
| `new_lead` | New lead |
| `urgent_lead` | Urgent lead |
| `human_handoff` | Human handoff requested |
| `ai_failure` | AI automation issue |

Include: `reason`, `priority`, lead `id`/`status`, message preview from **inbound** text (from workflow context), channel, business_id.

**Do not:** re-evaluate keywords, change lead status, or send notify when `notify_owner=false`.

### Duplicate path

When `data.message.is_duplicate === true`: expect `notify_owner=false` — branch must **not** fire.

---

## 5. WhatsApp Cloud API — future step (not scheduled in T13)

**Do not implement** unless explicitly approved as a follow-on slice.

| Step | Responsibility |
|------|----------------|
| Meta webhook verification | n8n Webhook node + verify token env |
| Raw → normalized mapping | `wamid` → `message.external_message_id`; sender → `customer.phone` / `external_customer_id` |
| Preserve `external_message_id` | Required for backend dedup |
| Reply send | WhatsApp Cloud API HTTP node with `reply_to_customer` body |
| Credentials | Meta `WHATSAPP_*` in n8n credentials only |

Proposed future task IDs: **T13-W1–T13-W4** (see task slice file) — **out of T13 P0**.

---

## 6. Environment variables & credentials

**Never commit secrets.** Document names in `.env.example` / ops runbook only.

**n8n deployment (T13.0):** [`docs/ops/n8n-deployment-plan.md`](../ops/n8n-deployment-plan.md) — compose at `n8n/docker-compose.yml`, env at `/opt/alpstein-ai/n8n/.env`, host port **15679**, container `alpstein_n8n`.

**Canonical checklist (T13.1):** [`docs/ops/n8n-env-credential-checklist.md`](../ops/n8n-env-credential-checklist.md) — backend URL, auth header, token alignment, n8n credential placement, test payload fields, security rules, and manual verification steps.

### n8n / integration

| Variable | Used by | Purpose |
|----------|---------|---------|
| `BACKEND_BASE_URL` | n8n HTTP node | e.g. `https://alpstein-ai.ch` — **no trailing slash** |
| `N8N_BACKEND_API_TOKEN` | n8n HTTP header + backend | Shared secret; `X-Alpstein-Webhook-Token` |

### Backend (already configured — n8n consumes)

| Variable | Purpose |
|----------|---------|
| `N8N_BACKEND_API_TOKEN` | Validates n8n calls |
| `ALPSTEIN_AI_DATABASE_URL` | Backend only — **not** n8n |
| `OPENAI_API_KEY` | Backend only — **not** n8n |

### Notification placeholders (n8n credentials)

| Name | Purpose |
|------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot API token (n8n Telegram credential) |
| `TELEGRAM_OWNER_CHAT_ID` | Destination chat / channel ID |
| `NOTIFICATION_*` | Optional future email/SMTP placeholders |

### Provider placeholders (future WhatsApp)

| Name | Purpose |
|------|---------|
| `WHATSAPP_PHONE_NUMBER_ID` | Cloud API send |
| `WHATSAPP_ACCESS_TOKEN` | Meta token (credential) |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | Meta webhook challenge |

---

## 7. Idempotency

| Rule | Owner |
|------|-------|
| Pass `message.external_message_id` whenever provider gives an ID | n8n normalization |
| Retries use **identical** normalized body (same `external_message_id`) | n8n HTTP retry (**T13.6** — not in T13.3) |
| Backend dedupes message, lead, notify flags | backend |
| n8n does not skip backend call based on local memory | n8n |
| On duplicate response (`is_duplicate=true`), still send `reply_to_customer` to customer | n8n |
| On duplicate, **do not** send owner notification | n8n (`notify_owner=false`) |
| Notification dedup | Backend primary; n8n must not notify when flag false |

---

## 8. T13 task breakdown (summary)

Full table: [`tasks/done/t13-n8n-workflow-slice.md`](../../tasks/done/t13-n8n-workflow-slice.md)

| ID | Task | Skill |
|----|------|-------|
| T13.1 | Env/credential checklist + ops doc (no secrets in repo) | n8n-integration-engineer |
| T13.2 | Workflow 1: test webhook + normalize node | n8n-integration-engineer |
| T13.3 | HTTP Request → backend + auth header | n8n-integration-engineer |
| T13.4 | Success path: customer reply (Respond to Webhook) | n8n-integration-engineer |
| T13.5 | Workflow 2: `notify_owner` branch + Telegram send | n8n-integration-engineer |
| T13.6 | Error branches (401/404/400/5xx) + HTTP retry on 5xx | n8n-integration-engineer |
| T13.7 | Manual E2E checklist execution | n8n-integration-engineer + reviewer |
| T13.8 | Export sanitized workflow notes / optional JSON placeholders | n8n-integration-engineer |
| T13.9 | Update project-status docs | n8n-integration-engineer |

**Review gates:** **Gate 1** — manual run after T13.3 impl (n8n → backend 200 + `success: true`); **Gate 2** — after T13.5 (notify on new-lead fixture); **Gate 3** — after T13.7 (**alpstein-reviewer**).

---

## Risks

| Risk | Mitigation |
|------|------------|
| Wrong auth header (Bearer vs `X-Alpstein-Webhook-Token`) | Document T10-F1 contract in T13.3 |
| n8n infers notify from `lead_created` | Gate only on `notify_owner` |
| Retry changes `external_message_id` | **T13.6** retry policy + T13.7 checklist |
| Secrets in exported workflow JSON | T13.8 strip credentials |
| WhatsApp scope creep | Explicit deferral §5 |

---

## Recommended first implementation subtask

**T13.1** — Done. [`docs/ops/n8n-env-credential-checklist.md`](../ops/n8n-env-credential-checklist.md)  
**T13.2** — Done. [`docs/ops/n8n-workflow1-test-webhook.md`](../ops/n8n-workflow1-test-webhook.md)  
**T13.3** — Implementation done (backend HTTP + auth). **Gate 1:** run manual verification in ops doc before T13.4.  
**Next:** **T13.4** — Customer reply path (`reply_to_customer` in Respond to Webhook).
