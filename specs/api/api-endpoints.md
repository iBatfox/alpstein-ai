# Alpstein AI — API Endpoints

## 1. Purpose

This document describes the backend API endpoints for Alpstein AI MVP.

The backend API is used by:

- n8n automation workflows;
- future admin dashboard;
- future internal tools;
- future integrations.

The MVP API must stay simple and focused on the core message flow.

---

# 2. API Design Principles

## 2.1 Backend Owns Business Logic

The backend API owns:

- validation;
- business logic;
- AI processing;
- database operations;
- lead creation.

n8n sends requests and triggers workflows, but does not own business logic.

---

## 2.2 Normalized Payloads

The backend should only receive normalized payloads.

Raw WhatsApp, Telegram, Instagram, or website chat payloads must be normalized by n8n before being sent to the backend.

---

## 2.3 JSON Only

All MVP API endpoints use JSON request and response bodies.

---

## 2.4 Tenant Safety

Every endpoint that reads or writes client-owned data must use tenant-aware access.

Client-owned data must always be filtered by:

```text
tenant_id
```

Where relevant, also by:

```text
business_id
```

---

## 2.5 MVP Authentication

For MVP, admin authentication can be simple.

Possible options:

- internal network only;
- API token;
- basic admin token.

Full user authentication is not required in MVP.

---

# 3. Base URL

Production domain:

```text
https://alpstein-ai.ch
```

Future API subdomain:

```text
https://api.alpstein-ai.ch
```

For MVP, the backend may be routed through nginx.

Example:

```text
https://alpstein-ai.ch/api
```

---

# 4. API Versioning

MVP version:

```text
/api/v1
```

All backend endpoints should use this prefix where possible.

Example:

```text
GET /api/v1/health
POST /api/v1/webhook/message
```

---

# 5. Response Format

## 5.1 Successful Response

Generic success format:

```json
{
  "success": true,
  "data": {}
}
```

---

## 5.2 Error Response

Generic error format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message"
  }
}
```

---

# 6. Health Endpoint

## GET /api/v1/health

Purpose:

Check that backend service is running.

Authentication:

```text
not required
```

Response:

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "alpstein-ai-backend",
    "environment": "production"
  }
}
```

---

# 7. Observability Endpoints (E2.5)

Read-only message trace inspection for ops and internal tools. Same API token as webhook (`X-Alpstein-Webhook-Token`).

All endpoints require query parameters:

```text
tenant_id (UUID, required)
business_id (UUID, required)
```

## GET /api/v1/observability/traces/{trace_id}

Returns one `message_traces` row when scoped to tenant + business.

## GET /api/v1/observability/traces

Lookup by exactly one of:

```text
inbound_message_id (UUID)
external_message_id (string, optional conversation_id filter)
```

## GET /api/v1/observability/conversations/{conversation_id}/traces

List traces for a conversation. Optional filters: `status`, `channel`, `limit` (max 100), `offset`.

Response envelope: `{ "success": true, "data": { "items": [...], "limit", "offset" } }`.

Trace payloads exclude prompts, raw provider payloads, and secrets.

Webhook success `data` may include optional `trace` object:

```json
{
  "trace_id": "uuid",
  "correlation_id": "uuid",
  "processing_status": "completed"
}
```

## GET /api/v1/observability/deliveries/{delivery_id}

Returns one `delivery_events` row when scoped to tenant + business.

## GET /api/v1/observability/conversations/{conversation_id}/deliveries

List outbound delivery rows for a conversation. Optional filters: `status`, `channel`, `limit` (max 100), `offset`.

## PATCH /api/v1/observability/deliveries/{delivery_id}

n8n reports channel delivery outcome after send attempt. Body:

```json
{
  "status": "delivered",
  "provider_message_id": "optional-provider-id",
  "provider_status": "optional"
}
```

For `failed`, include `error_type` and/or `error_message` (safe text only; no secrets or raw provider payloads).

Webhook success `data` may include optional `delivery` object:

```json
{
  "delivery_id": "uuid",
  "delivery_status": "pending",
  "outbound_message_id": "uuid"
}
```

## GET /api/v1/observability/replays

**E3.1c** — List retry/replay audit rows for ops. Auth: same webhook/internal token as other observability routes.

Required query: `tenant_id`, `business_id`.

Optional filters: `trace_id`, `delivery_id`, `conversation_id`, `idempotency_key`, `event_type`, `limit` (max 100), `offset`.

