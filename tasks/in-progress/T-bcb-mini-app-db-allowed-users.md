# T-bcb-mini-app-db-allowed-users

## Status

In progress

## Goal

Implement owner-managed user verification for the Business Context Builder
Telegram Mini App.

## Scope

- Add a backend-owned allowed users table for the Mini App.
- Verify Telegram Mini App `initData` server-side.
- Check Telegram numeric user ID against active allowed users.
- Return allowed/denied access before showing the Mini App UI.
- Keep management backend-only for now via documented direct database insert.

## Requirements

- Allowed user fields: Telegram user ID, display name, company name, status,
  optional notes, created at, updated at.
- No self-registration.
- No public account creation.
- No frontend admin functions.
- Do not expose secrets in frontend.
- Do not change assistant prompt logic, prompt builder, channel integrations,
  Docker, nginx, deployment, unrelated routes, API outside the Mini App bridge,
  or database tables outside this scope.

## Verification

- Backend tests for active allowed, missing allowed user, disabled user, invalid
  initData, and missing initData.
- Frontend JS syntax checks.
