**Doc status:** runtime-derived  
**Tier:** ops/production (pending move)  
**Canonical anchor:** [`../architecture/website-chat-architecture.md`](../architecture/website-chat-architecture.md)

# Website Chat MVP workflow (E1.6)

**Workflow file:** [`n8n/workflows/e1_6_workflow_website_chat_mvp_skeleton.json`](../../n8n/workflows/e1_6_workflow_website_chat_mvp_skeleton.json)  
**Workflow name:** `alpstein-incoming-message-website-chat`  
**Widget files:** [`website-widget/`](../../website-widget/)  
**Contract source:** [`specs/architecture/normalized-channel-contract.md`](../../specs/architecture/normalized-channel-contract.md)

---

## Goal

Run Website Chat as another ingress adapter using the existing backend path:

Website widget -> n8n webhook normalize -> `POST /api/v1/webhook/message` -> backend orchestration -> n8n shaped response -> widget.

No new backend endpoint, no separate AI system, no attachment support.

---

## Runtime chain

```text
Website Chat Webhook (POST /webhook/.../alpstein/website-chat/incoming)
  -> Normalize Website Chat Incoming (Code)
  -> POST Backend (HTTP + token + correlation headers)
       |- success -> Shape Website Customer Reply -> Respond Website Reply (200)
       |- error   -> Format Website Backend Error -> Respond Website Error (502)
       \- IF Notify Owner -> Shape Owner Notification -> Telegram Owner Notify
```

---

## Required environment variables (n8n)

| Variable | Required | Purpose |
|----------|----------|---------|
| `BACKEND_BASE_URL` | Yes | Backend base URL (compose: `http://backend:8000`) |
| `N8N_BACKEND_API_TOKEN` | Yes | Header `X-Alpstein-Webhook-Token` to backend |
| `ALPSTEIN_WEBSITE_CHAT_BUSINESS_ID` | Optional | Default `business_id` if widget omits it |
| `TELEGRAM_CHAT_ID` | Optional | Owner-notify destination (if owner branch enabled) |

Backend must have matching `N8N_BACKEND_API_TOKEN`.

---

## Startup notes (compose path)

1. Start stack:

```bash
cd /opt/alpstein-ai
docker-compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d postgres backend n8n
```

2. Confirm backend reachable from n8n:

```bash
docker exec alpstein_n8n_compose wget -qO- http://backend:8000/api/v1/health/ready
```

3. Open n8n UI: `http://127.0.0.1:15680`.
4. Import `n8n/workflows/e1_6_workflow_website_chat_mvp_skeleton.json`.
5. Configure credentials (owner notify node only) if owner branch should run.
6. Activate only after smoke checklist passes in the target environment.

---

## Webhook endpoints

| Mode | URL |
|------|-----|
| Test (editor) | `http://127.0.0.1:15680/webhook-test/alpstein/website-chat/incoming` |
| Active workflow | `http://127.0.0.1:15680/webhook/alpstein/website-chat/incoming` |

---

## Widget setup

Use script from [`website-widget/alpstein-chat-widget.js`](../../website-widget/alpstein-chat-widget.js):

```html
<script
  src="alpstein-chat-widget.js"
  data-webhook-url="http://127.0.0.1:15680/webhook/alpstein/website-chat/incoming"
  data-business-id="alpstein_ai_demo_001"
  data-title="Alpstein Assistant"
></script>
```

Local demo:

```bash
cd /opt/alpstein-ai/website-widget
python3 -m http.server 18080
```

Open `http://127.0.0.1:18080/example.html`.

---

## Normalization contract highlights

| Widget input | Backend transport |
|-------------|-------------------|
| `visitor_id` | `customer.external_customer_id` |
| `session_id` | `message.external_conversation_id = web:{session_id}` |
| `message_id` | `message.external_message_id = web:{session_id}:{message_id}` |
| `text` | `message.text` |
| `language` | `source.locale` |
| `page_url` / `referrer` / `utm_*` | `attribution.*` |
| `user_agent` | `message.client.user_agent` |

Correlation propagation:

- body `correlation_id` (normalized)
- header `X-Correlation-Id`
- header `X-N8n-Execution-Id = $execution.id`

---

## Verification procedure

### A) Direct webhook smoke (without widget)

```bash
VISITOR_ID="v-$(date +%s)"
SESSION_ID="s-$(date +%s)"
MESSAGE_ID="m-$(date +%s)"
curl -sS -X POST "http://127.0.0.1:15680/webhook/alpstein/website-chat/incoming" \
  -H "Content-Type: application/json" \
  -d "{
    \"business_id\": \"alpstein_ai_demo_001\",
    \"visitor_id\": \"$VISITOR_ID\",
    \"session_id\": \"$SESSION_ID\",
    \"message_id\": \"$MESSAGE_ID\",
    \"text\": \"Hello from website chat\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"language\": \"en\",
    \"page_url\": \"http://localhost:18080/example.html\"
  }"
```

Expected:

- HTTP 200
- `success: true`
- `message.text` present in response
- same `session_id` and `visitor_id` echoed

### B) Duplicate test

Resend the exact same payload (`message_id` unchanged).  
Expected: success path remains stable and backend duplicate behavior is preserved.

### C) Error path

Temporarily break `N8N_BACKEND_API_TOKEN` and call webhook again.  
Expected: HTTP 502 with safe error body from `Respond Website Error`.

---

## Smoke-test checklist

- [ ] Workflow imports successfully in n8n 1.95+
- [ ] `POST Backend` reaches `/api/v1/webhook/message` with token header
- [ ] `channel=website_chat` and `web:` IDs are generated correctly
- [ ] Widget receives AI text reply via same HTTP request
- [ ] Duplicate message_id does not break response path
- [ ] Correlation headers/body are forwarded
- [ ] Owner notify branch does not affect customer response timing
- [ ] Telegram ingress workflow remains unchanged and operational
- [ ] No attachment path available in widget or workflow

---

## Notes

- This workflow is exported with `"active": false` in repo.
- Runtime activation/deactivation is an operator step.
- Website Chat remains text-only in MVP.
