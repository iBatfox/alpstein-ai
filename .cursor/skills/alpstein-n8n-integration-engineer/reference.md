# Alpstein n8n Integration Engineer — Spec Reference

Read only the sections relevant to the current task.

## Source of truth (read first)

| Document | Use when |
|----------|----------|
| [AGENTS.md](../../../AGENTS.md) | Any integration work |
| [specs/mvp/mvp-scope.md](../../../specs/mvp/mvp-scope.md) | Channels and features in vs out of MVP |
| [specs/architecture/n8n-architecture.md](../../../specs/architecture/n8n-architecture.md) | n8n role, MVP workflows, must-not rules |
| [specs/architecture/deployment.md](../../../specs/architecture/deployment.md) | Docker services, domains, n8n deployment |
| [specs/api/webhooks.md](../../../specs/api/webhooks.md) | Normalized payload, response, security, idempotency |
| [specs/api/api-endpoints.md](../../../specs/api/api-endpoints.md) | Backend URL path (`/api/v1/webhook/message`) |
| [specs/flows/incoming-message-flow.md](../../../specs/flows/incoming-message-flow.md) | End-to-end message pipeline |
| [specs/flows/notification-flow.md](../../../specs/flows/notification-flow.md) | `notify_owner`, notification types |
| [specs/flows/lead-creation-flow.md](../../../specs/flows/lead-creation-flow.md) | Lead fields in backend response for owner messages |

Contract details and error codes: use [alpstein-api-designer/reference.md](../alpstein-api-designer/reference.md) — do not duplicate; link when changing payloads.

## MVP integration deliverables

```text
Workflow 1: Incoming message (webhook → normalize → backend → customer reply)
Workflow 2: Owner notification (notify_owner branch)
Channels: WhatsApp Cloud API, test webhook
Backend call: POST /api/v1/webhook/message + API token
```

## Normalized request (canonical)

```json
{
  "business_id": "demo_barbershop_001",
  "channel": "whatsapp",
  "customer": {
    "phone": "+41790000000",
    "name": "John",
    "email": null,
    "external_customer_id": "wa_001"
  },
  "message": {
    "text": "Hello, can I book an appointment tomorrow?",
    "external_message_id": "wamid.example",
    "timestamp": "2026-05-21T10:00:00Z",
    "raw_payload": {}
  }
}
```

## Backend success response (parse in n8n)

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "...",
    "lead_created": true,
    "lead": { "id": "...", "status": "new" },
    "conversation": { "id": "...", "status": "open" },
    "notify_owner": true
  }
}
```

## Provider → normalized field mapping (WhatsApp Cloud API)

Use official Meta docs for exact webhook shape. Typical mapping:

| Normalized field | WhatsApp source (conceptual) |
|------------------|------------------------------|
| `business_id` | Config / webhook path / static per workflow |
| `channel` | `"whatsapp"` |
| `customer.phone` | Sender phone from contacts/messages payload |
| `customer.name` | Profile name if present |
| `customer.external_customer_id` | WhatsApp user/wa id |
| `message.text` | Text body of inbound message |
| `message.external_message_id` | Message id (`wamid...`) |
| `message.timestamp` | Provider timestamp |
| `message.raw_payload` | Optional provider payload snapshot for debugging. Must not expose secrets or sensitive customer data in logs. |

Verify signature / verify token per Meta requirements in the **Webhook** trigger node, not in backend.

## n8n HTTP Request → backend

- Method: `POST`
- URL: `{BACKEND_BASE_URL}/api/v1/webhook/message`
- Header: API token as documented in deployment (e.g. `Authorization: Bearer ...` or project convention — match backend implementation)
- Body: JSON normalized payload
- Timeout: avoid blocking longer than provider allows; log non-2xx responses

Retries must not create duplicate backend records.
Preserve `external_message_id` across retries.


## n8n responsibility boundaries

n8n workflows must not implement:
- lead qualification logic
- prompt logic
- AI orchestration
- database business rules
- direct PostgreSQL writes


## Environment checklist (names only)

Document required vars in `.env.example` when adding integrations; never commit values:

```text
N8N_* (admin, encryption, webhook URL)
BACKEND_BASE_URL
BACKEND_API_TOKEN (n8n → backend)
WHATSAPP_* / provider tokens (in n8n credentials)
NOTIFICATION_* (Telegram bot, SMTP, etc.)
```

## n8n workflow export hygiene

If exporting workflows to the repo:

- Strip credential IDs or replace with placeholders
- No API keys in JSON
- Document activation steps in PR description, not in committed secrets

## Integration test path

1. `channel: "test"` or provider test number → n8n webhook
2. Confirm normalized body shape in execution log (redact customer-sensitive data in screenshots or exported logs)
3. Backend returns `success: true` and `data.reply_to_customer`
4. Customer receives reply on provider or test sink
5. Force lead path → `notify_owner: true` → notification workflow fires

## Handoff triggers

| Change | Hand off to |
|--------|-------------|
| New required/optional normalized fields | alpstein-api-designer → update webhooks.md |
| New response flags for automation | alpstein-api-designer + alpstein-backend-engineer |
| New persisted fields from integration | alpstein-database-architect |
| Webhook route or service logic | alpstein-backend-engineer |

## Out of scope (reference only)

Future n8n work per specs (not MVP): CRM, Google Sheets, reminders, analytics, async queues, per-channel workflow templates.
