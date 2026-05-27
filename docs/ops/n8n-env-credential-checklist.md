**Doc status:** canonical (ops)  
**Tier:** ops/production (pending move)

# n8n Environment & Credential Checklist (T13.1)

**Purpose:** Pre-flight checklist before building n8n Workflow 1 (test webhook path).  
**Scope:** Names and placement only — **no secret values in this repo.**  
**Design reference:** [`docs/project-status/t13-n8n-workflow-plan.md`](../project-status/t13-n8n-workflow-plan.md)  
**Contracts:** [`specs/api/webhooks.md`](../../specs/api/webhooks.md), [`specs/api/api-endpoints.md`](../../specs/api/api-endpoints.md)  
**Export parity (Phase C1):** [`n8n-runtime-export-parity.md`](n8n-runtime-export-parity.md), [`n8n/workflows/README.md`](../../n8n/workflows/README.md)

Use this checklist for local/dev and production n8n setup. Workflow JSON implementation starts at **T13.2**.

---

## 1. Backend connection

| Item | Value / rule |
|------|----------------|
| Base URL variable | `BACKEND_BASE_URL` |
| Health check | `GET {BACKEND_BASE_URL}/api/v1/health` — no auth |
| Webhook endpoint | `POST {BACKEND_BASE_URL}/api/v1/webhook/message` |
| Content-Type | `application/json` |
| Auth header name | `X-Alpstein-Webhook-Token` |
| Auth header value | Same shared secret as backend env `N8N_BACKEND_API_TOKEN` |
| Auth style | **Not** Bearer — use custom header only (T10-F1) |

### Token alignment (critical)

- [ ] Backend container/host has `N8N_BACKEND_API_TOKEN` set (see `.env.example`).
- [ ] n8n HTTP Request node sends **exactly** that value in `X-Alpstein-Webhook-Token`.
- [ ] Token is identical on both sides; mismatch → `401` `UNAUTHORIZED`, workflow must not retry with wrong creds.
- [ ] If backend token is unset/empty, webhook returns `403` `FORBIDDEN` — configure before testing T13.3.

### Example URLs (placeholders)

```text
BACKEND_BASE_URL=http://backend:8000             # portable target (compose internal)
BACKEND_BASE_URL=https://alpstein-ai.ch          # future production via nginx → api
BACKEND_BASE_URL=http://172.20.0.1:8010          # LEGACY Contabo host only (see n8n-runtime-start.md)
GET  {BACKEND_BASE_URL}/api/v1/health
POST {BACKEND_BASE_URL}/api/v1/webhook/message
```

Canonical env templates: [`backend/.env.example`](../../backend/.env.example), [`n8n/.env.example`](../../n8n/.env.example) — [`deployment-contract.md`](../deployment/deployment-contract.md).

---

## 2. n8n credentials and environment names

**Rule:** Never commit secret values. Document **names only** in repo; store values in server `.env`, n8n credentials UI, or n8n environment injection.

### Where each value lives

| Name | Used by | Store in n8n as | Notes |
|------|---------|-----------------|-------|
| `BACKEND_BASE_URL` | HTTP Request URL | n8n **Environment variable** (Docker `environment:` / n8n Settings → Variables) or expression `{{ $env.BACKEND_BASE_URL }}` | Public or internal URL depending on deployment |
| `N8N_BACKEND_API_TOKEN` | HTTP Request header | n8n **Generic Credential** (Header Auth) **or** environment variable referenced in node — **not** literal in workflow JSON | Must match backend `.env` |
| `N8N_BASIC_AUTH_USER` | n8n admin UI | Docker `.env` / compose | Protects n8n admin (port 5678) |
| `N8N_BASIC_AUTH_PASSWORD` | n8n admin UI | Docker `.env` / compose | Never in workflow export |

### Setup steps (no values)

- [ ] Add `BACKEND_BASE_URL` and `N8N_BACKEND_API_TOKEN` to deployment `.env` (backend + n8n services as applicable).
- [ ] In n8n, create a credential for backend webhook auth (e.g. Header Auth: name `X-Alpstein-Webhook-Token`, value from env) **or** bind header via `$env.N8N_BACKEND_API_TOKEN`.
- [ ] In HTTP Request node (T13.3), reference credential/env — do **not** paste token into node fields that export to JSON.
- [ ] Confirm workflow export / git does not contain credential IDs tied to real secrets (review at T13.8).

