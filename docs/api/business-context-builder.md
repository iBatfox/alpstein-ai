**Doc status:** runtime-derived API guide  
**Tier:** api/runtime  
**Canonical contract:** [`specs/context/business-context-builder-api.md`](../../specs/context/business-context-builder-api.md)

# Business Context Builder API

## Purpose

Business Context Builder collects interview answers and creates draft business context artifacts for onboarding and operator review.

The module can:

- create an interview session;
- store interview messages;
- ask the next interview question;
- complete a session;
- store a draft structured context and generated prompt;
- list saved draft contexts.

Business Context Builder output is draft-only. It is not a production assistant configuration.

---

# Isolation Rules

Business Context Builder must remain isolated from active assistant configuration.

Rules:

- writes only to PostgreSQL schema `business_context_builder`;
- does not write to production assistant tables;
- does not publish generated prompts or contexts;
- does not trigger n8n, CRM, Telegram Mini App, or production assistant workflows;
- uses tenant/business scoped access for every request;
- result metadata is stored under `structured_context.generation_metadata`.

---

# Auth

All Business Context Builder endpoints require the backend internal/webhook token dependency.

Required header:

```text
X-Alpstein-Webhook-Token: <token>
```

For local examples:

```bash
BASE_URL=http://localhost:8000
TOKEN=change-me
TENANT_ID=00000000-0000-0000-0000-000000000001
BUSINESS_ID=00000000-0000-0000-0000-000000000002
```

Common auth errors:

```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing webhook token"
  }
}
```

```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "Invalid webhook token"
  }
}
```

---

# Base Path

```text
/api/v1/business-context-builder
```

Full local base:

```text
http://localhost:8000/api/v1/business-context-builder
```

---

# Feature Flags

## BCB_AI_ENABLED

Controls AI next-question generation.

When `BCB_AI_ENABLED=false`, the backend stores the user message and returns a deterministic static assistant fallback question.

## BCB_AI_DRAFT_ENABLED

Controls AI draft result generation during session completion.

When `BCB_AI_DRAFT_ENABLED=false`, the backend completes the session with a deterministic fallback draft result.

Default behavior:

```text
BCB_AI_ENABLED=true
BCB_AI_DRAFT_ENABLED=false
```

---

# AI Fallback Behavior

Fallback is expected and safe.

The backend uses fallback behavior when:

- the related BCB AI feature flag is disabled;
- OpenAI/API key configuration is missing;
- the AI Gateway returns an error;
- the AI response is empty or cannot be parsed for draft result generation;
- an unexpected AI service error occurs.

Fallback behavior:

- request still succeeds when validation and database writes succeed;
- BCB data remains in `business_context_builder`;
- no production assistant data changes;
- draft result metadata records fallback state under `structured_context.generation_metadata`.

Example draft metadata:

```json
{
  "generation_metadata": {
    "provider": null,
    "model": null,
    "prompt_version": "1.0",
    "generation_timestamp": "2026-06-08T10:00:00+00:00",
    "fallback_used": true,
    "ai_enabled": false,
    "generation_mode": "fallback"
  }
}
```

---

# Shared Headers

Use these headers for every request:

```bash
-H "X-Alpstein-Webhook-Token: $TOKEN"
-H "Content-Type: application/json"
```

For `GET` requests, `Content-Type` is optional.

---

# Endpoint: POST /sessions

## Purpose

Create a new interview session and return the first assistant question.

## Required Headers

```text
X-Alpstein-Webhook-Token
Content-Type: application/json
```

## Request Body

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "business_id": "00000000-0000-0000-0000-000000000002",
  "telegram_user_id": null,
  "customer_id": null
}
```

Required:

- `tenant_id`
- `business_id`

Optional:

- `telegram_user_id`
- `customer_id`

## Response Body

```json
{
  "success": true,
  "data": {
    "session": {
      "id": "11111111-1111-1111-1111-111111111111",
      "tenant_id": "00000000-0000-0000-0000-000000000001",
      "business_id": "00000000-0000-0000-0000-000000000002",
      "telegram_user_id": null,
      "customer_id": null,
      "status": "active",
      "current_step": "company_information",
      "created_at": "2026-06-08T10:00:00",
      "updated_at": "2026-06-08T10:00:00",
      "completed_at": null
    },
    "message": {
      "id": "22222222-2222-2222-2222-222222222222",
      "session_id": "11111111-1111-1111-1111-111111111111",
      "role": "assistant",
      "content": "Hello. I will help you create a draft Business Context. What is the name of your company?",
      "created_at": "2026-06-08T10:00:00"
    }
  }
}
```

## Common Error Responses

Missing or invalid body:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "tenant_id"],
      "msg": "Field required"
    }
  ]
}
```

Missing or invalid token:

