# T-bcb-api-docs

## Goal

Document the Business Context Builder API and curl examples for local/internal use.

## Scope

- Create or update `docs/api/business-context-builder.md`.
- Document endpoint purpose, auth, bodies, responses, errors, and curl examples.
- Include the full happy-path curl sequence.
- Include documented error examples and AI fallback notes.
- Update project-status docs if required by project convention.

## Requirements

- Documentation only.
- Use base path `/api/v1/business-context-builder`.
- Document feature flags `BCB_AI_ENABLED` and `BCB_AI_DRAFT_ENABLED`.
- Preserve isolation rules for `business_context_builder` schema and draft-only results.
- Stop before commit.

## Out Of Scope

- Application features.
- Telegram Mini App.
- n8n integration.
- CRM integration.
- Production assistant publishing.
- Database schema changes.
- Alembic migrations.
- Backend tests unless code changes.

## Done When

- API guide exists with endpoint and curl examples.
- Project status docs are synchronized if needed.
- No application code is changed.
