# E0 — Telegram operational regression gate (Phase E)

**Date:** 2026-05-28  
**Phase:** E — Controlled Channel Expansion (entry gate)  
**Operator:** agent (automated verification on Contabo-class host)  
**Branch:** `stabilization/runtime-baseline`  
**Git HEAD:** `f4ff036` (audit start); continuation includes `docker-compose.yml` Langfuse passthrough (uncommitted)  
**Task:** [`tasks/done/T14.5-telegram-compose-regression.md`](../../tasks/done/T14.5-telegram-compose-regression.md)  
**Remediation:** [`e0-telegram-reference-channel-remediation-2026-05-28.md`](e0-telegram-reference-channel-remediation-2026-05-28.md) · [`tasks/done/T-e0-telegram-reference-channel-remediation.md`](../../tasks/done/T-e0-telegram-reference-channel-remediation.md)

## Final verdict (after remediation 2026-05-28)

| Verdict | **PASS WITH WARNINGS** |
|---------|-------------------------|

### Telegram reference channel status

**YES WITH WARNINGS** — portable `alpstein_n8n_compose` full path proven (**execution 222**). See remediation audit for warnings (synthetic Telegram Send, Langfuse, compose `up n8n`, **15679** container naming).

---

## Executive summary

| Work package | Result | Notes |
|--------------|--------|-------|
| **P0** Portable n8n | **PASS** (workaround) | `alpstein_n8n_compose` via `docker run`; `wget` → `/health/ready` **200**; `docker-compose up n8n` still **FAIL** (`ContainerConfig`) |
| **P1** Telegram smoke | **WARN** | Telegram-shaped `POST /webhook/message` **200** from `alpstein_internal` (simulates POST Backend node); **no** new n8n execution ID on portable Telegram Trigger |
| **P2** Runtime truth | **PASS** | Documented below + ops/project-status updates |
| **P3** Env / password | **PASS** (after remediation) | Volume password aligned to root `.env` for TCP/scram; trust-local trap documented |
| **P4** Langfuse | **WARN** | Keys present in root `.env`; compose passthrough added; backend **not** recreated — live trace not re-run |
| **P6** Discipline | **PASS** | G-EXP-2 PASS; legacy HubSpot n8n untouched |

---

## P2 — Canonical runtime truth (2026-05-28)

| Category | What | Owner / endpoint | Status on Contabo |
|----------|------|------------------|-------------------|
| **Compose (canonical for verification)** | `docker-compose -p alpstein-ai` | `alpstein_postgres` + `alpstein_backend` + `alpstein_n8n_compose` on `alpstein_internal` | Postgres + backend **healthy** after reset; portable n8n via **`docker run`** (compose `up n8n` blocked) |
| **Legacy (production ingress today)** | `n8n/docker-compose.yml` project `alpstein-n8n` | `alpstein_n8n` @ `127.0.0.1:15679`; `BACKEND_BASE_URL=http://172.20.0.1:8010` | **Running** after E0 restore; host backend **8010 down** |
| **Historical / evidence** | Prior gate runs | n8n exec **55–57**, **89–91** (legacy path) | Reference only — not re-run this continuation |
| **Telegram ingress owner (live)** | Legacy until cutover | Workflow `2lMuaSWD1XFOXLEK` · export `t14-alpstein-ai-greeting-v1` | **Deactivated** post-E0 (`active=false` after restart) |
| **Telegram ingress target (verification)** | Portable | `BACKEND_BASE_URL=http://backend:8000` | Network POST **200**; Trigger webhook not registered on `127.0.0.1:15680` |
| **Backend (portable canonical)** | Compose service | `http://backend:8000` inside `alpstein_internal` | Health/ready **200** when postgres healthy |
| **Backend (legacy canonical)** | Host uvicorn | `http://172.20.0.1:8010` | **Not running** on this host |
| **DB (portable canonical)** | Volume `alpstein_postgres_data` | `alpstein_postgres:5432` | Alembic at head; bootstrap OK |
| **DB (legacy)** | `backend_postgres` @ `127.0.0.1:15432` | Separate from portable volume | Not used in E0 continuation |
| **n8n volume** | `alpstein_n8n_data` | Shared name — **do not** run legacy + portable n8n concurrently | E0: legacy **stopped** briefly for portable smoke |
| **Workflow export (canonical git)** | `n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json` | `versionId` `t14-alpstein-ai-greeting-v1`, `active: false` | G-EXP-2 **PASS** |