Response `data.items[]`: `id`, scope ids, `source` (`webhook` | `delivery_patch`), `event_type` (`duplicate_retry`, `replay_ignored`, `illegal_transition`, …), `idempotency_key`, `correlation_id`, safe `metadata`, `created_at`. No raw provider payloads or secrets.

Illegal delivery PATCH transitions are recorded as `illegal_transition` with `metadata.from_status` / `metadata.to_status`; delivery row state is unchanged (terminal-safe).

## GET /api/v1/observability/retries

**E3.2c** — List operational retry attempts (`retry_attempts`).

Required query: `tenant_id`, `business_id`.

Optional: `trace_id`, `delivery_id`, `conversation_id`, `scope_type`, `status`, `limit`, `offset`.

## GET /api/v1/observability/dead-letter

**E3.2c** — List dead-letter rows (`dead_letter_events`).

Required query: `tenant_id`, `business_id`.

Optional: `trace_id`, `delivery_id`, `conversation_id`, `inbound_message_id`, `event_type`, `scope_type`, `limit`, `offset`.

**Delivery PATCH (E3.2):** Repeated `failed` PATCH increments `retry_count` even when n8n never sends `retrying`. At `ALPSTEIN_DELIVERY_MAX_RETRIES` (default 3), delivery status becomes `dead_letter`. Terminal `error_type` values (e.g. `chat_not_found`) may dead-letter on first failure.

## GET /api/v1/observability/adapters

**E3.3b** — Adapter-level operational health for MVP channels (`telegram`, `website_chat`).

Auth: same webhook/internal token as other observability routes.

Required query: `tenant_id`, `business_id`.

Optional: `window_hours` (1–168, default from `ALPSTEIN_AI_ADAPTER_MONITOR_WINDOW_HOURS`, default 24).

Response `data`:

```json
{
  "window_hours": 24,
  "isolation_summary": {
    "isolation_status": "intact",
    "spread_risk": false,
    "affected_adapters": [],
    "healthy_adapters": ["telegram", "website_chat"],
    "inactive_adapters": [],
    "containment_notes": []
  },
  "items": [
    {
      "adapter": "telegram",
      "status": "healthy",
      "status_reasons": [],
      "ingress_status": "healthy",
      "delivery_status": "healthy",
      "ingress_status_reasons": [],
      "delivery_status_reasons": [],
      "containment_status": "normal",
      "recent_messages": 42,
      "ingress_failed_count": 0,
      "ingress_retry_count": 0,
      "ingress_dead_letter_count": 0,
      "delivery_success_count": 40,
      "delivery_failure_count": 1,
      "delivery_pending_count": 1,
      "retry_count": 2,
      "dead_letter_count": 0,
      "rate_limit_violation_count": 0,
      "delivery_failure_rate": 0.024,
      "last_activity_at": "2026-05-28T14:00:00Z"
    }
  ]
}
```

**E3.4:** `status` is the combined worst severity of `ingress_status` and `delivery_status`. `isolation_summary` describes cross-adapter containment (`intact` | `at_risk` | `unknown`). `containment_status` per adapter: `normal` | `contained` | `peer_at_risk` | `shared_at_risk`.

`status`: `healthy` | `warning` | `degraded` | `inactive` (deterministic from backend metrics).

No prompts, message text, secrets, tokens, or raw provider payloads.

## GET /api/v1/observability/adapters/{adapter}

**E3.3b / E3.4b** — Single adapter detail. Path `adapter` must be `telegram` or `website_chat`; unknown adapter → `404 NOT_FOUND`.

Same query params as list. Response `data` includes ingress/delivery split fields, `containment_status`, optional `peer_adapter` summary (status fields only), `evaluated_at`, and optional:

```json
{
  "breakdown": {
    "delivery_by_status": {
      "pending": 1,
      "delivered": 40,
      "failed": 1
    }
  },
  "peer_adapter": {
    "adapter": "website_chat",
    "status": "healthy",
    "ingress_status": "healthy",
    "delivery_status": "healthy",
    "containment_status": "peer_at_risk"
  }
}
```

Metrics are derived at read time from `message_traces`, `delivery_events`, `retry_attempts`, `dead_letter_events`, `rate_limit_violations` (violation count by channel), `spam_decisions`, and `spam_containments` (decision/containment counts by channel) within the lookback window.

## GET /api/v1/observability/rate-limits

**E3.5c** — List rate-limit violation audit rows. Auth: same webhook/internal token as other observability routes.

**Query (required):** `tenant_id`, `business_id`

