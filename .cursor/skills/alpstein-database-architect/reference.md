# Alpstein Database — Spec Reference

Read only the sections relevant to the current task.

## Source of truth

| Document | Use when |
|----------|----------|
| [AGENTS.md](../../../AGENTS.md) | Tenant rules, who may write to DB |
| [specs/mvp/mvp-scope.md](../../../specs/mvp/mvp-scope.md) | In vs out of MVP |
| [specs/database/database-architecture.md](../../../specs/database/database-architecture.md) | Storage modes, security, access matrix |
| [specs/database/database-schema.md](../../../specs/database/database-schema.md) | Tables, columns, enums, constraints |
| [specs/database/entities.md](../../../specs/database/entities.md) | Entity meaning, lifecycle, business rules |
| [specs/architecture/backend-architecture.md](../../../specs/architecture/backend-architecture.md) | Where models and DB layer live |
| [specs/architecture/ai-configuration-architecture.md](../../../specs/architecture/ai-configuration-architecture.md) | AI config tables, prompt_runs |
| [specs/flows/incoming-message-flow.md](../../../specs/flows/incoming-message-flow.md) | Write order for messages/conversations |
| [specs/flows/lead-creation-flow.md](../../../specs/flows/lead-creation-flow.md) | Lead fields and status transitions |

## MVP tables (required)

### Core

```text
tenants
businesses
customers
conversations
messages
leads
database_connections
```
Credentials must be encrypted at rest and never exposed in logs or API responses.

### AI configuration

```text
tenant_business_profiles
tenant_ai_profiles
tenant_knowledge_sources
tenant_channel_settings
prompt_templates
prompt_runs
```

### Future (not MVP unless spec updated)

```text
events, audit_logs, users, subscriptions, integrations
```

## Tenant isolation matrix

| Table | tenant_id | business_id |
|-------|-----------|-------------|
| tenants | — (root) | — |
| businesses | required | — |
| customers | required | required |
| conversations | required | required |
| messages | required | required |
| leads | required | required |
| database_connections | required | optional per spec |
| tenant_* / prompt_* | required | per table in schema doc |

## Common enums (verify in schema doc before coding)

**Tenant status:** `active`, `inactive`, `suspended`

**Business storage_mode:** `shared`, `dedicated`, `external`

**Conversation channel:** `whatsapp`, `telegram`, `instagram`, `website_chat`, `test`

**Conversation status:** `open`, `waiting_for_customer`, `waiting_for_owner`, `closed`, `archived`

**Message sender_type:** `customer`, `ai`, `owner`, `system`

**Lead status:** `new`, `in_progress`, `contacted`, `closed`, `lost`

## Recommended uniqueness

| Table | Constraint |
|-------|------------|
| tenants | `slug` UNIQUE |
| businesses | `external_id` UNIQUE |
| customers | Use business-scoped unique identifiers appropriate to the channel (e.g. phone, external_customer_id). |

## Index guidance

Typical composite filters for backend services:

```text
(tenant_id, business_id)
(tenant_id, business_id, customer_id)
(conversation_id, created_at)   -- message history
(business_id, status)           -- lead lists
(tenant_id, business_id, channel)
```

Add indexes when a new query path is introduced — justify against spec flows, not speculation.

## Data flow (writes)

```text
n8n → normalized payload → backend → PostgreSQL
```

Backend owns:
- customer upsert
- conversation management
- message insert
- lead create/update
- prompt_runs persistence

Message persistence must support idempotent processing using external_message_id where available.

## Security checklist

- [ ] PostgreSQL not publicly exposed
- [ ] Only backend credentials in deployment secrets
- [ ] Queries tenant-scoped
- [ ] No credentials in `database_connections` as plain text
- [ ] Backups: daily dump, off-volume storage (ops; document if designing runbooks)

## Migration naming (suggested)

Use standard Alembic revision generation.

Examples:

```bash
alembic revision -m "create_messages_table"
alembic revision -m "add_prompt_runs_table"
```

One concern per revision:
- add table
- add column
- add index

Avoid mixed refactors in one migration.
