# Telegram ingress regression — INC-2026-05-29-R1

**Date:** 2026-05-29  
**Status:** **mitigated** (ops fixes applied; operator sign-off pending)  
**Prior incident:** [`telegram-incident-2026-05-29.md`](telegram-incident-2026-05-29.md) (execution **313**)  
**Workflow:** `alpstein-customer-ingress` (`aYrRmAGKhP4TJbG9`)  
**Out of scope:** ERPNext application stack, backend feature work, workflow redesign

---

## Executive summary

The customer bot failed again **for different reasons than a simple repeat of INC-2026-05-29**. Investigation found **four independent failure modes** that can each produce “bot silent”:

| # | Root cause | Symptom |
|---|------------|---------|
| **RC-A** | Telegram webhook **not registered** (`getWebhookInfo.url` empty) | No n8n executions |
| **RC-B** | **Stale backend image** (ORM without `flow_id`; DB requires `flow_id`) | `POST /api/v1/webhook/message` **500** |
| **RC-C** | n8n `BACKEND_BASE_URL=http://backend:8000` **DNS failure** after manual `docker run` (no `backend` alias) | Workflow may show success while backend never reached |
| **RC-D** | **Telegram Send Message** uses **owner** credential (`AlpsteinAIbot`) instead of **customer** (`alpsteinai_0001bot`) | Pipeline runs; user sees no reply on `@alpsteinai_0001bot` |

**ERR_ERL_UNEXPECTED_X_FORWARDED_FOR** in n8n logs is a **rate-limit warning only** — not the blocker (executions **317–327** succeeded with it present).

---

## Timeline (America/New_York, from `n8nEventLog.log`)

| Time | Event |
|------|--------|
| **~01:55** | INC-2026-05-29 remediation validated — execution **313** success |
| **02:45** | n8n container start (`activationMode: init`); executions **317–318** |
| **02:49–03:02** | Executions **320–325** success (webhook + env access working) |
| **02:58–03:06** | Operator **workflow.updated** + deactivate/activate cycles (new `versionId`s; ERPNext nodes present) |
| **03:00** | Execution **323** — **failed** at `Prepare ERPNext Lead Payload` (`URLSearchParams is not defined`) |
| **03:11** | Last live ingress before gap — executions **326–327** success |
| **03:11+ → investigation** | `getWebhookInfo` **empty**; no new customer executions |
| **Investigation** | Backend **500** (`flow_id` NOT NULL); Send node on owner bot; webhook re-bound; backend rebuilt; execution **330** E2E **200** |

---

## Evidence (commands / signals — no secrets)

### Telegram

- `getMe` — customer `@alpsteinai_0001bot` **ok**; owner `@AlpsteinAibot` **ok**; bots **separate**
- `getWebhookInfo` (customer, during outage) — `url: (EMPTY)`, `pending_update_count: 0`
- `getWebhookInfo` (post unpublish/publish) — URL `…/webhook/alpstein-telegram-customer-trigger-unified-inactive/webhook`

### n8n

- Active workflows: `alpstein-customer-ingress`, `alpstein-incoming-message-test` only
- `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` in container
- Workflow **31 nodes** (ERPNext branch added in UI — not in repo canonical export)
- Export credential bindings:
  - Trigger → `alpsteinai_0001bot`
  - **Send Message → `AlpsteinAIbot` (wrong)**
  - Owner Notify → `AlpsteinAIbot` (correct)

### Backend

- Running image **before fix:** `Conversation` model **without** `flow_id`; DB column `flow_id` **NOT NULL**
- Logs: `asyncpg.exceptions.NotNullViolationError: null value in column "flow_id" of relation "conversations"`
- Access log mix: **34× 200**, **11× 500** on `/api/v1/webhook/message` (approximate grep)
- **After rebuild** (`alpstein-ai-backend:local` current): `flow_id: True`; execution **330** → backend **200**

### Infrastructure

- `docker-compose up` recreate → `KeyError: ContainerConfig` (compose 1.29 / Docker 29)
- Manual `docker run` for n8n/backend — **no compose DNS name `backend`** unless network alias added
- nginx: webhook POST without secret → **403** (expected); `healthz` **200**

---

## Root cause analysis (mechanisms)

### RC-A — Webhook registration loss (recurring)

Telegram only delivers updates when `setWebhook` is active for the **current** bot token. An empty `getWebhookInfo.url` means **zero ingress** regardless of n8n workflow state.