**Query (optional):** `channel`, `scope_type`, `conversation_id`, `limit` (default 20, max 100), `offset` (default 0)

**Response:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "scope_type": "conversation",
        "scope_key": "uuid",
        "channel": "telegram",
        "conversation_id": "uuid",
        "limit_value": 30,
        "window_seconds": 60,
        "window_start": "2026-05-28T12:00:00Z",
        "observed_count": 31,
        "correlation_id": "uuid",
        "metadata": {
          "retry_after_seconds": 42,
          "limit": 30
        },
        "created_at": "2026-05-28T12:00:45Z"
      }
    ],
    "limit": 20,
    "offset": 0
  }
}
```

No prompts, message text, secrets, tokens, or raw provider payloads.

## GET /api/v1/observability/spam-decisions

**E3.6c** — List append-only spam decision audit rows. Auth: same webhook/internal token as other observability routes.

**Query (required):** `tenant_id`, `business_id`

**Query (optional):** `channel`, `rule_id`, `decision`, `conversation_id`, `limit` (default 20, max 100), `offset` (default 0)

**Response:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "rule_id": "payload_repeat",
        "scope_type": "conversation",
        "scope_key": "uuid:sha256prefix",
        "channel": "telegram",
        "conversation_id": "uuid",
        "decision": "mark_suspicious",
        "outcome": "applied",
        "observed_count": 5,
        "threshold": 5,
        "window_seconds": 300,
        "containment_id": null,
        "correlation_id": "uuid",
        "metadata": {
          "payload_hash_prefix": "abc123"
        },
        "created_at": "2026-05-28T12:00:45Z"
      }
    ],
    "limit": 20,
    "offset": 0
  }
}
```

No prompts, message text, secrets, tokens, or raw provider payloads.

## GET /api/v1/observability/spam-containments

**E3.6c** — List active or historical spam containment rows. Auth: same webhook/internal token as other observability routes.

**Query (required):** `tenant_id`, `business_id`

**Query (optional):** `channel`, `rule_id`, `action`, `conversation_id`, `active_only` (default `true`), `limit` (default 20, max 100), `offset` (default 0)