### Backend-only (n8n must not use)

| Name | Owner |
|------|--------|
| `ALPSTEIN_AI_DATABASE_URL` | Backend only (`DATABASE_URL` deprecated) |
| `ALPSTEIN_AI_ENVIRONMENT` | Backend only (`ENVIRONMENT` deprecated) |
| `OPENAI_API_KEY`, `OPENAI_MODEL`, `AI_REQUEST_TIMEOUT` | Backend only |
| `LANGFUSE_*` | Backend only |
| `SECRET_KEY` | Deprecated — not in `Settings`; do not configure |

---

## 3. Telegram credentials — dual-bot model

**Canonical design:** [`docs/architecture/telegram-channel-credentials.md`](../architecture/telegram-channel-credentials.md)

### 3a. Owner notification (T13.5 — Alpstein-owned bot)

Required for **owner notification branch only** — **not** for customer Telegram Trigger/Send.

| Name | Purpose | Required when |
|------|---------|---------------|
| `TELEGRAM_BOT_TOKEN` | Bot API token (prefer n8n **Telegram API** credential, not env literal) | **T13.5** — owner notify |
| `TELEGRAM_CHAT_ID` | Owner destination chat ID | **T13.5** — owner notify |

- [ ] Credential name in UI: e.g. **`AlpsteinAIbot`** (owner) — separate from customer bot.
- [ ] Never use this credential on **Telegram Trigger** for customer messages.

### 3b. Customer ingress (T14 — client-owned bot per business)

| Name | Purpose | Required when |
|------|---------|---------------|
| n8n credential `telegram_customer_<business_external_id>` | Client bot token | **T14** — Trigger + Send |
| `n8n/.env.telegram.customer` (gitignored) | One-time handoff for CLI import — **not** committed | **T14.2** import only |
| Backend `tenant_channel_settings.metadata.credential_ref` | Reference label only — **no token** | **T14** (optional metadata) |

- [ ] Client provides token via secure onboarding handoff — not repo/docs.
- [ ] Token only in n8n encrypted credential store; rotation = update credential in n8n UI.
- [ ] Workflow JSON: credential **name** binding in UI after import; no literals in git export.
- [ ] **T14.2:** `getMe` on owner (`Telegram account`) and customer (`telegram_customer_demo_barbershop_001`) — `bot_id` / `username` must differ.
- [ ] **T14.2:** Run `n8n/scripts/t14-import-customer-telegram-credential.sh` then `n8n/scripts/t14-verify-telegram-bots.sh` → `SEPARATION_VERIFIED=yes`.
- [ ] Never set customer bot token in `TELEGRAM_CHAT_ID` or owner credential.

**T14.2 runtime (2026-05-25):** owner `AlpsteinAIbot` (`@AlpsteinAibot`); customer `alpsteinai_0001bot` (`@alpsteinai_0001bot`); `SEPARATION_VERIFIED=yes` — see [`telegram-customer-ingress.md`](telegram-customer-ingress.md) § T14.2.

**T14.3 workflow:** [`n8n-workflow-telegram-customer-ingress.md`](n8n-workflow-telegram-customer-ingress.md) — `alpstein-incoming-message-telegram`; env `ALPSTEIN_TELEGRAM_BUSINESS_ID` optional.

**Test channel (T13.2–T13.4):** Telegram vars **not required.**

---

## 4. Test webhook payload requirements

Normalization (T13.2) must produce this contract before `POST /api/v1/webhook/message`.

### Required fields

| Field | Rule |
|-------|------|
| `business_id` | Business `external_id` string (e.g. seeded `demo_barbershop_001`) |
| `channel` | Must be `"test"` for Workflow 1 MVP path |
| `customer.phone` **or** `customer.external_customer_id` | At least one required |
| `message.text` | Non-empty customer message |
| `message.external_message_id` | **Required for idempotency tests** — stable across retries |

### Optional (safe to omit or null)

- `customer.name`, `customer.email`
- `message.timestamp`
- `message.raw_payload` — debug only; omit secrets; do not branch business logic on it

### Minimal normalized example (structure only)

