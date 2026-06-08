# Meta webhook setup

**Scope:** Backend verification + raw intake only (`GET/POST /webhooks/meta`) for Meta channels. Instagram DM events persist in the backend first, then dispatch to n8n unified customer ingress. No outbound WhatsApp on this route yet.

**Meta App:** `app_alpstein_ai`

---

## Environment variables

Set in `backend/.env` (unprefixed — see `backend/.env.example`):

| Variable | Purpose |
|----------|---------|
| `META_VERIFY_TOKEN` | Shared secret for Meta webhook verification handshake |
| `WHATSAPP_PHONE_NUMBER_ID` | Cloud API phone number ID (future outbound / routing) |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | WhatsApp Business Account ID |
| `WHATSAPP_ACCESS_TOKEN` | Graph API access token (**never log or commit**) |

Restart backend after changing env.

---

## Meta Developer Console

1. Open [Meta for Developers](https://developers.facebook.com/) → **app_alpstein_ai** → **WhatsApp** → **Configuration** (or **Webhooks**).
2. **Callback URL:**

   ```text
   https://api.alpstein-ai.ch/webhooks/meta
   ```

3. **Verify token:** exact value of `META_VERIFY_TOKEN` from `backend/.env`.
4. Click **Verify and save**. Meta sends:

   ```http
   GET /webhooks/meta?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
   ```

   Backend returns `hub.challenge` as **plain text** with HTTP **200** when token and mode match.

5. Subscribe to webhook fields as needed (e.g. `messages` for inbound customer messages).

**Local / staging:** expose the backend with HTTPS (Meta requires a public HTTPS URL). Use your staging API host instead of production if testing first.

---

## Production nginx route

Meta calls the public backend callback URL:

```text
https://api.alpstein-ai.ch/webhooks/meta
```

On the production host, nginx must proxy the exact path `/webhooks/meta` to the backend loopback upstream:

```nginx
location = /webhooks/meta {
    proxy_pass http://127.0.0.1:18081;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

The backend loopback port comes from the Docker Compose host binding:

```text
127.0.0.1:18081:8000
```

A stale upstream such as `http://127.0.0.1:8000` for `api.alpstein-ai.ch/webhooks/meta` causes public Meta deliveries to fail with nginx `502 Bad Gateway` when nothing is listening on host port `8000`.

The Instagram n8n ingress URL remains separate and unchanged:

```text
https://n8n.alpstein-ai.ch/webhook/alpstein/unified-customer-ingress/instagram/incoming
```

Flow:

```text
Meta -> https://api.alpstein-ai.ch/webhooks/meta
     -> nginx exact /webhooks/meta -> http://127.0.0.1:18081
     -> backend persists Instagram DM
     -> backend dispatches normalized event to n8n Instagram ingress URL
     -> n8n calls backend POST /api/v1/webhook/message
```

---

## Backend behaviour

| Method | Path | Behaviour |
|--------|------|-----------|
| `GET` | `/webhooks/meta` | Meta verification; `403` on mismatch |
| `POST` | `/webhooks/meta` | Accept JSON event; log safe metadata; `200 {"status":"received"}` |

Does **not** replace n8n normalized ingress (`POST /api/v1/webhook/message`). Instagram uses this route only for Meta delivery and backend persistence before backend-to-n8n dispatch. WhatsApp business processing will be wired in a later slice (normalization in n8n, SoT in PostgreSQL).

---

## Verification

Validate nginx syntax before reload:

```bash
nginx -t
```

Safe public POST probe for the Meta callback route:

```bash
curl -sS -i --max-time 15 \
  -X POST "https://api.alpstein-ai.ch/webhooks/meta" \
  -H "Content-Type: application/json" \
  -d '{"object":"instagram","entry":[]}'
```

Expected: HTTP 200 with `{"status":"received"}`. This validates public nginx routing without sending a real customer message.

Check backend logs for Instagram processing:

```bash
docker logs --since 10m alpstein_backend 2>&1 \
  | rg -i "instagram|channel=instagram|POST /api/v1/webhook/message|/webhooks/meta"
```

For a real Instagram DM, expect:

- public nginx access log: `POST /webhooks/meta` returns 200;
- backend log: Instagram ingress accepted or safe Instagram diagnostic;
- public/internal n8n access: `POST /webhook/alpstein/unified-customer-ingress/instagram/incoming` returns 200;
- backend log from n8n: `POST /api/v1/webhook/message` returns 200 and includes `channel=instagram` or equivalent Instagram prompt/flow diagnostics;
- n8n execution starts in workflow `alpstein-customer-ingress`.

Check n8n execution in the n8n UI or with the existing workflow/execution inspection procedure for `alpstein-customer-ingress` (`aYrRmAGKhP4TJbG9`).

### Local curl

Replace `YOUR_VERIFY_TOKEN` and run while backend listens. Inside the backend container the service listens on port `8000`; on the production host, use the compose loopback binding `127.0.0.1:18081`.

Container-local example:

```bash
curl -sS -G "http://127.0.0.1:8000/webhooks/meta" \
  --data-urlencode "hub.mode=subscribe" \
  --data-urlencode "hub.verify_token=YOUR_VERIFY_TOKEN" \
  --data-urlencode "hub.challenge=1158201444"
```

Expected: HTTP 200, body `1158201444` (plain text).

Production-host example:

```bash
curl -sS -G "http://127.0.0.1:18081/webhooks/meta" \
  --data-urlencode "hub.mode=subscribe" \
  --data-urlencode "hub.verify_token=YOUR_VERIFY_TOKEN" \
  --data-urlencode "hub.challenge=1158201444"
```

Sample POST intake:

```bash
curl -sS -X POST "http://127.0.0.1:8000/webhooks/meta" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "WABA_ID",
      "changes": [{
        "field": "messages",
        "value": {
          "messaging_product": "whatsapp",
          "metadata": {
            "display_phone_number": "15550001111",
            "phone_number_id": "PHONE_NUMBER_ID"
          },
          "messages": [{
            "from": "15551234567",
            "id": "wamid.HBgL...",
            "timestamp": "1520383572",
            "text": { "body": "Hello" },
            "type": "text"
          }]
        }
      }]
    }]
  }'
```

Expected: HTTP 200, `{"status":"received"}`.

---

## Instagram outbound note

If Instagram inbound reaches backend and n8n, but a customer reply fails, inspect backend Instagram outbound logs and Meta error codes without printing access tokens. Meta error code `100` with subcode `2534014` can be recipient-specific when other Instagram outbound sends succeed; treat that as evidence to investigate the specific recipient/account conversation or Meta permission state rather than a global nginx/n8n ingress failure.

---

## Security notes

- Do not log `META_VERIFY_TOKEN`, `WHATSAPP_ACCESS_TOKEN`, or `X-Hub-Signature-256` values.
- `X-Hub-Signature-256` validation is **not** implemented in this slice — add before production traffic if required by your security policy.
- Existing Telegram / Website paths via n8n and `POST /api/v1/webhook/message` are unchanged.

---

## Tests

From `backend/`:

```bash
pytest tests/test_meta_webhook.py -q
```
