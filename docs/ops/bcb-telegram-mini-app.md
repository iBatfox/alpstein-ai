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
- Sticky bottom navigation for Language, Contexts, Interview, Bots, and More.
- Frontend language selection persisted as `bcb_language`.
- Bots tab UI foundation with mock cards and bridge not-implemented state.
- Backend bridge routes under `/api/v1/telegram-mini-app/business-context-builder`.
- Server-side Telegram `initData` validation.
- Owner-only bridge access through `TELEGRAM_MINI_APP_ALLOWED_USER_IDS`.
- Server-side BCB tenant/business scope resolution.

## Intentionally Not Implemented

- n8n integration.
- CRM integration.
- Production assistant publishing.
- File generation.
- Backend schema changes.
- New public ports or backend services.
- Telegram bot messaging logic.
- Backend bot listing API.
- Backend language-aware BCB question/result generation.

## Local Run

```bash
cd telegram-mini-app/business-context-builder
python3 -m http.server 5174
```

Open:

```text
http://127.0.0.1:5174/
```

## HTTPS Deployment

Production URL:

```text
https://alpstein-ai.ch/telegram-context
```

Canonical browser URL after nginx redirect:

```text
https://alpstein-ai.ch/telegram-context/
```

Host static directory:

```text
/var/www/alpstein-ai/telegram-context/
```

Deployed files:

- `index.html`
- `styles.css`
- `src/app.js`
- `src/apiClient.js`

Deployment command from the repo:

```bash
sudo install -d -m 0755 /var/www/alpstein-ai/telegram-context/src
sudo install -m 0644 telegram-mini-app/business-context-builder/index.html /var/www/alpstein-ai/telegram-context/index.html
sudo install -m 0644 telegram-mini-app/business-context-builder/styles.css /var/www/alpstein-ai/telegram-context/styles.css
sudo install -m 0644 telegram-mini-app/business-context-builder/src/app.js /var/www/alpstein-ai/telegram-context/src/app.js
sudo install -m 0644 telegram-mini-app/business-context-builder/src/apiClient.js /var/www/alpstein-ai/telegram-context/src/apiClient.js
```

## Nginx

Live site config:

```text
/etc/nginx/sites-available/default
```

The `alpstein-ai.ch` HTTPS server contains:

```nginx
location = /telegram-context {
    return 301 /telegram-context/;
}

location ^~ /telegram-context/ {
    alias /var/www/alpstein-ai/telegram-context/;
    index index.html;
    try_files $uri $uri/ /telegram-context/index.html;
    add_header Cache-Control "no-store" always;
    add_header X-Content-Type-Options "nosniff" always;
}

location ^~ /api/v1/telegram-mini-app/business-context-builder/ {
    proxy_pass http://127.0.0.1:18081;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

No new public ports are required; nginx continues to use existing `80/443`.
The backend compose service binds `127.0.0.1:18081:8000` for host nginx only.
Do not use `0.0.0.0:8000:8000` or expose the backend directly.

Reload after edits:

```bash
sudo nginx -t
sudo systemctl reload nginx
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

On production, bridge mode should use the same-origin nginx bridge proxy:

```text
https://alpstein-ai.ch/telegram-context/?api_mode=bridge
```

If the backend is not on the same origin, pass:

```text
api_base_url=https://<backend-host>
```

Bridge mode reads `window.Telegram.WebApp.initData` and sends it to the backend.
It does not send the internal webhook token and does not send tenant/business
identifiers.

If the backend returns `403` with `TELEGRAM_USER_NOT_ALLOWED`, the frontend shows
only the restricted-access screen and hides contexts/interview/bots navigation.

## Language

Supported frontend languages:

- English `en`
- Deutsch `de`
- Français `fr`
- Українська `uk`

Selection is stored in browser storage as:

```text
bcb_language
```

Mock mode uses the selected language for static questions. Bridge mode keeps the
selected language frontend-only because the BCB bridge/backend does not yet have
a safe language parameter.

## Bots Tab

The Bots tab is a UI foundation.

- Mock mode returns local sample bot cards.
- Bridge mode returns a clear “not implemented yet” state because no backend bot
  listing API exists in this scope.
- Create bot and Link context are disabled/coming soon.

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
TELEGRAM_MINI_APP_ALLOWED_USER_IDS=
BCB_TELEGRAM_TENANT_ID=
BCB_TELEGRAM_BUSINESS_ID=
```

The BCB scope values are UUIDs. They are not accepted from the frontend and are
not validated through public schema foreign keys.

`TELEGRAM_MINI_APP_ALLOWED_USER_IDS` is a comma-separated list of numeric
Telegram user IDs, for example:

```text
TELEGRAM_MINI_APP_ALLOWED_USER_IDS=123456789,987654321
```

Empty allowlist denies access. This is the safest default for production.

To find a Telegram user ID, use a trusted Telegram ID lookup bot or a temporary
operator-only diagnostic outside the frontend. Do not commit Telegram user IDs,
bot tokens, or internal webhook tokens into frontend files.

## Telegram HTTPS Setup

Telegram supplies trusted `initData` only inside the Mini App runtime. Test
bridge mode in Telegram after the Mini App is served over HTTPS.

BotFather Mini App URL setup should happen only after HTTPS deployment. Use
`api_mode=mock` for local browser development before that.

Use this Mini App URL in BotFather:

```text
https://alpstein-ai.ch/telegram-context/
```

## Verification

Static HTTPS checks:

```bash
curl -I https://alpstein-ai.ch/telegram-context
curl -I https://alpstein-ai.ch/telegram-context/
curl -I https://alpstein-ai.ch/telegram-context/styles.css
curl -I https://alpstein-ai.ch/telegram-context/src/app.js
curl -I https://alpstein-ai.ch/telegram-context/src/apiClient.js
```

Expected:

- `/telegram-context` returns `301` to `/telegram-context/`.
- `/telegram-context/` returns `200 text/html`.
- CSS returns `200 text/css`.
- JS modules return `200 application/javascript`.

Bridge readiness check:

```bash
curl -i https://alpstein-ai.ch/api/v1/telegram-mini-app/business-context-builder/contexts
```

Expected once the backend bridge code is deployed: a project-style auth error
for missing Telegram `initData`, not an internal token error. If the live backend
returns `404`, nginx is reaching backend but the running backend image/process
does not yet include the Phase 2 bridge routes.

Host upstream readiness check:

```bash
curl -i http://127.0.0.1:18081/api/v1/health/ready
```

Expected:

- `200 OK` when the backend container is healthy.
- Loopback-only binding visible as `127.0.0.1:18081->8000/tcp` in `docker compose ps`.

## Security Notes

- `TELEGRAM_BOT_TOKEN` stays on the backend.
- `TELEGRAM_MINI_APP_ALLOWED_USER_IDS` stays on the backend.
- `N8N_BACKEND_API_TOKEN` stays out of frontend code.
- Expired and invalid-signature `initData` are rejected by the backend.
- Allowed-user enforcement happens after `initData` validation and before BCB
  service access.
- BCB access is scoped by backend-configured `BCB_TELEGRAM_TENANT_ID` and
  `BCB_TELEGRAM_BUSINESS_ID`.
- The bridge reuses BCB service methods and does not write to production
  assistant tables.
