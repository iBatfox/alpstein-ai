# T-bcb-telegram-mini-app-https-deployment

## Status

In progress

## Scope

Deploy the Business Context Builder Telegram Mini App static frontend at:

```text
https://alpstein-ai.ch/telegram-context
```

## Requirements

- Serve `index.html`, `styles.css`, `src/app.js`, and `src/apiClient.js`.
- Configure nginx/static serving on the existing HTTPS host.
- Do not expose backend secrets.
- Do not change Business Context Builder backend logic.
- Do not add ports, n8n, CRM, or production assistant publishing.
- Document deployment and verification steps.

## Verification

- HTTPS URL responds.
- Static assets load.
- Browser mock mode is available.
- Same-origin bridge path is proxied for server-side auth.