**Response:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "rule_id": "payload_repeat",
        "scope_type": "conversation",
        "scope_key": "uuid:sha256prefix",
        "channel": "telegram",
        "conversation_id": "uuid",
        "action": "throttle",
        "expires_at": "2026-05-28T12:05:45Z",
        "released_at": null,
        "correlation_id": "uuid",
        "metadata": {
          "observed_count": 5,
          "threshold": 5,
          "window_seconds": 300
        },
        "created_at": "2026-05-28T12:00:45Z"
      }
    ],
    "limit": 20,
    "offset": 0
  }
}
```

No prompts, message text, secrets, tokens, or raw provider payloads.

**E3.4c optional ingress gate:** When `ALPSTEIN_AI_INGRESS_CONTAINMENT_ENABLED=true` (default **false**), `POST /api/v1/webhook/message` may return `503` with `error.code=ADAPTER_INGRESS_CONTAINED` for the failing adapter only (inbound dead-letter evidence + `containment_status=contained`). Peer adapter is never blocked.

---

# 8. Incoming Message Endpoint

## POST /api/v1/webhook/message

Purpose:

Main endpoint used by n8n to send normalized incoming customer messages.

This is the most important MVP endpoint.

**Canonical contract (E1.2):** logical normalized fields and transport mapping — [normalized-channel-contract.md](../architecture/normalized-channel-contract.md). Wire format: [webhooks.md](webhooks.md) §7.

Authentication:

```text
API token recommended
```

Request:

```json
{
  "business_id": "demo_barbershop_001",
  "channel": "whatsapp",
  "operator_business_context": null,
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

Optional `operator_business_context` (string, max 8192 characters): operator-editable business notes from n8n; reference data for Prompt Builder only; not returned in response. Full contract: [webhooks.md](webhooks.md) §7. **Runtime:** T14-OC-2 (Prompt Builder append; not persisted in MVP).

Response:

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "Hello! Sure. What service would you like to book and what time works best for you?",
    "lead_created": true,
    "lead": {
      "id": "8a6a3a5e-6c02-4b87-b8d4-12d10c86c111",
      "status": "new",
      "service_requested": "Barbershop appointment"
    },
    "conversation": {
      "id": "b62cfe3c-7b7e-4dd3-9c91-2eb35d2de901",
      "status": "open"
    },
    "notify_owner": true
  }
}
```

Responsibilities:

- validate request;
- identify business by external ID;
- find or create customer;
- find or create conversation;
- save customer message;
- process AI response;
- save AI message;
- create lead if needed;
- return structured response to n8n.

**E3.5 optional rate limiting:** When `ALPSTEIN_AI_RATE_LIMIT_ENABLED=true` (default **false**), non-duplicate ingress may return **429** with `error.code=RATE_LIMIT_EXCEEDED` and safe `error.metadata` (`scope_type`, `retry_after_seconds`, `limit`, etc.). Idempotent duplicates do not increment counters. Enforcement runs after duplicate detection and before E3.4 ingress containment and AI orchestration. n8n should apply exponential backoff on 429 (see `docs/ops/ingress-rate-limit-429.md`).

**E3.6 optional anti-spam protection:** When `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED=true` (default **false**), non-duplicate ingress is evaluated for deterministic abuse rules after E3.5 rate limiting and before E3.4 ingress containment and AI orchestration. Initial production posture uses `ALPSTEIN_AI_SPAM_PRODUCTION_SAFE_MODE=true` (default) — only `mark_suspicious` decisions are applied; blocking actions (`throttle`, `temporary_block`, `ignore`) require staging validation with production safe mode off. May return **429** `SPAM_THROTTLED` or **403** `SPAM_CONTAINED` with safe `error.metadata` (`rule_id`, `decision`, etc.). No message text, prompts, secrets, or tokens in spam tables or error metadata. Payload repeat detection uses SHA-256 fingerprint of normalized message text (see `docs/ops/ingress-spam-protection.md`).

---

# 8. Business Endpoints

## POST /api/v1/businesses

Purpose:

Create a business profile.

Authentication:

```text
admin/internal required
```

Request:

```json
{
  "tenant_id": "43a1e937-0ef2-4725-97b6-7f016eea55ff",
  "external_id": "demo_barbershop_001",
  "name": "Demo Barbershop",
  "business_type": "barbershop",
  "description": "Local demo barbershop for Alpstein AI MVP.",
  "phone": "+41790000000",
  "email": "owner@example.com",
  "website": "https://example.com",
  "address": "St. Gallen, Switzerland",
  "working_hours": {
    "monday": "09:00-18:00",
    "tuesday": "09:00-18:00"
  },
  "language": "de",
  "timezone": "Europe/Zurich",
  "ai_prompt": "You are a polite AI assistant for a local barbershop.",
  "ai_tone": "friendly",
  "ai_language": "de"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "id": "15ecf8ed-b88d-495b-99d6-845d6cc6fdb3",
    "external_id": "demo_barbershop_001",
    "name": "Demo Barbershop",
    "status": "active"
  }
}
```

---

## GET /api/v1/businesses/{business_id}

Purpose:

Get business profile by internal UUID or external ID.

Authentication:

```text
admin/internal required
```

Response:

```json
{
  "success": true,
  "data": {
    "id": "15ecf8ed-b88d-495b-99d6-845d6cc6fdb3",
    "tenant_id": "43a1e937-0ef2-4725-97b6-7f016eea55ff",
    "external_id": "demo_barbershop_001",
    "name": "Demo Barbershop",
    "business_type": "barbershop",
    "status": "active"
  }
}
```

---

# 9. Lead Endpoints

## GET /api/v1/leads

Purpose:

Return leads.

Authentication:

```text
admin/internal required
```

Query parameters:

```text
tenant_id
business_id
status
limit
offset
```

Example:

```text
GET /api/v1/leads?tenant_id=...&business_id=...&status=new&limit=20&offset=0
```

Response:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "6e2c7e16-c197-4a69-a6c4-820aef04d997",
        "tenant_id": "43a1e937-0ef2-4725-97b6-7f016eea55ff",
        "business_id": "15ecf8ed-b88d-495b-99d6-845d6cc6fdb3",
        "customer_id": "bf9bda63-0d8e-4cf9-857d-278a72462201",
        "conversation_id": "b62cfe3c-7b7e-4dd3-9c91-2eb35d2de901",
        "service_requested": "Barbershop appointment",
        "preferred_date": "2026-05-22",
        "preferred_time": "14:00:00",
        "status": "new",
        "priority": "normal",
        "source_channel": "whatsapp",
        "ai_summary": "Customer wants to book a haircut tomorrow.",
        "created_at": "2026-05-21T10:00:00Z"
      }
    ],
    "limit": 20,
    "offset": 0
  }
}
```

---

## GET /api/v1/leads/{lead_id}

Purpose:

Return one lead.

Authentication:

