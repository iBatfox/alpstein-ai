# Business Context Builder API Specification

## 1. Purpose

This document defines the MVP API contract for Business Context Builder.

The API is implemented inside the existing Alpstein AI backend under:

```text
/api/v1/business-context-builder
```

All endpoints use JSON request and response bodies and the existing Alpstein AI response envelope.

---

# 2. API Principles

Business Context Builder endpoints must:

- use `/api/v1`;
- return `success`, `data`, and `error` envelopes;
- validate tenant and business scope;
- read and write only the `business_context_builder` PostgreSQL schema;
- expose draft context data only;
- avoid production assistant side effects.

The API must not:

- call OpenAI in the MVP;
- trigger n8n workflows in the MVP;
- upload files to CRM in the MVP;
- create or update production AI assistants;
- expose internal platform system prompts.

---

# 3. Authentication

MVP authentication follows existing Alpstein AI internal/admin endpoint rules.

Allowed options:

```text
internal network
admin/internal API token
```

Full public customer authentication, RBAC, OAuth, and Telegram Mini App authentication are out of scope for the backend MVP.

---

# 4. Response Envelope

Successful response:

```json
{
  "success": true,
  "data": {}
}
```

Error response:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message"
  }
}
```

Common error codes:

```text
VALIDATION_ERROR
TENANT_NOT_FOUND
BUSINESS_NOT_FOUND
CONTEXT_BUILDER_SESSION_NOT_FOUND
CONTEXT_BUILDER_SESSION_COMPLETED
CONTEXT_BUILDER_RESULT_EXISTS
UNAUTHORIZED
FORBIDDEN
DATABASE_ERROR
INTERNAL_ERROR
```

If implementation prefers only globally defined error codes, module-specific cases may use `VALIDATION_ERROR`, `FORBIDDEN`, or `INTERNAL_ERROR` with precise messages.

---

# 5. Shared Resource Shapes

## Session

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "business_id": "uuid",
  "telegram_user_id": null,
  "customer_id": null,
  "status": "in_progress",
  "current_step": "company_information",
  "created_at": "2026-06-07T12:00:00Z",
  "updated_at": "2026-06-07T12:00:00Z",
  "completed_at": null
}
```

## Message

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "role": "assistant",
  "content": "Hello. I will help you create a draft Business Context. What is the name of your company?",
  "created_at": "2026-06-07T12:00:00Z"
}
```

## Result

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "tenant_id": "uuid",
  "business_id": "uuid",
  "structured_context": {
    "company": {},
    "business_description": "",
    "assistant_goals": [],
    "services": [],
    "target_customers": {},
    "common_questions": [],
    "lead_qualification": {},
    "communication_style": {},
    "restrictions": [],
    "handoff_rules": []
  },
  "generated_prompt": "Draft placeholder prompt text.",
  "context_file_path": null,
  "context_file_url": null,
  "created_at": "2026-06-07T12:00:00Z",
  "updated_at": "2026-06-07T12:00:00Z"
}
```

---

# 6. POST /api/v1/business-context-builder/sessions

Purpose:

Create a new Business Context Builder interview session.

Request body:

```json
{
  "tenant_id": "uuid",
  "business_id": "uuid",
  "telegram_user_id": null,
  "customer_id": null
}
```

Required fields:

```text
tenant_id
business_id
```

Optional fields:

```text
telegram_user_id
customer_id
```

Response body:

```json
{
  "success": true,
  "data": {
    "session": {
      "id": "uuid",
      "tenant_id": "uuid",
      "business_id": "uuid",
      "telegram_user_id": null,
      "customer_id": null,
      "status": "in_progress",
      "current_step": "company_information",
      "created_at": "2026-06-07T12:00:00Z",
      "updated_at": "2026-06-07T12:00:00Z",
      "completed_at": null
    },
    "message": {
      "id": "uuid",
      "session_id": "uuid",
      "role": "assistant",
      "content": "Hello. I will help you create a draft Business Context. What is the name of your company?",
      "created_at": "2026-06-07T12:00:00Z"
    }
  }
}
```

Behavior:

- validates tenant and business scope;
- creates one session in `business_context_builder.sessions`;
- creates the first assistant message in `business_context_builder.messages`;
- returns the session and first assistant question.

Error cases:

