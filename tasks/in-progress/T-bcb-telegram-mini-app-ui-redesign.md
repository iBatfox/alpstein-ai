# T-bcb-telegram-mini-app-ui-redesign

## Goal

Redesign the Business Context Builder Telegram Mini App as a polished mobile AI chat/interview interface.

## Scope

- Update only the static frontend files for the Mini App.
- Preserve the existing HTML, CSS, and vanilla JavaScript structure.
- Improve header, step status, progress bar and dots, chat feed, assistant/user bubbles, sticky input, completion action, loading/error states, and empty contexts UI.
- Respect Telegram theme params where practical.
- Keep mock mode and bridge mode.

## Out Of Scope

- React, Vite, or a new frontend build system.
- Backend code changes.
- Backend route changes.
- nginx, Docker, database, n8n, CRM, assistant publishing, or production assistant writes.
- Bridge auth logic changes or frontend secrets.

## Checks

- `node --check telegram-mini-app/business-context-builder/src/app.js`
- `node --check telegram-mini-app/business-context-builder/src/apiClient.js`
- `git diff --check`
- Manual browser verification at `https://alpstein-ai.ch/telegram-context/?api_mode=mock`
