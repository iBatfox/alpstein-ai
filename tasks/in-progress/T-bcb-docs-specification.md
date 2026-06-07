# T-bcb-docs-specification

## Goal

Prepare complete documentation for the Business Context Builder module based on existing Alpstein AI specs and Cursor rules.

## Scope

- Inspect `specs/context`.
- Inspect general `specs/` conventions.
- Inspect `.cursor` project rules.
- Create or update Business Context Builder MVP, database, flow, API, and architecture specs.
- Add a short project-level safety note if appropriate.

## Requirements

- Documentation-only.
- Follow existing spec style and architecture terminology.
- Preserve backend, n8n, AI layer, database, CRM, and Telegram Mini App boundaries.
- Document draft-only behavior and explicit publishing boundary.
- Document dedicated PostgreSQL schema `business_context_builder`.

## Out Of Scope

- FastAPI routes.
- SQLAlchemy models.
- Alembic migrations.
- Services.
- Tests.
- Production backend logic changes.

## Done When

- Required spec files exist under `specs/context`.
- API contract is documented.
- Database tables and migration rules are documented.
- Safety rules are documented in project instructions.
- No application code is modified.
