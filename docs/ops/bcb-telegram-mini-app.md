# Business Context Builder Telegram Mini App

## Status

Phase 2 adds the secure backend bridge needed for Telegram Mini App calls to
Business Context Builder.

Location:

```text
telegram-mini-app/business-context-builder/
```

## Implemented

- Start screen with interview entry actions.
- Interview screen with chat-style messages, current step, input, send, and complete actions.
- Result screen with generated draft result and generation metadata fields.
- Contexts screen with empty state and pagination-ready layout.
- Telegram WebApp SDK initialization when available.
- Telegram theme parameter support through CSS variables.
- Browser preview without Telegram.
- Isolated API client module with mock and bridge adapters.
- Backend bridge routes under `/api/v1/telegram-mini-app/business-context-builder`.
- Server-side Telegram `initData` validation.
- Server-side BCB tenant/business scope resolution.

## Intentionally Not Implemented

- n8n integration.
- CRM integration.
- Production assistant publishing.
- File generation.
- Backend schema changes.
- New public ports or backend services.
- Telegram bot messaging logic.

## Local Run

```bash
cd telegram-mini-app/business-context-builder
python3 -m http.server 5174
```

Open:

```text
http://127.0.0.1:5174/
```

## API Adapter

Local browser preview uses a mock adapter by default:

```text
api_mode=mock
```

Telegram runtime can use bridge mode:

```text
api_mode=bridge
```

If the backend is not on the same origin, pass:

```text
api_base_url=https://<backend-host>
```

Bridge mode reads `window.Telegram.WebApp.initData` and sends it to the backend.
It does not send the internal webhook token and does not send tenant/business
identifiers.

## Backend Bridge

Namespace:

```text
/api/v1/telegram-mini-app/business-context-builder
```

Endpoints:

- `POST /auth/session`
- `POST /sessions`
- `POST /sessions/{session_id}/messages`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/complete`
- `GET /contexts`

Operational endpoints require the `X-Telegram-Init-Data` header.

Required behavior:

- receive Telegram Mini App `initData`;
- validate `initData` server-side using the bot token;
- resolve tenant and business scope server-side;
- call existing BCB backend service without exposing internal tokens;
- return only draft BCB data to the Mini App.

The bridge must not publish drafts to production assistants.

## Backend Env

Set on the backend only:

```text
TELEGRAM_BOT_TOKEN=
TELEGRAM_INITDATA_MAX_AGE_SECONDS=86400
BCB_TELEGRAM_TENANT_ID=
BCB_TELEGRAM_BUSINESS_ID=
```

The BCB scope values are UUIDs. They are not accepted from the frontend and are
not validated through public schema foreign keys.

## Telegram HTTPS Setup

Telegram supplies trusted `initData` only inside the Mini App runtime. Test
bridge mode in Telegram after the Mini App is served over HTTPS.

BotFather Mini App URL setup should happen only after HTTPS deployment. Use
`api_mode=mock` for local browser development before that.

## Security Notes

- `TELEGRAM_BOT_TOKEN` stays on the backend.
- `N8N_BACKEND_API_TOKEN` stays out of frontend code.
- Expired and invalid-signature `initData` are rejected by the backend.
- BCB access is scoped by backend-configured `BCB_TELEGRAM_TENANT_ID` and
  `BCB_TELEGRAM_BUSINESS_ID`.
- The bridge reuses BCB service methods and does not write to production
  assistant tables.
