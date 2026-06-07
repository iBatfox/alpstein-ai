# Business Context Builder Architecture

## 1. Purpose

This document defines where Business Context Builder belongs inside Alpstein AI architecture.

The module collects interview data and generates draft business context artifacts. It must remain isolated from active production AI assistant configuration.

---

# 2. Placement Inside Existing Backend

Business Context Builder belongs inside the existing Alpstein AI Python backend.

It is not a separate product backend, microservice, or public integration server.

```text
Existing Alpstein AI backend
    │
    ├── existing API routes
    ├── existing backend services
    ├── existing AI layer
    └── Business Context Builder module
        │
        ├── API contract
        ├── service logic
        └── isolated PostgreSQL schema
```

Backend layer responsibilities remain unchanged:

- API routes validate HTTP requests and call services.
- Services own business logic and database writes.
- Database models map to PostgreSQL tables.
- AI provider calls, when introduced later, go through AI Gateway Service.

---

# 3. No Separate Public Backend Service

The MVP must not create:

- a separate backend application;
- a separate public API service;
- a separate FastAPI process;
- a separate deployment unit;
- a separate public domain;
- a new externally exposed port.

All API paths must live under the existing backend API namespace:

```text
/api/v1/business-context-builder
```

---

# 4. No New External Ports For MVP

Business Context Builder must use the existing backend runtime and existing reverse proxy/deployment surface.

MVP must not expose:

- a new backend port;
- a direct PostgreSQL port;
- a new n8n webhook endpoint for this module;
- a Telegram Mini App backend port;
- a CRM callback endpoint.

Future UI or integration clients should call the existing backend API through approved routing.

---

# 5. Isolated Backend Module

Future implementation should keep Business Context Builder isolated from production assistant modules.

Possible implementation layout:

```text
backend/app/api/routes/business_context_builder.py
backend/app/schemas/business_context_builder.py
backend/app/services/business_context_builder_service.py
backend/app/models/business_context_builder.py
```

Rules:

- keep routes thin;
- keep business logic in the service layer;
- keep persistence in the backend database layer;
- do not put prompt logic in n8n;
- do not put transport-specific Telegram logic in backend business logic;
- do not reuse production assistant tables for draft data.

This architecture document does not authorize creating implementation files in the documentation task.

---

# 6. Isolated PostgreSQL Schema

Business Context Builder uses the existing Alpstein AI PostgreSQL instance with a dedicated schema:

```text
business_context_builder
```

Allowed MVP tables:

```text
business_context_builder.sessions
business_context_builder.messages
business_context_builder.results
```

Tenant isolation still applies:

```text
tenant_id
business_id
```

Every backend query for Business Context Builder data must filter by `tenant_id`. Business-scoped queries must also filter by `business_id`.

---

# 7. No Production Assistant Table Usage

Business Context Builder must not read or write active assistant configuration tables during MVP.

Forbidden production table targets include:

```text
tenant_business_profiles
tenant_ai_profiles
tenant_knowledge_sources
tenant_channel_settings
prompt_templates
prompt_runs
```

Notes:

- `prompt_runs` are not used because MVP placeholder logic does not call AI.
- Generated prompt text in `business_context_builder.results.generated_prompt` is draft text only.
- Future publishing requires a separate controlled workflow.

---

# 8. MVP Component Flow

```text
Caller
    ↓
Existing backend API
    ↓
Business Context Builder route
    ↓
Business Context Builder service
    ↓
business_context_builder schema
    ↓
Draft result
```

MVP service behavior:

- create session;
- save assistant placeholder messages;
- save user messages;
- advance placeholder interview steps;
- complete session;
- save draft result.

No external integrations are called.

---

# 9. Future AI Interview Service

Future versions may replace placeholder interview logic with AI-driven question generation and structured extraction.

Future AI architecture must follow existing Alpstein AI AI-layer boundaries:

```text
Business Context Builder service
    ↓
Prompt Builder Service
    ↓
AI Gateway Service
    ↓
provider response
    ↓
Business Context Builder service validates output
    ↓
business_context_builder schema
```

Rules:

- AI Gateway Service is the only layer that may call OpenAI or other providers.
- Prompt Builder Service owns prompt assembly.
- Platform safety rules remain non-overridable.
- AI must not write to PostgreSQL directly.
- Backend service validates and persists AI output.

Future AI integration is not part of the MVP.

---

# 10. Future CRM Attachment

Future versions may attach generated context files to a CRM customer record.

Architecture rule:

```text
Backend explicit action
    ↓
file generation / storage
    ↓
CRM integration layer
    ↓
context_file_path / context_file_url updated
```

MVP must not:

- generate context files;
- upload files to CRM;
- call CRM APIs;
- synchronize automatically with CRM.

The fields `context_file_path` and `context_file_url` are reserved only.

---

# 11. Future n8n Export

Future versions may use n8n for export or routing after an explicit backend workflow exists.

Architecture rule:

- backend owns business logic and data validation;
- n8n handles transport, automation, and external integration;
- n8n must not write directly to PostgreSQL;
- n8n must not contain prompt logic;
- n8n must not publish draft contexts by itself.

MVP must not add n8n integration for Business Context Builder.

---

# 12. Future Telegram Mini App

Future versions may provide a Telegram Mini App frontend for the interview.

Architecture rule:

```text
Telegram Mini App UI
    ↓
existing backend API
    ↓
Business Context Builder module
```

MVP must not:

- implement Telegram Mini App frontend;
- add Telegram-specific backend business logic;
- call Telegram APIs from Business Context Builder;
- expose separate Telegram backend ports.

Telegram identity fields remain optional and reserved.

---

# 13. Publishing Boundary

Publishing is separate from Business Context Builder MVP.

Future publishing must be an explicit workflow:

```text
draft result
    ↓
operator review
    ↓
explicit publish action
    ↓
validation against platform safety rules
    ↓
controlled production assistant update
```

Until that workflow exists:

- draft results remain in `business_context_builder.results`;
- active assistant tables are unchanged;
- production assistant prompts are unchanged;
- production assistant behavior is unchanged.

---

# 14. Safety Rules

- Business Context Builder data is draft-only.
- Never modify active AI assistant business contexts from this module.
- Never write Business Context Builder data into production assistant tables.
- Always use the `business_context_builder` PostgreSQL schema.
- Publishing to production assistants requires a separate explicit workflow.
- No n8n, CRM, Telegram Mini App, or OpenAI integration in the backend MVP unless a later task explicitly requests it.
- Preserve tenant isolation with `tenant_id` and `business_id`.

---

# 15. Related Specifications

- [business-context-builder-mvp.md](business-context-builder-mvp.md)
- [business-context-builder-database.md](business-context-builder-database.md)
- [business-context-builder-flow.md](business-context-builder-flow.md)
- [business-context-builder-api.md](business-context-builder-api.md)
- [../architecture/system-architecture.md](../architecture/system-architecture.md)
- [../architecture/backend-architecture.md](../architecture/backend-architecture.md)
- [../architecture/ai-configuration-architecture.md](../architecture/ai-configuration-architecture.md)