| Case | Error code |
|------|------------|
| Missing required field | `VALIDATION_ERROR` |
| Tenant does not exist or is not accessible | `TENANT_NOT_FOUND` or `FORBIDDEN` |
| Business does not exist or is not accessible | `BUSINESS_NOT_FOUND` or `FORBIDDEN` |
| Caller is not authorized | `UNAUTHORIZED` |
| Database write fails | `DATABASE_ERROR` |

MVP limitations:

- first assistant question is static placeholder text;
- no OpenAI call;
- no Telegram Mini App auth;
- no CRM linkage beyond reserved IDs;
- no production assistant update.

---

# 7. POST /api/v1/business-context-builder/sessions/{session_id}/messages

Purpose:

Add a user message to an active interview session and receive the next placeholder assistant question.

Request body:

```json
{
  "tenant_id": "uuid",
  "business_id": "uuid",
  "content": "We are a local service business in St. Gallen."
}
```

Required fields:

```text
tenant_id
business_id
content
```

Response body:

```json
{
  "success": true,
  "data": {
    "session": {
      "id": "uuid",
      "tenant_id": "uuid",
      "business_id": "uuid",
      "status": "in_progress",
      "current_step": "business_description",
      "created_at": "2026-06-07T12:00:00Z",
      "updated_at": "2026-06-07T12:05:00Z",
      "completed_at": null
    },
    "user_message": {
      "id": "uuid",
      "session_id": "uuid",
      "role": "user",
      "content": "We are a local service business in St. Gallen.",
      "created_at": "2026-06-07T12:05:00Z"
    },
    "assistant_message": {
      "id": "uuid",
      "session_id": "uuid",
      "role": "assistant",
      "content": "What are your main services?",
      "created_at": "2026-06-07T12:05:01Z"
    }
  }
}
```

Behavior:

- validates tenant and business scope;
- verifies the session is `in_progress`;
- saves the user message;
- advances `current_step` using placeholder logic;
- saves the assistant placeholder reply;
- returns both saved messages.

Error cases:

| Case | Error code |
|------|------------|
| Invalid `session_id` | `VALIDATION_ERROR` |
| Session not found in tenant/business scope | `CONTEXT_BUILDER_SESSION_NOT_FOUND` or `FORBIDDEN` |
| Session is completed or archived | `CONTEXT_BUILDER_SESSION_COMPLETED` or `VALIDATION_ERROR` |
| Empty content | `VALIDATION_ERROR` |
| Caller is not authorized | `UNAUTHORIZED` |
| Database write fails | `DATABASE_ERROR` |

MVP limitations:

- next question is static/deterministic;
- no AI interpretation of user content;
- no file generation;
- no production assistant update.

---

# 8. GET /api/v1/business-context-builder/sessions/{session_id}

Purpose:

Retrieve one interview session with its messages and optional result.

Query parameters:

```text
tenant_id UUID required
business_id UUID required
```

Response body:

```json
{
  "success": true,
  "data": {
    "session": {
      "id": "uuid",
      "tenant_id": "uuid",
      "business_id": "uuid",
      "status": "in_progress",
      "current_step": "services",
      "created_at": "2026-06-07T12:00:00Z",
      "updated_at": "2026-06-07T12:10:00Z",
      "completed_at": null
    },
    "messages": [
      {
        "id": "uuid",
        "session_id": "uuid",
        "role": "assistant",
        "content": "Hello. I will help you create a draft Business Context. What is the name of your company?",
        "created_at": "2026-06-07T12:00:00Z"
      }
    ],
    "result": null
  }
}
```

Behavior:

- filters by `tenant_id`, `business_id`, and `session_id`;
- returns messages ordered by `created_at`;
- includes `result` only if the session was completed and a result exists.

Error cases:

| Case | Error code |
|------|------------|
| Missing tenant or business query parameter | `VALIDATION_ERROR` |
| Session not found in scope | `CONTEXT_BUILDER_SESSION_NOT_FOUND` or `FORBIDDEN` |
| Caller is not authorized | `UNAUTHORIZED` |
| Database read fails | `DATABASE_ERROR` |

MVP limitations:

- no pagination for session messages unless later required;
- no production assistant data included;
- no generated context file included beyond nullable reserved fields.

---