**Likely triggers this regression:**

- n8n **container recreate/restart** without successful publish-time `setWebhook`
- **BotFather token rotation** (credential count went from 3 → 4) clearing webhook without re-bind
- Repeated UI **deactivate/activate** without verifying `getWebhookInfo` after each change

This is the **same class** as INC-2026-05-29 RC-1 but **not proof the first fix was wrong** — registration is **not durable** across these events without a verification step.

### RC-B — Backend image / schema drift (new)

Postgres was migrated (`conversations.flow_id` NOT NULL, default flows seeded). The **running** `alpstein_backend` container was built from **older code** that omitted `flow_id` on insert → **500** for new conversations.

**Not** an n8n or Telegram issue; explains intermittent failures when webhook **was** working (executions reached POST Backend).

### RC-C — Docker DNS mismatch (new)

`n8n/.env` sets `BACKEND_BASE_URL=http://backend:8000`. Compose creates DNS name `backend`. **Manual** `docker run --name alpstein_backend` does **not**, unless `--network-alias backend` is added.

Symptom: `ping: bad address 'backend'` from n8n; POST Backend node cannot reach API (execution **329** showed workflow success without backend log line until URL fixed to `alpstein_backend` or alias added).

### RC-D — Wrong outbound Telegram credential (new)

**Telegram Send Message** uses credential id `oTj3scjSJY32GUBN` (**AlpsteinAIbot**). Customer DMs are on **@alpsteinai_0001bot**. Replies are sent with the **owner** bot token — often **invisible** in the customer chat.

Known pattern from E1.9 cutover; reintroduced by UI workflow edits / version publishes.

### RC-E — ERPNext nodes in ingress workflow (contributing)

Operator-added ERPNext branch caused execution **323** failure. Does not explain empty webhook but increases failure rate when ingress is active.

---

## Fixes applied during investigation (2026-05-29)

| Step | Action |
|------|--------|
| 1 | Rebuilt `alpstein-ai-backend:local` and restored `alpstein_backend` container (current code with `flow_id`) |
| 2 | Recreated `alpstein_n8n_compose` with `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`, `BACKEND_BASE_URL=http://alpstein_backend:8000` |
| 3 | Unpublish → restart → publish → restart unified workflow (Telegram webhook re-registered) |
| 4 | Added Docker network alias `backend` → `alpstein_backend` so `http://backend:8000` resolves |
| 5 | Validated execution **330**: n8n success + backend `POST /api/v1/webhook/message` **200** |

**Not completed (operator):**

- Re-bind **Telegram Send Message** → credential **`alpsteinai_0001bot`** in n8n UI (DB patch attempted; use UI to avoid SQLite corruption — `PRAGMA integrity_check` reported errors after failed patch attempt; restore from `database.sqlite.bak-*` if n8n UI misbehaves)
- Live DM to `@alpsteinai_0001bot`
- Token rotation sign-off if not already done in BotFather
- Remove or disable ERPNext branch in ingress workflow if not approved for production

---

## Validation

| Check | Result |
|-------|--------|
| `getWebhookInfo` (customer) | **Pass** — production unified path |
| `N8N_BLOCK_ENV_ACCESS_IN_NODE` | **false** |
| Synthetic webhook + secret | **HTTP 200** |
| n8n execution **330** | **success** (Trigger → Normalize → POST Backend → Telegram Send) |
| Backend webhook | **HTTP 200** |
| `wget http://backend:8000/...` from n8n | **Pass** (after network alias) |
| Live Telegram DM | **Pending operator** |

---

## Recommendations (P1)

1. **Post every n8n deploy:** `getWebhookInfo` + one live DM + record execution ID.
2. **Never `docker run` n8n/backend without:** (a) `BACKEND_BASE_URL=http://alpstein_backend:8000` **or** (b) `--alias backend` on backend container.
3. **Always rebuild backend** after Alembic migrations before declaring ingress healthy.
4. **Credential checklist** after any workflow UI save: Trigger + Send = `alpsteinai_0001bot`; Owner Notify = `AlpsteinAIbot`.
5. **Avoid full `docker-compose up`** on this host until `ContainerConfig` issue resolved — use targeted `docker run` / `--no-deps`.
6. **Do not add ERPNext logic** to customer ingress until architecture-approved; keep ERPNext out of hot path.

---

**Report status:** For operator review. Not committed unless requested.
