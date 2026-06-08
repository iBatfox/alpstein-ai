# Business Context Builder Telegram Mini App

## Status

Phase 1 adds a static frontend skeleton only.

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
- Isolated API client module with mock adapter.

## Intentionally Not Implemented

- Real Telegram authentication.
- Backend auth bridge.
- n8n integration.
- CRM integration.
- Production assistant publishing.
- File generation.
- Backend schema changes.
- New public ports or backend services.

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

Phase 1 uses a mock adapter by default:

```text
api_mode=mock
```

The placeholder backend adapter does not send requests because the current BCB
API uses an internal backend token. Frontend code must never include that token.

## Phase 2 Auth Bridge

Phase 2 must add a secure backend bridge before real API calls are enabled.

Required behavior:

- receive Telegram Mini App `initData`;
- validate `initData` server-side using the bot token;
- resolve tenant and business scope server-side;
- call existing BCB backend logic without exposing internal tokens;
- return only draft BCB data to the Mini App.

The bridge must not publish drafts to production assistants.
