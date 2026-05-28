# E0 — Telegram reference channel remediation

**Date:** 2026-05-28  
**Branch:** `stabilization/runtime-baseline` (pre-flight clean)  
**Operator:** agent (Contabo-class host)  
**Task:** [`tasks/done/T-e0-telegram-reference-channel-remediation.md`](../../tasks/done/T-e0-telegram-reference-channel-remediation.md)  
**Prior audit:** [`e0-telegram-regression-2026-05-28.md`](e0-telegram-regression-2026-05-28.md)

## Final verdict

| Verdict | **PASS WITH WARNINGS** |
|---------|-------------------------|

### Telegram reference channel status

**YES WITH WARNINGS**

Portable compose n8n is the **verified** Telegram ingress owner for the full Trigger → backend → AI → notify chain. **Customer Telegram delivery** used a synthetic chat ID (`chat not found` on Send — expected per ops convention). **Langfuse trace IDs** were not present on `prompt_runs` (compose backend missing `LANGFUSE_*` env at runtime). **Legacy** `alpstein_n8n` container was **stopped** during smoke; **portable** `alpstein_n8n_compose` bound **15679** (nginx upstream).

---

## 1. Pre-flight safety

| Check | Result |
|-------|--------|
| `git status` | **Clean** on `stabilization/runtime-baseline` |
| Latest E0 commits | Present (`fe561c7`, `9dab4b3`, …) |
| HubSpot `integrationhubspot_n8n` | **Untouched** |
| Legacy `alpstein_n8n` | **Stopped** before portable takeover |
| Dual `alpstein_n8n_data` mount | **Avoided** — single container at a time |

---

## 2. Portable n8n ownership

| Check | Result |
|-------|--------|
| Container | `alpstein_n8n_compose` on `127.0.0.1:15679` (nginx → `https://n8n.alpstein-ai.ch`) |
| `BACKEND_BASE_URL` | `http://backend:8000` |
| `WEBHOOK_URL` | `https://n8n.alpstein-ai.ch/` |
| Backend ready from n8n | **200** (`/api/v1/health/ready`) |
| Telegram `getWebhookInfo` URL | `https://n8n.alpstein-ai.ch/webhook/alpstein-telegram-customer-trigger/webhook` |
| Active workflows | **One** — `2lMuaSWD1XFOXLEK` during smoke; **`active=0`** after |
| Legacy on 15679 during smoke | **No** |

**Startup (workaround — compose `up n8n` still `ContainerConfig` on this host):**

```bash
docker stop alpstein_n8n
docker rm -f alpstein_n8n alpstein_n8n_compose
docker run -d --name alpstein_n8n_compose --network alpstein_internal \
  -p 127.0.0.1:15679:5678 --env-file ./n8n/.env \
  -e BACKEND_BASE_URL=http://backend:8000 \
  -e WEBHOOK_URL=https://n8n.alpstein-ai.ch/ \
  -v alpstein_n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n:1.95.3
```

---

## 3. Full Telegram smoke

### Injection (webhook, not live DM)

Telegram Trigger secret is deterministic: `{workflowId}_{nodeId}` →  
`2lMuaSWD1XFOXLEK_b1c2d3e4-1400-4000-8000-000000000001` (header `X-Telegram-Bot-Api-Secret-Token`).

| Field | Value |
|-------|--------|
| **n8n execution ID** | **222** |
| Mode | `webhook` |
| Status | `success` |
| Started | `2026-05-28 01:25:08` UTC |
| HTTPS inject HTTP | **200** |
| Backend before/after | **healthy** / **healthy** |
| Backend log | `POST /api/v1/webhook/message` **200** from `172.21.0.4` (n8n on `alpstein_internal`) |

### Node / branch evidence (execution **222** data)

| Step | Evidence |
|------|----------|
| Telegram Trigger | Webhook accepted (execution started) |
| POST Backend | Present; `success: true`; `reply_to_customer` present |
| Telegram Send Message | Ran; **`Bad Request: chat not found`** (synthetic chat `990203`) |
| Owner notify | `notify_owner: true`; **Telegram Owner Notify** branch executed |
| OpenAI / prompt | New `prompt_runs` row (see below) |

### Prompt run

| Field | Value |
|-------|--------|
| `prompt_runs.id` | `e426d4bc-b91e-4d4d-872c-2bcf2b32cf3a` |
| `conversation_intent` | `social_greeting` |
| `langfuse_trace_id` in metadata | **empty** (compose backend without `LANGFUSE_*` in container env) |

### Langfuse

**WARN** — not validated live. Root `.env` has keys; running `alpstein_backend` had **0** `LANGFUSE_*` env vars until operator recreates with compose passthrough (committed in `docker-compose.yml`).

---

## 4. Export / runtime parity

| Check | Result |
|-------|--------|
| `scripts/n8n/export-scrub.sh` G-EXP-2 | **PASS** (3 canonical files) |
| Active workflow during smoke | `2lMuaSWD1XFOXLEK` only |
| Post-smoke | `active=0` in DB after deactivate + restart |
| Canonical export | `t14_workflow_telegram_customer_ingress_skeleton.json` · `versionId` `t14-alpstein-ai-greeting-v1` |
| Unsafe export in git | **None** |

---

## 5. Runtime truth (decision)

| Question | Answer |
|----------|--------|
| **Canonical ingress (verification / E0 sign-off)** | Portable **`alpstein_n8n_compose`** + **`alpstein_backend`** on `alpstein_internal` |
| **Canonical backend endpoint (portable)** | `http://backend:8000` |
| **Canonical DB (portable)** | Volume `alpstein_postgres_data` · service `alpstein_postgres` |
| **Legacy n8n** | Container **`alpstein_n8n` stopped** for smoke; **not** deprecated in code — still documented for Contabo until cutover |
| **Production nginx today** | `127.0.0.1:15679` → currently **`alpstein_n8n_compose`** after remediation (operator must confirm intentional cutover vs restore legacy container name) |
| **Telegram workflow ID (canonical)** | `2lMuaSWD1XFOXLEK` |
| **Rollback export** | `n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json` + backup `n8n/workflows/backups/` |

---

## 6. Warnings (do not hide)

1. **Customer Telegram delivery** — synthetic chat → `chat not found`; pipeline pass, not handset delivery. Real DM still recommended for operator sign-off.
2. **Langfuse** — no trace ID on prompt_run; recreate backend with `LANGFUSE_*` for observability gate.
3. **compose `up n8n`** — still broken (`ContainerConfig`); use `docker run` workaround until compose v2 or fix.
4. **Production container naming** — nginx unchanged; process on **15679** is **`alpstein_n8n_compose`**, not `alpstein_n8n`. Document before next deploy.
5. **Legacy host backend `:8010`** — still not running; portable backend owns webhook traffic during this state.

---

## 7. Operator post-remediation checklist

- [ ] Confirm intentional: keep **portable** on **15679** vs restore **legacy** `alpstein_n8n` container name
- [ ] Optional: one **real DM** to `@alpsteinai_0001bot` with workflow re-activated → handset delivery proof
- [ ] `docker-compose -p alpstein-ai up -d --force-recreate backend` for Langfuse passthrough
- [ ] Record execution ID in [`n8n-workflow-telegram-customer-ingress.md`](../ops/n8n-workflow-telegram-customer-ingress.md) § E0 remediation

---

## Related

- [`n8n-compose.md`](../deployment/n8n-compose.md)
- [`n8n-workflow-telegram-customer-ingress.md`](../ops/n8n-workflow-telegram-customer-ingress.md)