```text
admin/internal required
```

Response:

```json
{
  "success": true,
  "data": {
    "id": "6e2c7e16-c197-4a69-a6c4-820aef04d997",
    "status": "new",
    "service_requested": "Barbershop appointment",
    "customer_note": "Customer prefers tomorrow afternoon."
  }
}
```

---

## PATCH /api/v1/leads/{lead_id}

Purpose:

Update lead status or details.

Authentication:

```text
admin/internal required
```

Request:

```json
{
  "status": "contacted",
  "priority": "high",
  "customer_note": "Owner called the customer."
}
```

Response:

```json
{
  "success": true,
  "data": {
    "id": "6e2c7e16-c197-4a69-a6c4-820aef04d997",
    "status": "contacted",
    "priority": "high"
  }
}
```

---

# 10. Conversation Endpoints

## GET /api/v1/conversations/{conversation_id}

Purpose:

Return conversation details and recent messages.

Authentication:

```text
admin/internal required
```

Response:

```json
{
  "success": true,
  "data": {
    "id": "b62cfe3c-7b7e-4dd3-9c91-2eb35d2de901",
    "tenant_id": "43a1e937-0ef2-4725-97b6-7f016eea55ff",
    "business_id": "15ecf8ed-b88d-495b-99d6-845d6cc6fdb3",
    "customer_id": "bf9bda63-0d8e-4cf9-857d-278a72462201",
    "channel": "whatsapp",
    "status": "open",
    "messages": [
      {
        "id": "fa91a6ad-c5f1-4e58-9793-70d0f11e8128",
        "sender_type": "customer",
        "message_text": "Hello, can I book an appointment tomorrow?",
        "created_at": "2026-05-21T10:00:00Z"
      },
      {
        "id": "117370a4-b0e2-4fdb-849b-4307de26a725",
        "sender_type": "ai",
        "message_text": "Hello! Sure. What service would you like to book and what time works best for you?",
        "created_at": "2026-05-21T10:00:03Z"
      }
    ]
  }
}
```

---

# 11. Customer Endpoints

## GET /api/v1/customers

Purpose:

Return customers.

Authentication:

```text
admin/internal required
```

Query parameters:

```text
tenant_id
business_id
phone
limit
offset
```

Response:

```json
{
  "success": true,
  "data": {
    "items": [],
    "limit": 20,
    "offset": 0
  }
}
```

---

## GET /api/v1/customers/{customer_id}

Purpose:

Return customer details.

Authentication:

```text
admin/internal required
```

---

# 12. Tenant Endpoints

## POST /api/v1/tenants

Purpose:

Create tenant account.

Authentication:

```text
admin/internal required
```

Request:

```json
{
  "name": "Demo Tenant",
  "slug": "demo-tenant",
  "email": "owner@example.com",
  "phone": "+41790000000"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "id": "43a1e937-0ef2-4725-97b6-7f016eea55ff",
    "name": "Demo Tenant",
    "slug": "demo-tenant",
    "status": "active"
  }
}
```

---

## GET /api/v1/tenants/{tenant_id}

Purpose:

Return tenant details.

Authentication:

```text
admin/internal required
```

---

# 13. Error Codes

Common error codes:

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
ADAPTER_INGRESS_CONTAINED
RATE_LIMIT_EXCEEDED
SPAM_THROTTLED
SPAM_CONTAINED
```

Example:

```json
{
  "success": false,
  "error": {
    "code": "BUSINESS_NOT_FOUND",
    "message": "Business was not found for external_id demo_barbershop_001"
  }
}
```

---

# 14. MVP Required Endpoints

For MVP, the required endpoints are:

```text
GET /api/v1/health
POST /api/v1/webhook/message
POST /api/v1/tenants
POST /api/v1/businesses
GET /api/v1/businesses/{business_id}
GET /api/v1/leads
GET /api/v1/conversations/{conversation_id}
```

Other endpoints can be added after MVP core flow works.

---

# 15. Not Required In MVP

The MVP API does not require:

- full user authentication;
- payment endpoints;
- subscription endpoints;
- frontend dashboard endpoints;
- file upload endpoints;
- voice endpoints;
- analytics endpoints;
- public customer API;
- complex role-based permissions.

---

# 16. API Success Criteria

The API is successful if:

- n8n can send normalized messages to backend;
- backend can return a structured response;
- leads can be queried;
- conversations can be queried;
- businesses can be created;
- tenant isolation is respected;
- responses are predictable;
- errors are structured;
- future dashboard can reuse the same API.