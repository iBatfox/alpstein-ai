# T-langfuse-compose-env-enable

## Goal

Enable Langfuse tracing through backend environment configuration only.

## Scope

- Check Docker Compose backend environment loading.
- Ensure backend can receive:
  - `LANGFUSE_PUBLIC_KEY`
  - `LANGFUSE_SECRET_KEY`
  - `LANGFUSE_HOST`
  - `LANGFUSE_TRACING_ENABLED=true`
- Preserve any existing `LANGFUSE_BASE_URL` usage by mapping or documenting that backend runtime expects `LANGFUSE_HOST`.
- Update env examples/docs only as needed.

## Requirements

- Do not commit real Langfuse keys.
- Do not change AI orchestration, prompt building, OpenAI gateway, n8n workflows, webhook logic, CRM/ERP sync, or working integrations.
- Do not change `LangfuseTracingService` unless absolutely necessary.
- Keep this as a configuration task, not a refactor.

## Tests

- Validate Docker Compose config renders backend Langfuse environment variables.
- Run targeted Langfuse tracing tests if the local test environment is available.

## Out Of Scope

- Runtime tracing logic changes.
- AI prompt/gateway/orchestration changes.
- n8n workflow changes.
- Live Langfuse key disclosure or secret storage.
