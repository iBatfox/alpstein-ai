# T-bcb-backend-hardening

## Goal

Harden the isolated Business Context Builder backend MVP lifecycle.

## Scope

- Persist and advance `sessions.current_step`.
- Use the allowed session statuses `active`, `completed`, and `cancelled`.
- Reject invalid lifecycle states and invalid status transitions.
- Reject message writes to completed or cancelled sessions.
- Keep unfinished sessions retrievable and continuable.
- Keep context listing paginated with `limit` and `offset`.
- Keep all Business Context Builder routes under `/api/v1/business-context-builder`.
- Keep Business Context Builder storage isolated in the `business_context_builder` schema.

## Out Of Scope

- AI or OpenAI integration.
- n8n integration.
- CRM integration.
- Telegram Mini App logic.
- File generation.
- Publishing to production assistants.
- Writes to production assistant tables.
- Public-schema foreign keys from Business Context Builder tables.

## Tests

- Business Context Builder service tests.
- Business Context Builder API tests.
- Model metadata tests.
- Alembic migration tests for Business Context Builder changes.
