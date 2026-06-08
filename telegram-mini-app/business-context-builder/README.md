# Business Context Builder Telegram Mini App

Static Telegram Mini App UI for the Business Context Builder interview flow.

## Files

- `index.html` — Mini App shell.
- `styles.css` — responsive Telegram-safe layout and theme variables.
- `src/app.js` — screen state and UI behavior.
- `src/apiClient.js` — isolated BCB API adapter.

## Local Run

From this directory:

```bash
python3 -m http.server 5174
```

Open:

```text
http://127.0.0.1:5174/
```

Optional preview parameters:

```text
?api_mode=mock
?api_mode=bridge&api_base_url=https://backend.example
```

## Current Behavior

- Uses the mock API adapter by default.
- Supports `api_mode=bridge` for Telegram runtime calls through the backend bridge.
- Initializes `window.Telegram.WebApp` when the Telegram SDK is available.
- Applies Telegram theme colors when running inside Telegram.
- Works in a normal browser for local preview.
- Does not expose backend internal tokens.

## Bridge API Contract

Bridge mode uses:

- `POST /api/v1/telegram-mini-app/business-context-builder/auth/session`
- `POST /api/v1/telegram-mini-app/business-context-builder/sessions`
- `POST /api/v1/telegram-mini-app/business-context-builder/sessions/{session_id}/messages`
- `GET /api/v1/telegram-mini-app/business-context-builder/sessions/{session_id}`
- `POST /api/v1/telegram-mini-app/business-context-builder/sessions/{session_id}/complete`
- `GET /api/v1/telegram-mini-app/business-context-builder/contexts`

All bridge requests send Telegram `initData` to the backend. Operational
requests use the `X-Telegram-Init-Data` header. The frontend does not send
tenant or business identifiers in bridge mode.

## Backend Env

Required for bridge mode:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_INITDATA_MAX_AGE_SECONDS`
- `BCB_TELEGRAM_TENANT_ID`
- `BCB_TELEGRAM_BUSINESS_ID`

The bot token is backend-only. Do not add it to this directory or any frontend
deployment config.

## Telegram Setup Notes

Bridge mode requires real Telegram `window.Telegram.WebApp.initData`, so it must
be tested inside Telegram after the Mini App is served over HTTPS.

BotFather Mini App URL setup should happen only after HTTPS deployment. Local
browser development should use `api_mode=mock`.

## Not Implemented

- Telegram bot messaging logic.
- n8n integration.
- CRM integration.
- Production assistant publishing.
- File generation.
- Direct internal-token BCB API calls from the browser.
