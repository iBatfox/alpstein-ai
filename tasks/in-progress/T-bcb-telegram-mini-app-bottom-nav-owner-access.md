# T-bcb-telegram-mini-app-bottom-nav-owner-access

## Status

In progress

## Scope

Add bottom navigation, language selection, Bots tab UI foundation, and owner-only
Telegram Mini App bridge access for Business Context Builder.

## Requirements

- Keep static vanilla HTML/CSS/JS.
- Add bottom tabs: Language, Contexts, Interview, Bots, More.
- Store selected language in `localStorage` as `bcb_language`.
- Keep language frontend-only until backend language support exists.
- Add mock Bots tab data and bridge placeholder state.
- Add backend-only `TELEGRAM_MINI_APP_ALLOWED_USER_IDS` allowlist.
- Reject non-allowed Telegram users before BCB service access.
- Do not expose secrets or allowed user IDs in frontend.
- Do not add CRM, n8n, production assistant publishing, OAuth, email login, schema changes, or new public ports.

## Verification

- Backend bridge tests for allowlist behavior.
- Frontend JS syntax checks.
- `git diff --check`.
- Manual/mock static checks.
