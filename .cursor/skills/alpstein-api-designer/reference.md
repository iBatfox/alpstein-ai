# Alpstein API Designer — Spec Reference

Read only the sections relevant to the current task.

## Source of truth (read first)

| Document | Use when |
|----------|----------|
| [AGENTS.md](../../../AGENTS.md) | Any API or contract work |
| [specs/mvp/mvp-scope.md](../../../specs/mvp/mvp-scope.md) | Scoping / in vs out of MVP |
| [specs/api/api-endpoints.md](../../../specs/api/api-endpoints.md) | REST paths, envelopes, admin endpoints |
| [specs/api/webhooks.md](../../../specs/api/webhooks.md) | Normalized payloads, n8n flow, security |
| [specs/architecture/backend-architecture.md](../../../specs/architecture/backend-architecture.md) | API vs schema vs service layers |
| [specs/architecture/n8n-architecture.md](../../../specs/architecture/n8n-architecture.md) | What n8n must not do |
| [specs/flows/incoming-message-flow.md](../../../specs/flows/incoming-message-flow.md) | Message pipeline contract |
| [specs/flows/lead-creation-flow.md](../../../specs/flows/lead-creation-flow.md) | Lead fields in responses |
| [specs/flows/notification-flow.md](../../../specs/flows/notification-flow.md) | `notify_owner` and downstream automation |
| [specs/database/database-schema.md](../../../specs/database/database-schema.md) | Field names/types for response DTOs |

## MVP required endpoints

```text
GET  /api/v1/health
POST /api/v1/webhook/message
POST /api/v1/tenants
POST /api/v1/businesses
GET  /api/v1/businesses/{business_id}
GET  /api/v1/leads
GET  /api/v1/conversations/{conversation_id}
```

Deferred (documented in api-endpoints.md, implement after core flow):

```text
GET  /api/v1/leads/{lead_id}
PATCH /api/v1/leads/{lead_id}
GET  /api/v1/customers
GET  /api/v1/customers/{customer_id}
GET  /api/v1/tenants/{tenant_id}
```

## Error codes (use consistently)

```text
VALIDATION_ERROR
BUSINESS_NOT_FOUND
TENANT_NOT_FOUND
CUSTOMER_NOT_FOUND
CONVERSATION_NOT_FOUND
LEAD_NOT_FOUND
AI_PROVIDER_ERROR
DATABASE_ERROR
UNAUTHORIZED
FORBIDDEN
INTERNAL_ERROR
```

## Normalized webhook request (canonical)

```json
{
  "business_id": "demo_barbershop_001",
  "channel": "whatsapp",
  "customer": {
    "phone": "+41790000000",
    "name": null,
    "email": null,
    "external_customer_id": null
  },
  "message": {
    "text": "Hello, can I book an appointment tomorrow?",
    "external_message_id": "wamid.example",
    "timestamp": "2026-05-21T10:00:00Z",
    "raw_payload": {}
  }
}
```

## Webhook success `data` (canonical)

```json
{
  "reply_to_customer": "...",
  "lead_created": true,
  "lead": {
    "id": "uuid",
    "status": "new",
    "service_requested": "..."
  },
  "conversation": {
    "id": "uuid",
    "status": "open"
  },
  "notify_owner": true
}
```

## Channel and lead enums

**channel:** `whatsapp` | `telegram` | `instagram` | `website_chat` | `test`

**lead status:** `new` | `in_progress` | `contacted` | `closed` | `lost`

## List endpoint query parameters

| Resource | Typical params |
|----------|----------------|
| leads | `tenant_id`, `business_id`, `status`, `limit`, `offset` |
| customers | `tenant_id`, `business_id`, `phone`, `limit`, `offset` |

All client-owned list endpoints must enforce tenant_id filtering server-side.

## Security checklist (contracts)

- HTTPS for production webhooks and API
- API token on n8n → backend (`POST /api/v1/webhook/message`)
- Provider verification and raw payload handling stay in n8n. Backend receives normalized contracts only.
- No secrets in request/response examples committed to repo
- Do not design endpoints that expose system prompts or tenant override of platform safety rules

## Spec update checklist

When changing contracts, update in lockstep:

- [ ] `specs/api/api-endpoints.md` — path, method, auth, examples
- [ ] `specs/api/webhooks.md` — if normalization or n8n↔backend response changes
- [ ] Relevant `specs/flows/*.md` — if orchestration or flags change
- [ ] Note backend: Pydantic schemas under `backend/app/schemas/`
- [ ] Note database: columns only if persistence shape changes

## Design review checklist

- [ ] `/api/v1` prefix and JSON-only MVP bodies
- [ ] `success` / `data` / `error` envelope on all responses
- [ ] Stable `error.code` from spec list
- [ ] Tenant/business scoping documented for client-owned data
- [ ] No raw provider payloads at backend boundary
- [ ] Webhook response supports n8n reply + notification flags
- [ ] No MVP-out-of-scope auth or product APIs
- [ ] No transport/provider-specific logic leaked into API contracts
- [ ] Webhook ingestion endpoints must support idempotency using `external_message_id` where available.