```json
{
  "business_id": "demo_barbershop_001",
  "channel": "test",
  "customer": {
    "phone": "+41790000000",
    "external_customer_id": "test_customer_001"
  },
  "message": {
    "text": "Hello, can I book tomorrow?",
    "external_message_id": "test-msg-001"
  }
}
```

### Idempotency test rule

- [ ] First POST with `external_message_id` → expect `success: true`, `data.message.is_duplicate: false`.
- [ ] Second POST with **same** `external_message_id` and body → expect `data.message.is_duplicate: true`, `data.notify_owner: false`.
- [ ] HTTP retries (5xx) must reuse the **same** JSON body and `external_message_id`.

---

## 5. Security rules

- [ ] **No API tokens in workflow JSON** committed to git — use n8n credentials or `$env` references.
- [ ] **No credentials in repo** — `.env` is gitignored; `.env.example` has empty placeholders only.
- [ ] **Do not log or screenshot** full `message.raw_payload`, phone numbers, or tokens in shared channels — redact in n8n execution logs and review screenshots.
- [ ] **n8n must not write to PostgreSQL** — no Postgres nodes for business data in MVP; backend owns all DB writes.
- [ ] n8n admin protected (basic auth, HTTPS in production).
- [ ] Do not expose or log system prompts from backend responses.

---

## 6. Local / manual verification checklist

Run before T13.3 (HTTP node) and repeat after env changes.

### Connectivity

- [ ] `GET {BACKEND_BASE_URL}/api/v1/health` returns `200` with `"success": true` and `"status": "ok"`.
- [ ] Backend reachable from n8n host/container (same Docker network or public URL as configured).

### Auth

- [ ] `N8N_BACKEND_API_TOKEN` set on backend.
- [ ] Same token configured for n8n outbound header (credential or env).
- [ ] POST without header → `401` `UNAUTHORIZED`.
- [ ] POST with wrong token → `401` `UNAUTHORIZED`.

### Happy-path webhook (curl or n8n manual test)

- [ ] `POST /api/v1/webhook/message` with valid normalized body + header → `200`, `"success": true`.
- [ ] Response includes `data.reply_to_customer` (non-empty for new message).
- [ ] Response envelope shape matches [`specs/api/webhooks.md`](../../specs/api/webhooks.md) (`data.lead_created`, `data.notify_owner`, etc.).

### Idempotency

- [ ] Duplicate `external_message_id` → `data.message.is_duplicate: true`.
- [ ] Duplicate response → `data.notify_owner: false` (no owner notify on retry).
- [ ] Customer path may still return `data.reply_to_customer` on duplicate (prior AI text or ack).

### Deferred (later tasks)

- [ ] **notify_owner branch** — test after T13.5 (Telegram send); not required for T13.1–T13.4.
- [ ] **Owner Telegram message** — T13.7 E2E checklist.

### Sample curl template (replace placeholders locally; do not commit real token)

```bash
curl -sS -X POST "${BACKEND_BASE_URL}/api/v1/webhook/message" \
  -H "Content-Type: application/json" \
  -H "X-Alpstein-Webhook-Token: ${N8N_BACKEND_API_TOKEN}" \
  -d '{
    "business_id": "demo_barbershop_001",
    "channel": "test",
    "customer": { "phone": "+41790000000" },
    "message": {
      "text": "Hello, first message",
      "external_message_id": "manual-test-001"
    }
  }'
```

---

## 7. Prerequisites for workflow build (T13.2+)

- [ ] Dev seed applied if using `demo_barbershop_001` (`scripts/seed_dev_ai_configuration.py`).
- [ ] Database migrations current (`alembic upgrade head`).
- [ ] This checklist completed and reviewed.
- [ ] Next task: **T13.2** — Workflow 1 skeleton (test webhook + normalize node).

---

## Related documents

| Document | Topic |
|----------|--------|
| [`t13-n8n-workflow-plan.md`](../project-status/t13-n8n-workflow-plan.md) | Full workflow design |
| [`tasks/done/t13-n8n-workflow-slice.md`](../../tasks/done/t13-n8n-workflow-slice.md) | T13 task breakdown + T13.7 E2E |
| [`specs/architecture/n8n-architecture.md`](../../specs/architecture/n8n-architecture.md) | n8n role and boundaries |
| [`specs/architecture/deployment.md`](../../specs/architecture/deployment.md) | Docker services, domains |
