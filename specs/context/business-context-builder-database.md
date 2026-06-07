# Business Context Builder Database Specification

## 1. Purpose

This document defines the database storage rules for the Business Context Builder module.

Business Context Builder stores draft interview sessions, messages, and generated context results. The data must remain isolated from active Alpstein AI assistant configuration.

---

# 2. Existing PostgreSQL Usage

Business Context Builder uses the existing Alpstein AI PostgreSQL instance.

Do not create:

- a separate PostgreSQL server;
- a separate database;
- direct n8n database writes;
- AI-layer database writes.

Backend services are the only layer allowed to write Business Context Builder data.

---

# 3. Dedicated Schema

Business Context Builder must use a separate PostgreSQL schema:

```text
business_context_builder
```

Allowed MVP tables:

```text
business_context_builder.sessions
business_context_builder.messages
business_context_builder.results
```

The schema is reserved only for this module.

---

# 4. Isolation Rules

Business Context Builder data is draft-only client-owned data.

Every persisted session and result must be tenant-scoped:

```text
tenant_id
business_id
```

Queries must filter by `tenant_id`. Business-scoped queries must also filter by `business_id`.

The module must not:

- write into production assistant tables;
- modify `tenant_business_profiles`;
- modify `tenant_ai_profiles`;
- modify `tenant_knowledge_sources`;
- modify `prompt_templates`;
- modify active prompt or assistant configuration;
- automatically publish generated context data.

Production assistants must not depend on the `business_context_builder` schema.

---

# 5. Database Structure

```text
Alpstein AI PostgreSQL
    │
    ├── public / existing Alpstein AI schemas and tables
    │
    └── business_context_builder
        │
        ├── sessions
        ├── messages
        └── results
```

---

# 6. Table: business_context_builder.sessions

Purpose:

Store one interview lifecycle.

Fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | Yes | Primary key. |
| tenant_id | UUID | Yes | Tenant owner. Required for tenant isolation. |
| business_id | UUID | Yes | Business the draft context is being prepared for. |
| telegram_user_id | TEXT | No | Reserved for future Telegram Mini App identity. Not required by MVP. |
| customer_id | UUID | No | Reserved for future CRM/customer linkage. |
| status | TEXT | Yes | Interview state. |
| current_step | TEXT | No | Current interview section or placeholder step. |
| created_at | TIMESTAMP | Yes | Creation timestamp. |
| updated_at | TIMESTAMP | Yes | Last update timestamp. |
| completed_at | TIMESTAMP | No | Set when status becomes `completed`. |

Allowed `status` values:

```text
created
in_progress
completed
archived
```

Recommended constraints:

```text
PRIMARY KEY (id)
status IN ('created', 'in_progress', 'completed', 'archived')
```

Recommended indexes:

```text
(tenant_id, business_id)
(tenant_id, business_id, status)
```

---

# 7. Table: business_context_builder.messages

Purpose:

Store interview conversation history.

Fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | Yes | Primary key. |
| tenant_id | UUID | Yes | Copied from the owning session for tenant-safe querying. |
| business_id | UUID | Yes | Copied from the owning session for business-safe querying. |
| session_id | UUID | Yes | References `business_context_builder.sessions.id`. |
| role | TEXT | Yes | Message role. |
| content | TEXT | Yes | Message content. |
| created_at | TIMESTAMP | Yes | Creation timestamp. |

Allowed `role` values:

```text
assistant
user
system
```

Relationship:

```text
sessions
1
↓
many
messages
```

Foreign key:

```text
business_context_builder.messages.session_id
→ business_context_builder.sessions.id
```

Recommended constraints:

```text
PRIMARY KEY (id)
role IN ('assistant', 'user', 'system')
```

Recommended indexes:

```text
(tenant_id, business_id, session_id)
(session_id, created_at)
```

---

# 8. Table: business_context_builder.results

Purpose:

Store generated draft business context and generated prompt text.

Fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | Yes | Primary key. |
| tenant_id | UUID | Yes | Tenant owner. Required for tenant isolation. |
| business_id | UUID | Yes | Business the draft result belongs to. |
| session_id | UUID | Yes | References `business_context_builder.sessions.id`. |
| structured_context | JSONB | Yes | Draft structured business context. |
| generated_prompt | TEXT | Yes | Draft generated prompt text. |
| context_file_path | TEXT | No | Reserved for future generated context file path. |
| context_file_url | TEXT | No | Reserved for future CRM/file attachment URL. |
| created_at | TIMESTAMP | Yes | Creation timestamp. |
| updated_at | TIMESTAMP | Yes | Last update timestamp. |

Relationship:

```text
sessions
1
↓
1
results
```

Foreign key:

```text
business_context_builder.results.session_id
→ business_context_builder.sessions.id
```

Recommended constraints:

```text
PRIMARY KEY (id)
UNIQUE (session_id)
```

Recommended indexes:

```text
(tenant_id, business_id)
(tenant_id, business_id, created_at)
```

---

# 9. JSONB structured_context

`structured_context` stores the generated draft business context as JSONB.

MVP placeholder shape:

```json
{
  "company": {
    "name": null,
    "website": null,
    "industry": null,
    "country": null,
    "languages": []
  },
  "business_description": "",
  "assistant_goals": [],
  "services": [],
  "target_customers": {},
  "common_questions": [],
  "lead_qualification": {},
  "communication_style": {},
  "restrictions": [],
  "handoff_rules": []
}
```

The structure may evolve in later specs, but it must remain draft-only until an explicit publishing workflow exists.

---

# 10. generated_prompt Storage

`generated_prompt` stores draft system prompt text generated from the interview result.

Purpose:

- future review by an operator;
- future prompt editing;
- future explicit publishing workflow.

The prompt must not be automatically used by production assistants.

The generated prompt must not override platform-controlled safety rules from Alpstein AI prompt architecture.

---

# 11. Reserved Context File Fields

Future versions may generate context files:

```text
business_context.md
business_context.txt
```

Reserved fields:

```text
context_file_path
context_file_url
```

MVP rules:

- leave both fields nullable;
- do not generate files;
- do not upload files;
- do not attach files to CRM;
- do not expose file links unless a later file workflow exists.

---

# 12. Alembic Migration Rules

Future Alembic migrations for this module must:

- use one concern per revision;
- create schema `business_context_builder` if it does not exist;
- create only Business Context Builder tables;
- keep Business Context Builder tables in the dedicated schema;
- use UUID primary keys;
- include `created_at` and `updated_at` where required;
- add tenant-safe indexes for documented query paths.

Migration names should follow existing Alembic style, for example:

```bash
alembic revision -m "create_business_context_builder_tables"
```

This documentation task does not create migrations.

---

# 13. Forbidden Operations

Migrations and application code for this module must never:

- create Business Context Builder tables in production assistant schemas;
- alter production assistant tables;
- rename production assistant tables;
- migrate production assistant data into Business Context Builder;
- migrate Business Context Builder data into production assistant tables;
- write into `tenant_business_profiles`;
- write into `tenant_ai_profiles`;
- write into `tenant_knowledge_sources`;
- modify `prompt_templates`;
- create CRM, n8n, Telegram, or OpenAI side effects.

---

# 14. Related Specifications

- [business-context-builder-mvp.md](business-context-builder-mvp.md)
- [business-context-builder-flow.md](business-context-builder-flow.md)
- [business-context-builder-api.md](business-context-builder-api.md)
- [../database/database-architecture.md](../database/database-architecture.md)
- [../database/database-schema.md](../database/database-schema.md)
