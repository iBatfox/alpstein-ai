# Alpstein Backend — Spec Reference

Read only the sections relevant to the current task.

## Source of truth (read first)

| Document | Use when |
|----------|----------|
| [AGENTS.md](../../../AGENTS.md) | Any backend work |
| [specs/mvp/mvp-scope.md](../../../specs/mvp/mvp-scope.md) | Scoping / in vs out of MVP |
| [specs/architecture/system-architecture.md](../../../specs/architecture/system-architecture.md) | System boundaries |
| [specs/architecture/backend-architecture.md](../../../specs/architecture/backend-architecture.md) | Layers, structure, endpoints |
| [specs/architecture/ai-configuration-architecture.md](../../../specs/architecture/ai-configuration-architecture.md) | AI services, prompts, config layers |
| [specs/architecture/n8n-architecture.md](../../../specs/architecture/n8n-architecture.md) | n8n responsibilities |
| [specs/database/database-architecture.md](../../../specs/database/database-architecture.md) | DB access rules |
| [specs/database/database-schema.md](../../../specs/database/database-schema.md) | Tables and columns |
| [specs/database/entities.md](../../../specs/database/entities.md) | Entity meaning and lifecycle |
| [specs/api/api-endpoints.md](../../../specs/api/api-endpoints.md) | REST contracts |
| [specs/api/webhooks.md](../../../specs/api/webhooks.md) | Webhook payloads |
| [specs/flows/incoming-message-flow.md](../../../specs/flows/incoming-message-flow.md) | Main message pipeline |
| [specs/flows/lead-creation-flow.md](../../../specs/flows/lead-creation-flow.md) | Lead detection and status |
| [specs/flows/notification-flow.md](../../../specs/flows/notification-flow.md) | Owner notification flags |

## MVP backend services (required)

```text
Webhook Processing Service
Conversation Service
Lead Service
AI Configuration Service
Prompt Builder Service
Knowledge Retrieval Service
AI Gateway Service
Notification Service
```


Backend services orchestrate the full AI execution flow:

```text
config → knowledge → prompt builder → gateway → PromptRun → response validation
```

## MVP API endpoints (required)

```text
POST /api/v1/webhook/message
GET  /api/v1/health
POST /api/v1/tenants
POST /api/v1/businesses
GET  /api/v1/leads
GET  /api/v1/conversations/{id}
```

Older docs may reference `/webhook/message` or `/health` without the `/api/v1` prefix — follow `specs/api/api-endpoints.md` for the canonical paths.

## MVP database entities (required)

```text
tenants, businesses, customers, conversations, messages, leads
tenant_business_profiles, tenant_ai_profiles, tenant_knowledge_sources, tenant_channel_settings
prompt_templates, prompt_runs. 
```
All client-owned entities must enforce tenant_id filtering in repositories and services.

## Lead statuses

```text
new | in_progress | contacted | closed | lost
```

## Webhook response shape (n8n contract)

Success responses should support n8n automation, e.g.:

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "...",
    "lead_created": true,
    "lead": {
      "id": "...",
      "service_requested": "...",
      "status": "new"
    },
    "notify_owner": true
  }
}
```

Webhook processing must support idempotency using `external_message_id` where available.

## Security checklist

- HTTPS for public endpoints
- API token between n8n and backend
- PostgreSQL not publicly exposed
- Tenant isolation on all client data queries
- No secrets in logs or commits

## Development priority (backend-architecture)

1. Project structure → health → DB → models → webhook → message storage → mock AI → leads → real AI → n8n integration test

Do not skip ahead to future features before the MVP message flow works.
