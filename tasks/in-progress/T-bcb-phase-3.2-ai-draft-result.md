# T-bcb-phase-3.2-ai-draft-result

## Goal

Implement AI draft result generation when a Business Context Builder session is completed.

## Scope

- Extend the BCB prompt service with a final draft result prompt.
- Extend the BCB AI service with `generate_draft_result(...)`.
- Wire draft result generation into `complete_session()`.
- Keep fallback draft generation when AI is disabled, unavailable, or fails.
- Store draft output in `business_context_builder.results`.
- Add/update focused prompt, AI service, business service, and API tests.

## Out Of Scope

- Telegram Mini App.
- n8n integration.
- CRM attachment.
- Assistant publishing.
- Prompt publishing.
- File generation.
- External foreign keys.
- Public schema changes.
- New API version, backend service, or public port.

## Tests

- Prompt service final draft prompt constraints and history inclusion.
- AI service success, disabled, missing config, and gateway failure fallback.
- Business service stores AI draft and fallback draft on completion.
- Completion rejects completed/cancelled sessions.
- Completion does not call next-question AI.
- API completion returns generated draft result.
- Retrieval returns `result: null` before completion and stored result after completion.
