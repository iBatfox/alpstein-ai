# Business Context Builder MVP

## 1. Purpose

Business Context Builder is an isolated Alpstein AI backend module for collecting business information through an interview and producing draft onboarding artifacts.

The module prepares:

- structured business context;
- generated system prompt text;
- saved interview history.

The generated data is draft-only. It must not automatically change active AI assistants, production prompts, tenant AI profiles, knowledge sources, or production business contexts.

---

# 2. MVP Goals

The first MVP must allow an internal user or future client UI to:

- create a new interview session;
- continue an existing interview session;
- send and store interview messages;
- receive placeholder assistant questions;
- complete an interview;
- generate placeholder structured business context;
- generate placeholder system prompt text;
- save the generated result.

The MVP goal is documentation and backend readiness for onboarding workflows, not live assistant publishing.

---

# 3. Scope

Included in MVP:

- backend session lifecycle contract;
- interview message persistence contract;
- placeholder interview logic;
- draft result generation contract;
- PostgreSQL persistence in a dedicated schema;
- API contract for future route implementation;
- strict isolation from production assistant data.

The MVP may be called by internal tooling or a future UI, but the backend contract remains JSON-only under `/api/v1`.

---

# 4. Out Of Scope

The MVP must not implement:

- OpenAI or other AI provider calls;
- AI Gateway integration;
- n8n workflow integration;
- CRM file upload or CRM attachment;
- Telegram Mini App frontend;
- active AI assistant creation;
- automatic publishing to production assistants;
- writes to production assistant tables;
- tenant self-service dashboard;
- payment, billing, or subscriptions.

---

# 5. Architecture Overview

Business Context Builder is part of the existing Alpstein AI backend.

```text
Internal user or future UI
    ↓
/api/v1/business-context-builder
    ↓
Business Context Builder API layer
    ↓
Business Context Builder service layer
    ↓
business_context_builder PostgreSQL schema
    ↓
Draft structured context + draft generated prompt
```

Layer ownership follows existing Alpstein AI rules:

- API routes receive HTTP requests, validate schemas, and call services.
- Backend services own business logic and database writes.
- PostgreSQL stores draft interview data.
- n8n remains transport/integration only.
- AI layer remains prompt/config/gateway only and is not used by this MVP.

---

# 6. Backend Strategy

Business Context Builder must use the existing Alpstein AI backend.

Do not create:

- a separate public backend service;
- a separate API server;
- new external ports;
- separate deployment infrastructure.

The module should be isolated inside the backend. Future implementation may use files similar to:

```text
backend/app/api/routes/business_context_builder.py
backend/app/schemas/business_context_builder.py
backend/app/services/business_context_builder_service.py
backend/app/models/business_context_builder.py
```

This document does not authorize creating those files in the current documentation task.

---

# 7. Database Strategy

Use the existing Alpstein AI PostgreSQL instance.

Do not create a separate database server.

Use a dedicated PostgreSQL schema:

```text
business_context_builder
```

Allowed MVP tables:

```text
business_context_builder.sessions
business_context_builder.messages
business_context_builder.results
```

Business Context Builder data is client-owned draft data and must include tenant isolation fields where persisted:

```text
tenant_id
business_id
```

No production assistant tables may be read from or written to as part of the MVP.

---

# 8. Isolation Rules

Business Context Builder must remain isolated from active assistant configuration.

The module must never:

- modify active AI assistants;
- update production prompts;
- update `tenant_business_profiles`;
- update `tenant_ai_profiles`;
- update `tenant_knowledge_sources`;
- write Business Context Builder data into production assistant tables;
- publish automatically;
- synchronize with CRM;
- synchronize with n8n;
- call OpenAI or any AI provider in the MVP.

Generated contexts are drafts. Publishing to production assistants requires a separate explicit workflow and separate approval.

---

# 9. Placeholder Interview Logic

The first MVP must not call OpenAI.

Placeholder logic:

- create a session;
- create the first assistant message from a static template;
- save user messages;
- return static next questions based on `current_step`;
- save assistant replies;
- mark a session as completed;
- create placeholder `structured_context`;
- create placeholder `generated_prompt`;
- save the result.

Placeholder questions may follow the interview sections defined in [business-context-builder-flow.md](business-context-builder-flow.md).

---

# 10. Future CRM File Attachment

Future versions may generate a context file such as:

```text
business_context.md
business_context.txt
```

Future versions may attach that file to a CRM customer record.

MVP limitations:

- no file generation;
- no file upload;
- no CRM API calls;
- no CRM synchronization.

The reserved result fields are documented in [business-context-builder-database.md](business-context-builder-database.md):

```text
context_file_path
context_file_url
```

---

# 11. Future n8n Export

Future versions may expose a workflow where n8n exports or routes completed draft contexts.

MVP limitations:

- no n8n workflow;
- no n8n trigger from completion;
- no direct n8n write to PostgreSQL;
- no automatic publish or CRM routing.

n8n must remain transport and integration only.

---

# 12. Future Telegram Mini App

Future versions may use a Telegram Mini App as the user interface for the interview.

MVP limitations:

- no Telegram Mini App frontend;
- no Telegram-specific backend payloads;
- no direct Telegram SDK usage in backend;
- no transport-specific business logic.

Any Telegram UI must call the same normalized backend API contract.

---

# 13. Safety Rules

- Business Context Builder data is draft-only.
- Never modify active AI assistant business contexts from this module.
- Never write Business Context Builder data into production assistant tables.
- Always use the `business_context_builder` PostgreSQL schema.
- Publishing to production assistants requires a separate explicit workflow.
- No n8n, CRM, Telegram Mini App, or OpenAI integration in the backend MVP unless a later task explicitly requests it.
- Tenant-owned rows must be scoped by `tenant_id`; business-scoped rows must also include `business_id`.

---

# 14. Related Specifications

- [business-context-builder-architecture.md](business-context-builder-architecture.md)
- [business-context-builder-database.md](business-context-builder-database.md)
- [business-context-builder-flow.md](business-context-builder-flow.md)
- [business-context-builder-api.md](business-context-builder-api.md)
- [../architecture/backend-architecture.md](../architecture/backend-architecture.md)
- [../database/database-architecture.md](../database/database-architecture.md)
- [../api/api-endpoints.md](../api/api-endpoints.md)