```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing webhook token"
  }
}
```

## curl

```bash
curl -sS -X POST "$BASE_URL/api/v1/business-context-builder/sessions" \
  -H "X-Alpstein-Webhook-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"business_id\": \"$BUSINESS_ID\",
    \"telegram_user_id\": null,
    \"customer_id\": null
  }"
```

---

# Endpoint: POST /sessions/{session_id}/messages

## Purpose

Add a user answer to an active session and return the next assistant message.

## Required Headers

```text
X-Alpstein-Webhook-Token
Content-Type: application/json
```

## Request Body

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "business_id": "00000000-0000-0000-0000-000000000002",
  "content": "Alpstein Services GmbH helps local businesses automate customer conversations."
}
```

Required:

- `tenant_id`
- `business_id`
- `content`

`content` must be a non-empty string.

## Response Body

```json
{
  "success": true,
  "data": {
    "session": {
      "id": "11111111-1111-1111-1111-111111111111",
      "tenant_id": "00000000-0000-0000-0000-000000000001",
      "business_id": "00000000-0000-0000-0000-000000000002",
      "telegram_user_id": null,
      "customer_id": null,
      "status": "active",
      "current_step": "business_description",
      "created_at": "2026-06-08T10:00:00",
      "updated_at": "2026-06-08T10:01:00",
      "completed_at": null
    },
    "user_message": {
      "id": "33333333-3333-3333-3333-333333333333",
      "session_id": "11111111-1111-1111-1111-111111111111",
      "role": "user",
      "content": "Alpstein Services GmbH helps local businesses automate customer conversations.",
      "created_at": "2026-06-08T10:01:00"
    },
    "assistant_message": {
      "id": "44444444-4444-4444-4444-444444444444",
      "session_id": "11111111-1111-1111-1111-111111111111",
      "role": "assistant",
      "content": "Who are your target customers?",
      "created_at": "2026-06-08T10:01:01"
    }
  }
}
```

## Common Error Responses

Session not found:

```json
{
  "success": false,
  "error": {
    "code": "CONTEXT_BUILDER_SESSION_NOT_FOUND",
    "message": "Business Context Builder session not found"
  }
}
```

Tenant/business scope mismatch:

```json
{
  "success": false,
  "error": {
    "code": "CONTEXT_BUILDER_SCOPE_MISMATCH",
    "message": "Business Context Builder session is outside the requested tenant or business"
  }
}
```

Completed session cannot receive messages:

```json
{
  "success": false,
  "error": {
    "code": "CONTEXT_BUILDER_SESSION_CLOSED",
    "message": "Business Context Builder session is completed or cancelled"
  }
}
```

Empty content:

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "content"],
      "msg": "String should have at least 1 character"
    }
  ]
}
```

## curl

```bash
curl -sS -X POST "$BASE_URL/api/v1/business-context-builder/sessions/$SESSION_ID/messages" \
  -H "X-Alpstein-Webhook-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"business_id\": \"$BUSINESS_ID\",
    \"content\": \"Alpstein Services GmbH helps local businesses automate customer conversations.\"
  }"
```

---

# Endpoint: GET /sessions/{session_id}

## Purpose

Retrieve one session with all messages and the draft result when available.

## Required Headers

```text
X-Alpstein-Webhook-Token
```

## Query Parameters

```text
tenant_id UUID required
business_id UUID required
```

## Response Body

```json
{
  "success": true,
  "data": {
    "session": {
      "id": "11111111-1111-1111-1111-111111111111",
      "tenant_id": "00000000-0000-0000-0000-000000000001",
      "business_id": "00000000-0000-0000-0000-000000000002",
      "telegram_user_id": null,
      "customer_id": null,
      "status": "active",
      "current_step": "target_customers",
      "created_at": "2026-06-08T10:00:00",
      "updated_at": "2026-06-08T10:02:00",
      "completed_at": null
    },
    "messages": [
      {
        "id": "22222222-2222-2222-2222-222222222222",
        "session_id": "11111111-1111-1111-1111-111111111111",
        "role": "assistant",
        "content": "Hello. I will help you create a draft Business Context. What is the name of your company?",
        "created_at": "2026-06-08T10:00:00"
      }
    ],
    "result": null
  }
}
```

## Common Error Responses

Session not found:

```json
{
  "success": false,
  "error": {
    "code": "CONTEXT_BUILDER_SESSION_NOT_FOUND",
    "message": "Business Context Builder session not found"
  }
}
```

Missing query parameter:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["query", "tenant_id"],
      "msg": "Field required"
    }
  ]
}
```

## curl

```bash
curl -sS "$BASE_URL/api/v1/business-context-builder/sessions/$SESSION_ID?tenant_id=$TENANT_ID&business_id=$BUSINESS_ID" \
  -H "X-Alpstein-Webhook-Token: $TOKEN"