# 9. POST /api/v1/business-context-builder/sessions/{session_id}/complete

Purpose:

Complete an interview session and create a draft result.

Request body:

```json
{
  "tenant_id": "uuid",
  "business_id": "uuid"
}
```

Required fields:

```text
tenant_id
business_id
```

Response body:

```json
{
  "success": true,
  "data": {
    "session": {
      "id": "uuid",
      "tenant_id": "uuid",
      "business_id": "uuid",
      "status": "completed",
      "current_step": "completed",
      "created_at": "2026-06-07T12:00:00Z",
      "updated_at": "2026-06-07T12:30:00Z",
      "completed_at": "2026-06-07T12:30:00Z"
    },
    "result": {
      "id": "uuid",
      "session_id": "uuid",
      "tenant_id": "uuid",
      "business_id": "uuid",
      "structured_context": {
        "company": {},
        "business_description": "",
        "assistant_goals": [],
        "services": [],
        "target_customers": {},
        "common_questions": [],
        "lead_qualification": {},
        "communication_style": {},
        "restrictions": [],
        "handoff_rules": []
      },
      "generated_prompt": "Draft placeholder prompt text.",
      "context_file_path": null,
      "context_file_url": null,
      "created_at": "2026-06-07T12:30:00Z",
      "updated_at": "2026-06-07T12:30:00Z"
    }
  }
}
```

Behavior:

- validates tenant and business scope;
- verifies the session is active;
- applies MVP completion rules;
- marks session `completed`;
- creates one result in `business_context_builder.results`;
- returns the completed session and result.

Error cases:

| Case | Error code |
|------|------------|
| Session not found in scope | `CONTEXT_BUILDER_SESSION_NOT_FOUND` or `FORBIDDEN` |
| Session already completed and result exists | `CONTEXT_BUILDER_RESULT_EXISTS` or return existing result |
| Required completion data missing | `VALIDATION_ERROR` |
| Caller is not authorized | `UNAUTHORIZED` |
| Database write fails | `DATABASE_ERROR` |

MVP limitations:

- result is placeholder-generated;
- no OpenAI call;
- no file generation;
- no CRM attachment;
- no n8n export;
- no production assistant publishing.

---

# 10. GET /api/v1/business-context-builder/contexts

Purpose:

List draft generated contexts for a tenant and business.

Query parameters:

```text
tenant_id UUID required
business_id UUID optional or required by caller context
limit integer optional, default 50, max 100
offset integer optional, default 0
```

Response body:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "session_id": "uuid",
        "tenant_id": "uuid",
        "business_id": "uuid",
        "generated_prompt": "Draft placeholder prompt text.",
        "context_file_path": null,
        "context_file_url": null,
        "created_at": "2026-06-07T12:30:00Z",
        "updated_at": "2026-06-07T12:30:00Z"
      }
    ],
    "limit": 50,
    "offset": 0
  }
}
```

Behavior:

- filters by `tenant_id`;
- filters by `business_id` when provided or required;
- returns only Business Context Builder draft results;
- orders newest first unless implementation documents another order.

Error cases:

| Case | Error code |
|------|------------|
| Missing tenant query parameter | `VALIDATION_ERROR` |
| Business not accessible | `BUSINESS_NOT_FOUND` or `FORBIDDEN` |
| Caller is not authorized | `UNAUTHORIZED` |
| Database read fails | `DATABASE_ERROR` |

MVP limitations:

- list endpoint returns draft contexts only;
- no production assistant contexts included;
- no publish status unless a later workflow adds it;
- no CRM attachment status beyond nullable reserved fields.

---

# 11. Safety Rules

- Every endpoint must enforce tenant isolation.
- Business-scoped reads and writes must filter by `tenant_id` and `business_id`.
- Never return production assistant business contexts from these endpoints.
- Never write to production assistant tables from these endpoints.
- Never trigger n8n, CRM, Telegram, or OpenAI side effects in the MVP.
- Publishing requires a separate explicit workflow and separate API contract.

---

# 12. Related Specifications

- [business-context-builder-mvp.md](business-context-builder-mvp.md)
- [business-context-builder-flow.md](business-context-builder-flow.md)
- [business-context-builder-database.md](business-context-builder-database.md)
- [../api/api-endpoints.md](../api/api-endpoints.md)