---

## P0 — Portable n8n compose

### Startup (approved workaround)

`docker-compose -p alpstein-ai … up -d n8n` failed with `KeyError: 'ContainerConfig'` (compose **1.29.2**, Docker **29.x**).

```bash
cd /opt/alpstein-ai
# Legacy stopped briefly — shared alpstein_n8n_data (no dual-writer)
docker stop alpstein_n8n

docker run -d \
  --name alpstein_n8n_compose \
  --network alpstein_internal \
  --restart unless-stopped \
  -p 127.0.0.1:15680:5678 \
  --env-file ./n8n/.env \
  -e BACKEND_BASE_URL=http://backend:8000 \
  -e WEBHOOK_URL=http://127.0.0.1:15680/ \
  -v alpstein_n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n:1.95.3
```

### Connectivity

| Check | Result |
|-------|--------|
| `docker exec alpstein_n8n_compose wget -qO- http://backend:8000/api/v1/health/ready` | **200** JSON `ready` |
| n8n UI `http://127.0.0.1:15680/` (basic auth) | **200** |
| Legacy `alpstein_n8n` on **15679** | **Restored** after P1; portable container **stopped** |
| HubSpot `integrationhubspot_n8n` | **Untouched** |

### Isolation

- **Ports:** legacy **15679**, portable dev **15680** — no port conflict.
- **Volume:** same `alpstein_n8n_data` — **exclusive** mount required (documented in [`n8n-compose.md`](../deployment/n8n-compose.md)).

---

## P1 — Telegram smoke (portable stack)

### Backend health

| When | `alpstein_backend` | `/health/ready` |
|------|-------------------|-----------------|
| Before network POST | healthy | 200 |
| After network POST | healthy | 200 |

### Portable network POST (Telegram-shaped contract)

From `curlimages/curl` on `alpstein_internal` (same path as n8n **POST Backend** node):

| Field | Value |
|-------|--------|
| HTTP | **200** |
| `success` | **true** |
| `reply_to_customer` length | **282** chars (RU greeting scenario) |
| Duplicate `data.message.is_duplicate` | **true** (same `external_message_id`) |

### Prompt runs (DB)

| `prompt_runs.id` | `created_at` (UTC) |
|------------------|---------------------|
| `11b52702-addd-4cf3-9f02-e967082c21d8` | 2026-05-28 00:55:46 |
| `96686c6c-2a59-4dda-a2cb-c80b6cce310e` | 2026-05-28 00:55:10 |

### n8n workflow execution

| Item | Result |
|------|--------|
| New portable execution IDs | **None** — Telegram Trigger not registered on local `WEBHOOK_URL` |
| Telegram Send / owner notify via n8n | **Not exercised** on portable path |
| Historical reference | Legacy exec **89–91** ([`n8n-workflow-telegram-customer-ingress.md`](../ops/n8n-workflow-telegram-customer-ingress.md)) |

**Post-test:** Workflow `2lMuaSWD1XFOXLEK` set `active=false`; legacy `alpstein_n8n` restarted; **no** active workflows listed after restart.

---

## P3 — Env / password discipline

