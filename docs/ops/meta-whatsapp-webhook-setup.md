# Meta / WhatsApp Cloud API webhook setup

**Scope:** Backend verification + raw intake only (`GET/POST /webhooks/meta`). No AI, no outbound WhatsApp on this route yet.

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

## Backend behaviour

| Method | Path | Behaviour |
|--------|------|-----------|
| `GET` | `/webhooks/meta` | Meta verification; `403` on mismatch |
| `POST` | `/webhooks/meta` | Accept JSON event; log safe metadata; `200 {"status":"received"}` |

Does **not** replace n8n normalized ingress (`POST /api/v1/webhook/message`). WhatsApp business processing will be wired in a later slice (normalization in n8n, SoT in PostgreSQL).

---

## Local verification (curl)

Replace `YOUR_VERIFY_TOKEN` and run while backend listens (default dev: port 8000):

```bash
curl -sS -G "http://127.0.0.1:8000/webhooks/meta" \
  --data-urlencode "hub.mode=subscribe" \
  --data-urlencode "hub.verify_token=YOUR_VERIFY_TOKEN" \
  --data-urlencode "hub.challenge=1158201444"
```

Expected: HTTP 200, body `1158201444` (plain text).

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
