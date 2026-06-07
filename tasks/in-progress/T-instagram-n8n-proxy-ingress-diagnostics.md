# T-instagram-n8n-proxy-ingress-diagnostics

## Goal

Safely restore and verify Instagram ingress through n8n without changing working Telegram or backend AI flow.

## Scope

- Check Docker Compose and n8n env for reverse proxy settings.
- Add or verify `N8N_PROXY_HOPS=1` when appropriate for the current n8n version.
- Verify n8n can receive external webhook calls behind nginx without the `X-Forwarded-For` trust proxy error.
- Verify the Instagram webhook path is active in production mode:
  `/webhook/alpstein/unified-customer-ingress/instagram/incoming`
- Provide exact operational commands for n8n recreate, env checks, logs, webhook registration, and backend Instagram log checks.

## Requirements

- Do not refactor code.
- Do not modify Telegram flow.
- Do not change AI orchestration, OpenAI, ERPNext, CRM sync, or backend webhook logic.
- Do not print or commit secrets.
- If the issue is Meta webhook subscription/permissions rather than n8n, stop and report clearly.

## Tests

- Render Docker Compose config for n8n environment.
- Inspect n8n runtime env and logs after recreate.
- Inspect n8n workflow registration safely.

## Out Of Scope

- Workflow logic changes.
- Telegram workflow changes.
- Backend service changes.
- Meta app permission or subscription mutation.
