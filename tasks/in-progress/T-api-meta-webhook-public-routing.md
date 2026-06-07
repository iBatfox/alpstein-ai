# T-api-meta-webhook-public-routing

## Goal

Restore public routing for `https://api.alpstein-ai.ch/webhooks/meta` to the backend container.

## Scope

- Inspect Docker Compose backend port publishing and nginx `api.alpstein-ai.ch` upstream.
- Apply the minimal safe routing fix using the existing deployment pattern.
- Verify backend health, public API health, and Meta webhook verification.

## Requirements

- Do not modify backend application code.
- Do not modify Telegram flow.
- Do not modify AI orchestration.
- Do not modify n8n workflows.
- Keep backend host exposure loopback-only when using host port publishing.
- Do not print secrets.

## Tests

- Host curl to backend health.
- Public curl to `api.alpstein-ai.ch` health.
- Public `GET /webhooks/meta` wrong-token check no longer returns `502`.
- Public `GET /webhooks/meta` correct-token check returns the challenge.
- Confirm n8n Instagram webhook remains active.

## Rollback

Recreate backend with the base compose file only to remove the dev-overlay host port bind.
