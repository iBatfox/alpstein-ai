# Alpstein Task Planner — Reference

Read only sections relevant to the planning goal.

## Source of truth

| Document | Use when planning |
|----------|-------------------|
| [AGENTS.md](../../../AGENTS.md) | Global rules, layer boundaries |
| [specs/mvp/mvp-scope.md](../../../specs/mvp/mvp-scope.md) | In vs out of MVP; success criteria |
| [specs/project/vision.md](../../../specs/project/vision.md) | Product intent (not extra features) |
| [specs/project/business-goals.md](../../../specs/project/business-goals.md) | Prioritization context |
| [specs/architecture/system-architecture.md](../../../specs/architecture/system-architecture.md) | System boundaries |
| [specs/architecture/backend-architecture.md](../../../specs/architecture/backend-architecture.md) | Backend structure and services |
| [specs/architecture/n8n-architecture.md](../../../specs/architecture/n8n-architecture.md) | n8n-only work |
| [specs/architecture/ai-configuration-architecture.md](../../../specs/architecture/ai-configuration-architecture.md) | AI service ordering |
| [specs/database/database-architecture.md](../../../specs/database/database-architecture.md) | DB access rules |
| [specs/database/database-schema.md](../../../specs/database/database-schema.md) | Tables, columns, enums |
| [specs/database/entities.md](../../../specs/database/entities.md) | Entity lifecycle |
| [specs/flows/incoming-message-flow.md](../../../specs/flows/incoming-message-flow.md) | Message pipeline steps |
| [specs/flows/lead-creation-flow.md](../../../specs/flows/lead-creation-flow.md) | Lead tasks |
| [specs/flows/notification-flow.md](../../../specs/flows/notification-flow.md) | Owner notification tasks |
| [specs/api/api-endpoints.md](../../../specs/api/api-endpoints.md) | REST task breakdown |
| [specs/api/webhooks.md](../../../specs/api/webhooks.md) | Normalized payloads, n8n contract |

## MVP critical path (default P0 slice)

Decompose in this order when the goal is "get MVP working":

```text
1. Tenant/business resolution + core entities (DB + models)
2. Normalized webhook ingest (schema + validation + idempotency handling)
3. Conversation + message persistence
4. AI config load → knowledge → prompt build → gateway → AI message persist
5. Lead create/update + response flags
6. n8n: normalize inbound → call backend → reply + notify owner
```

Each bullet is multiple **small** tasks, not one epic.

## MVP backend services (task boundaries)

Split work per service, not per "backend milestone":

```text
Webhook Processing Service
Conversation Service
Lead Service
AI Configuration Service
Prompt Builder Service
Knowledge Retrieval Service
AI Gateway Service
Notification Service (response flags; n8n sends actual notify)
```

## MVP API endpoints (contract tasks)

```text
POST /api/v1/webhook/message
GET  /api/v1/health
POST /api/v1/tenants
POST /api/v1/businesses
GET  /api/v1/leads
GET  /api/v1/conversations/{id}
```

Canonical paths: [specs/api/api-endpoints.md](../../../specs/api/api-endpoints.md).

## MVP database entities

```text
tenants, businesses, customers, conversations, messages, leads
tenant_business_profiles, tenant_ai_profiles, tenant_knowledge_sources, tenant_channel_settings
prompt_templates, prompt_runs
```

## Layer ownership (dependency hints)

| Layer | Plan tasks for | Never plan as |
|-------|----------------|---------------|
| PostgreSQL | Migrations, models, tenant-filtered queries | n8n writes, AI writes |
| Backend services | Business logic, orchestration | Raw channel payloads |
| API routes | HTTP, Pydantic, delegate | Business logic in routes |
| AI stack | Gateway, prompt builder, config | DB writes, messaging |
| n8n | Webhooks, normalize, send reply/notify | Business rules, prompts, DB |

## Out of scope — do not create implementation tasks

Unless user explicitly confirms approval outside MVP:

```text
Dashboard, billing, vector DB/RAG, job queues, microservices
n8n → PostgreSQL writes, AI direct DB access
Direct WhatsApp/Telegram/Instagram SDK in backend (normalization is n8n)
Self-service onboarding UI, automatic prompt builder UI
Advanced CRM sync, enterprise RBAC
```

## Example decomposition

**Goal:** "Implement incoming WhatsApp messages end-to-end"

| ID | Task | P | Depends |
|----|------|---|---------|
| T1 | Migration: tables required by incoming-message flow (only missing) | P0 | — |
| T2 | Models + repository with `tenant_id` filter for conversation/message | P0 | T1 |
| T3 | Pydantic schema for normalized webhook body per webhooks.md | P0 | — |
| T4 | Webhook route: validate + delegate to message service (no AI yet) | P0 | T2, T3 |
| T5 | Message service: persist inbound; stub response shape | P0 | T4 |
| T6 | Message service: load AI config → retrieve knowledge → build prompt → gateway call per incoming-message-flow.md | P0 | T5 |
| T7 | Lead service step + `lead_created` in response | P0 | T6 |
| T8 | pytest: fixture normalized payload → 200 + spec fields | P1 | T7 |
| T9 | n8n workflow: normalize test payload → POST backend → branch reply | P0 | T7 |

**Not one task:** "Implement WhatsApp flow."

## Related skills

| Skill | When to suggest |
|-------|-----------------|
| alpstein-backend-engineer | Python services, routes, orchestration |
| alpstein-database-architect | Schema design questions |
| alpstein-migration-engineer | Alembic migrations |
| alpstein-api-designer | Contract design before coding |
| alpstein-n8n-integration-engineer | Workflows, normalization |
| alpstein-ai-integration-engineer | AI Gateway, prompts, config |
| alpstein-reviewer | After a task is implemented |

## Planning constraints

- Prefer thin vertical slices over broad infrastructure phases
- Avoid speculative scalability tasks
- Do not plan Redis, queues, microservices, or plugin systems unless explicitly required by specs
- Prefer one working flow before optimization