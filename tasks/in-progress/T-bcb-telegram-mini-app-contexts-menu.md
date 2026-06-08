# T-bcb-telegram-mini-app-contexts-menu

## Goal

Add a Business Contexts menu to the Telegram Mini App before the interview flow.

## Scope

- Frontend-only changes to the static Telegram Mini App.
- Show a main Business Contexts screen on load.
- Allow creating a new context interview.
- Store and continue one unfinished local session id.
- List existing draft contexts through the existing client API.
- Allow returning from interview and result screens to the contexts menu.
- Add a compact header menu with enabled navigation items and disabled placeholders for future language/edit behavior.
- Keep mock and bridge API modes.

## Out Of Scope

- Language selection behavior.
- Google, GitHub, email, or other authentication.
- Editing saved contexts.
- Adaptive AI questioning.
- CRM, n8n, publishing, backend schema changes, new backend routes, nginx, Docker, or database changes.

## Checks

- `node --check telegram-mini-app/business-context-builder/src/app.js`
- `node --check telegram-mini-app/business-context-builder/src/apiClient.js`
- `git diff --check`
- Sync static files to `/var/www/alpstein-ai/telegram-context/`.
- Verify live page and assets return 200 and include contexts menu markers.
