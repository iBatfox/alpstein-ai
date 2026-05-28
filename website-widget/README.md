# Website Chat Widget (E1.6 MVP)

Minimal embeddable widget for Website Chat MVP runtime path:

Widget -> n8n Website Chat webhook -> backend `POST /api/v1/webhook/message` -> n8n response -> widget render.

## Files

- `alpstein-chat-widget.js` — embeddable widget script
- `example.html` — local demo page

## Usage

```html
<script
  src="alpstein-chat-widget.js"
  data-webhook-url="https://<n8n-host>/webhook/alpstein/website-chat/incoming"
  data-business-id="alpstein_ai_demo_001"
  data-title="Alpstein Assistant"
></script>
```

Required attributes:

- `data-webhook-url` — website chat n8n webhook endpoint
- `data-business-id` — backend external business id

## MVP constraints

- Text-only messages
- Anonymous visitor/session basics only
- No attachment/media/voice support
- No account/login flows
- No cross-tab sync