```

---

# Endpoint: POST /sessions/{session_id}/complete

## Purpose

Complete an active session and create one draft context result.

At least one user message is required before completion.

## Required Headers

```text
X-Alpstein-Webhook-Token
Content-Type: application/json
```

## Request Body

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "business_id": "00000000-0000-0000-0000-000000000002"
}
```

## Response Body

```json
{
  "success": true,
  "data": {
    "session": {
      "id": "11111111-1111-1111-1111-111111111111",
      "tenant_id": "00000000-0000-0000-0000-000000000001",
      "business_id": "00000000-0000-0000-0000-000000000002",
      "telegram_user_id": null,
      "customer_id": null,
      "status": "completed",
      "current_step": "completed",
      "created_at": "2026-06-08T10:00:00",
      "updated_at": "2026-06-08T10:05:00",
      "completed_at": "2026-06-08T10:05:00"
    },
    "result": {
      "id": "55555555-5555-5555-5555-555555555555",
      "session_id": "11111111-1111-1111-1111-111111111111",
      "tenant_id": "00000000-0000-0000-0000-000000000001",
      "business_id": "00000000-0000-0000-0000-000000000002",
      "structured_context": {
        "company_overview": "Alpstein Services GmbH",
        "business_description": "Helps local businesses automate customer conversations.",
        "target_customers": "Local service businesses",
        "products_services": "AI customer conversation automation",
        "sales_process": "Unknown or not provided.",
        "communication_style": "Professional and concise",
        "known_constraints": [],
        "missing_information": ["pricing", "handoff rules"],
        "draft_quality_confidence": {
          "level": "low",
          "reason": "Fallback draft generated without AI interpretation."
        },
        "generation_metadata": {
          "provider": null,
          "model": null,
          "prompt_version": "1.0",
          "generation_timestamp": "2026-06-08T10:05:00+00:00",
          "fallback_used": true,
          "ai_enabled": false,
          "generation_mode": "fallback"
        }
      },
      "generated_prompt": "Draft fallback business context generated from the interview transcript. Review is required before any production assistant use.",
      "context_file_path": null,
      "context_file_url": null,
      "created_at": "2026-06-08T10:05:00",
      "updated_at": "2026-06-08T10:05:00"
    }
  }
}
```

## Common Error Responses

Session not found:

```json
{
  "success": false,
  "error": {
    "code": "CONTEXT_BUILDER_SESSION_NOT_FOUND",
    "message": "Business Context Builder session not found"
  }
}
```

No user messages before completion:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "at least one user message is required before completion"
  }
}
```

Already completed or invalid status:

```json
{
  "success": false,
  "error": {
    "code": "CONTEXT_BUILDER_INVALID_STATUS_TRANSITION",
    "message": "cannot complete session with status completed"
  }
}
```

## curl

```bash
curl -sS -X POST "$BASE_URL/api/v1/business-context-builder/sessions/$SESSION_ID/complete" \
  -H "X-Alpstein-Webhook-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"business_id\": \"$BUSINESS_ID\"
  }"
```

---

# Endpoint: GET /contexts?limit=20&offset=0

## Purpose

List draft context results for one tenant and business.

## Required Headers

```text
X-Alpstein-Webhook-Token
```

## Query Parameters

```text
tenant_id UUID required
business_id UUID required
limit integer optional, default 50, min 1, max 100
offset integer optional, default 0, min 0
```

## Response Body

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "55555555-5555-5555-5555-555555555555",
        "session_id": "11111111-1111-1111-1111-111111111111",
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "business_id": "00000000-0000-0000-0000-000000000002",
        "generated_prompt": "Draft fallback business context generated from the interview transcript. Review is required before any production assistant use.",
        "context_file_path": null,
        "context_file_url": null,
        "created_at": "2026-06-08T10:05:00",
        "updated_at": "2026-06-08T10:05:00"
      }
    ],
    "limit": 20,
    "offset": 0
  }
}
```

## Common Error Responses

Invalid limit:

```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["query", "limit"],
      "msg": "Input should be less than or equal to 100"
    }
  ]
}
```

Invalid offset:

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["query", "offset"],
      "msg": "Input should be greater than or equal to 0"
    }
  ]
}
```

## curl

```bash
curl -sS "$BASE_URL/api/v1/business-context-builder/contexts?tenant_id=$TENANT_ID&business_id=$BUSINESS_ID&limit=20&offset=0" \
  -H "X-Alpstein-Webhook-Token: $TOKEN"