| Check | Result |
|-------|--------|
| Root `.env` `POSTGRES_PASSWORD` set | Yes |
| TCP/scram from peer container | **PASS** after `ALTER USER` aligned to `.env` |
| Trust-local false positive | Documented — `psql -h localhost` inside postgres container does **not** validate `.env` password |
| `ALPSTEIN_AI_DATABASE_URL` in backend matches `.env` | **PASS** after backend recreate |
| `N8N_BACKEND_API_TOKEN` | Present in backend + `n8n/.env` (values not logged) |
| Secrets in git / logs | None committed; no tokens in sampled backend logs |

**Operator-controlled:** Re-run password alignment after any volume restore; document in [`database-recovery.md`](../ops/database-recovery.md) cross-link (see remediation task E0-R3).

---

## P4 — Langfuse (optional)

| Check | Result |
|-------|--------|
| `LANGFUSE_*` in root `.env` | Present (not recorded) |
| Compose `backend` service | **Updated** — passthrough `${LANGFUSE_*}` added to `docker-compose.yml` |
| Running `alpstein_backend` container | **Not recreated** during continuation — tracing not re-validated |
| Hard gate? | **No** — WARN only |

**Operator:** `docker-compose -p alpstein-ai up -d --force-recreate backend` after `.env` keys set; one webhook smoke; confirm trace in Langfuse UI (IDs only in ops doc).

---

## P0 initial run (2026-05-28 early) — retained notes

Early E0 hit postgres name drift (`61f0c2d54a79_alpstein_postgres`), backend password drift, and portable n8n absent. Continuation reset stack with `docker-compose down` + `up` for postgres/backend and applied P0 workaround for n8n.

---

## Open risks / remediation

See [`T-e0-telegram-reference-channel-remediation.md`](../../tasks/todo/T-e0-telegram-reference-channel-remediation.md):

1. Fix or document `ContainerConfig` for `docker-compose up n8n`
2. Portable Telegram Trigger smoke with execution IDs (or signed live DM)
3. Postgres password alignment runbook
4. Langfuse compose recreate + trace spot-check
5. Contabo cutover plan (legacy vs portable; host 8010)

---

## Commands (sanitized audit trail)

```bash
cd /opt/alpstein-ai
set -a && . ./.env && set +a

docker-compose -p alpstein-ai down
docker-compose -p alpstein-ai up -d postgres backend
# ALTER USER when TCP auth fails — password from .env, not logged

docker run -d --name alpstein_n8n_compose --network alpstein_internal \
  -p 127.0.0.1:15680:5678 --env-file ./n8n/.env \
  -e BACKEND_BASE_URL=http://backend:8000 \
  -e WEBHOOK_URL=http://127.0.0.1:15680/ \
  -v alpstein_n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n:1.95.3

docker exec alpstein_n8n_compose wget -qO- http://backend:8000/api/v1/health/ready
docker-compose -p alpstein-ai --profile bootstrap run --rm backend-bootstrap
scripts/n8n/export-scrub.sh

# Telegram-shaped POST from alpstein_internal
docker run --rm --network alpstein_internal curlimages/curl:8.5.0 \
  -H "Content-Type: application/json" \
  -H "X-Alpstein-Webhook-Token: <from-env>" \
  -d '<telegram-shaped-json>' \
  http://backend:8000/api/v1/webhook/message

docker stop alpstein_n8n_compose
cd n8n && docker-compose -p alpstein-n8n up -d   # restore legacy
docker exec alpstein_n8n n8n update:workflow --id=2lMuaSWD1XFOXLEK --active=false
docker restart alpstein_n8n
```

---

## Related

- [`d4-2-compose-e2e-hardening-2026-05-28.md`](d4-2-compose-e2e-hardening-2026-05-28.md)
- [`n8n-compose.md`](../deployment/n8n-compose.md)
- [`n8n-runtime-export-parity.md`](../ops/n8n-runtime-export-parity.md)
- [`n8n-workflow-telegram-customer-ingress.md`](../ops/n8n-workflow-telegram-customer-ingress.md)
