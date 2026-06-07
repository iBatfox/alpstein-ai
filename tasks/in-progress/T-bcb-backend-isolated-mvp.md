# T-bcb-backend-isolated-mvp

## Goal

Implement the first isolated backend version of Business Context Builder.

## Scope

- Add isolated SQLAlchemy models for Business Context Builder sessions, messages, and results.
- Add an Alembic revision creating only the `business_context_builder` schema and MVP tables.
- Add Pydantic API schemas.
- Add service methods for session creation, message storage, deterministic placeholder replies, session retrieval, completion, and context listing.
- Add FastAPI routes under `/api/v1/business-context-builder`.
- Register the route in the existing backend app.
- Add focused tests for schema isolation, migration source, lifecycle behavior, tenant/business scoping, and production assistant isolation.

## Out Of Scope

- OpenAI or AI Gateway integration.
- n8n integration.
- CRM attachment.
- Telegram Mini App logic.
- File generation.
- Publishing to production assistant.
- Writes to production assistant tables.
- New public ports or separate backend services.

## Tests

- Model metadata uses schema `business_context_builder`.
- Migration source creates schema and three tables.
- Session creation stores a session and first assistant message.
- User message stores user and assistant placeholder messages.
- Session retrieval returns session and messages.
- Completion creates one draft result.
- Context listing is scoped by `tenant_id` and `business_id`.
- Service queries are tenant/business scoped.
- Production assistant tables are not used.