```

---

# Full Happy Path

Set local placeholders:

```bash
BASE_URL=http://localhost:8000
TOKEN=change-me
TENANT_ID=00000000-0000-0000-0000-000000000001
BUSINESS_ID=00000000-0000-0000-0000-000000000002
```

Create a session:

```bash
CREATE_RESPONSE=$(curl -sS -X POST "$BASE_URL/api/v1/business-context-builder/sessions" \
  -H "X-Alpstein-Webhook-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"business_id\": \"$BUSINESS_ID\",
    \"telegram_user_id\": null,
    \"customer_id\": null
  }")

echo "$CREATE_RESPONSE"
SESSION_ID=$(printf '%s' "$CREATE_RESPONSE" | jq -r '.data.session.id')
```

Send first user message:

```bash
curl -sS -X POST "$BASE_URL/api/v1/business-context-builder/sessions/$SESSION_ID/messages" \
  -H "X-Alpstein-Webhook-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"business_id\": \"$BUSINESS_ID\",
    \"content\": \"Our company is Alpstein Services GmbH in St. Gallen.\"
  }"
```

Send second user message:

```bash
curl -sS -X POST "$BASE_URL/api/v1/business-context-builder/sessions/$SESSION_ID/messages" \
  -H "X-Alpstein-Webhook-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"business_id\": \"$BUSINESS_ID\",
    \"content\": \"We help local businesses automate customer messages, lead capture, and owner notifications.\"
  }"
```

Retrieve the session:

```bash
curl -sS "$BASE_URL/api/v1/business-context-builder/sessions/$SESSION_ID?tenant_id=$TENANT_ID&business_id=$BUSINESS_ID" \
  -H "X-Alpstein-Webhook-Token: $TOKEN"
```

Complete the session:

```bash
curl -sS -X POST "$BASE_URL/api/v1/business-context-builder/sessions/$SESSION_ID/complete" \
  -H "X-Alpstein-Webhook-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"business_id\": \"$BUSINESS_ID\"
  }"
```

List contexts:

```bash
curl -sS "$BASE_URL/api/v1/business-context-builder/contexts?tenant_id=$TENANT_ID&business_id=$BUSINESS_ID&limit=20&offset=0" \
  -H "X-Alpstein-Webhook-Token: $TOKEN"
```

---

# Error Examples

## Session Not Found

```bash
curl -sS "$BASE_URL/api/v1/business-context-builder/sessions/99999999-9999-9999-9999-999999999999?tenant_id=$TENANT_ID&business_id=$BUSINESS_ID" \
  -H "X-Alpstein-Webhook-Token: $TOKEN"
```

```json
{
  "success": false,
  "error": {
    "code": "CONTEXT_BUILDER_SESSION_NOT_FOUND",
    "message": "Business Context Builder session not found"
  }
}
```

## Completed Session Cannot Receive Messages

```bash
curl -sS -X POST "$BASE_URL/api/v1/business-context-builder/sessions/$SESSION_ID/messages" \
  -H "X-Alpstein-Webhook-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"business_id\": \"$BUSINESS_ID\",
    \"content\": \"Can I add one more detail?\"
  }"
```

```json
{
  "success": false,
  "error": {
    "code": "CONTEXT_BUILDER_SESSION_CLOSED",
    "message": "Business Context Builder session is completed or cancelled"
  }
}
```

## Invalid limit/offset

```bash
curl -sS "$BASE_URL/api/v1/business-context-builder/contexts?tenant_id=$TENANT_ID&business_id=$BUSINESS_ID&limit=0&offset=-1" \
  -H "X-Alpstein-Webhook-Token: $TOKEN"
```

FastAPI validation returns a `detail` array for query validation errors.

## AI Fallback Note

No error is returned just because AI is disabled or unavailable.

Expected successful fallback:

```json
{
  "success": true,
  "data": {
    "result": {
      "structured_context": {
        "generation_metadata": {
          "prompt_version": "1.0",
          "fallback_used": true,
          "ai_enabled": false,
          "generation_mode": "fallback"
        }
      }
    }
  }
}
```

---

# Developer Notes

- BCB writes only to PostgreSQL schema `business_context_builder`.
- BCB tables do not use external foreign keys to production assistant tables.
- BCB must not write to production assistant tables.
- BCB must not publish to active AI assistants.
- BCB must not trigger n8n, CRM, or Telegram Mini App workflows.
- Result metadata is stored under `structured_context.generation_metadata`.
- `BCB_AI_ENABLED` controls next-question AI generation.
- `BCB_AI_DRAFT_ENABLED` controls final draft result AI generation.
- Next question prompt version: `1.0`.
- Draft result prompt version: `1.0`.
- Context list responses return result summaries and do not include full `structured_context`; retrieve the session to see the full result.

Prompt version constants:

```text
BCB_NEXT_QUESTION_PROMPT_VERSION=1.0
BCB_DRAFT_RESULT_PROMPT_VERSION=1.0
```
