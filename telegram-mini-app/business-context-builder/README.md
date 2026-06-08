# Business Context Builder Telegram Mini App

Static Phase 1 UI skeleton for the Business Context Builder interview flow.

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
?tenant_id=<uuid>&business_id=<uuid>&api_mode=mock
```

## Phase 1 Behavior

- Uses the mock API adapter by default.
- Initializes `window.Telegram.WebApp` when the Telegram SDK is available.
- Applies Telegram theme colors when running inside Telegram.
- Works in a normal browser for local preview.
- Does not expose backend internal tokens.

## Backend API Contract

The future real adapter must use the existing BCB endpoints:

- `POST /api/v1/business-context-builder/sessions`
- `POST /api/v1/business-context-builder/sessions/{session_id}/messages`
- `GET /api/v1/business-context-builder/sessions/{session_id}`
- `POST /api/v1/business-context-builder/sessions/{session_id}/complete`
- `GET /api/v1/business-context-builder/contexts`

## Phase 2 Requirement

The current BCB backend API is protected by an internal token. That token must
not be shipped to the Mini App. Phase 2 needs a secure backend auth bridge that:

- validates Telegram `initData` server-side;
- maps the Telegram user/session to tenant and business scope;
- calls the internal BCB API or service from the backend;
- returns only safe draft data to the Mini App.

Until that bridge exists, `api_mode=backend` intentionally fails in the browser.
