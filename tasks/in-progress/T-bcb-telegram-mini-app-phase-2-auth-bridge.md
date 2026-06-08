# T-bcb-telegram-mini-app-phase-2-auth-bridge

## Status

In progress

## Scope

Implement a secure backend auth bridge for the Business Context Builder Telegram Mini App.

## Requirements

- Validate Telegram Mini App `initData` server-side.
- Keep Telegram bot token and internal webhook token out of frontend code.
- Resolve BCB `tenant_id` and `business_id` from backend settings.
- Add bridge routes under `/api/v1/telegram-mini-app/business-context-builder`.
- Reuse existing Business Context Builder service and schemas.
- Keep BCB database schema unchanged.
- Do not add n8n, CRM, production assistant publishing, file generation, external FK, or new public ports.

## Verification

- Backend auth service tests.
- Backend bridge route tests.
- Frontend JavaScript syntax checks.
- Mock mode remains available for local browser development.
