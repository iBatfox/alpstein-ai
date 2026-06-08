# T-bcb-phase-3.3-ai-traceability

## Goal

Add Business Context Builder AI traceability and prompt versioning for reproducible AI behavior.

## Scope

- Add prompt version constants for next-question and draft-result prompts.
- Add a lightweight AI trace object for provider, model, prompt version, fallback, latency, and token metadata.
- Persist draft generation metadata inside `business_context_builder.results` using existing JSONB storage.
- Extend structured logs for next-question and draft-result operations with prompt version and trace metadata.
- Add tests for prompt version exposure, metadata persistence, fallback metadata, mocked gateway metadata propagation, and no production assistant writes.

## Out Of Scope

- Telegram Mini App.
- n8n integration.
- CRM integration.
- Assistant publishing.
- File generation.
- New backend service or public port.
- External foreign keys.
- Production assistant table writes.

## Tests

- Prompt versions exposed correctly.
- Generated result stores AI metadata.
- Fallback result stores fallback metadata.
- Mocked gateway metadata propagates into draft result.
- No real OpenAI call required.
- Production assistant tables are not used.
