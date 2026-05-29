# Telegram customer ingress outage — incident report

**Incident ID:** INC-2026-05-29-TELEGRAM  
**Date:** 2026-05-29  
**Status:** **resolved** (validated)  
**Severity:** **high** (customer-facing ingress down)  
**Scope:** Alpstein portable stack — `alpstein_n8n_compose` + unified workflow `alpstein-customer-ingress`  
**Out of scope:** ERPNext, backend application code, database schema

**Runbook updates:** [`../ops/n8n-unified-customer-ingress-runbook.md`](../ops/n8n-unified-customer-ingress-runbook.md) §10  
**Related audits:** [`e1-9-unified-ingress-cutover-2026-05-28.md`](e1-9-unified-ingress-cutover-2026-05-28.md) · [`e0-telegram-regression-2026-05-28.md`](e0-telegram-regression-2026-05-28.md)

---

## Summary

After upgrading the portable n8n runtime to **n8n 2.22.5**, the **Telegram customer bot stopped responding**. Two independent root causes were confirmed:

1. **Telegram webhook registration was missing** — `getWebhookInfo` reported an empty webhook URL, so Telegram had no delivery target.
2. **n8n 2.x blocked `$env` in Code nodes by default** — the unified workflow node **Normalize Telegram Incoming** reads `ALPSTEIN_TELEGRAM_BUSINESS_ID` via `$env`; executions failed immediately after the Telegram Trigger.

Remediation re-registered the Telegram webhook (unpublish → restart → publish → restart), recreated the n8n container with `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (persisted in `docker-compose.yml` and `n8n/.env`), and restored Postgres after a failed compose recreate. Post-fix validation: webhook registered, synthetic ingress **HTTP 200**, n8n execution **313** success, backend `POST /api/v1/webhook/message` **HTTP 200**.

---

## Timeline

| Time (UTC, approximate) | Event |
|-------------------------|--------|
| Pre-incident | Portable stack on unified ingress (`aYrRmAGKhP4TJbG9`); n8n image bumped toward **2.22.5** |
| Incident start | Customer Telegram bot stops replying to DMs |
| Detection | Operator observes no new successful customer ingress executions; workflow errors after trigger |
| Diagnosis | `getWebhookInfo` → empty `url`; failed executions on **Normalize Telegram Incoming** (env access) |
| Remediation | Webhook re-registration cycle; n8n recreate with `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`; Postgres recovery after compose recreate issue |
| Validation | Webhook registered; synthetic webhook **200**; execution **313**; backend webhook **200** |
| Close | Ingress path operational; documentation and runbook updated |

*Exact clock times to be appended by operator if log retention allows.*

---

## Detection

| Signal | Observation |
|--------|-------------|
| User report | Telegram bot not responding |
| n8n executions | Failures on unified ingress after Telegram Trigger |
| Telegram API | `getWebhookInfo` — **no webhook URL** configured |
| Backend | No (or insufficient) successful `POST /api/v1/webhook/message` from customer path during outage |

---

## Impact

| Area | Impact |
|------|--------|
| **Customer Telegram** | Inbound messages not processed; no AI reply path |
| **Website Chat** | Not primary failure mode for this incident (Telegram path) |
| **Backend / DB** | No schema or code change; service healthy when reached |
| **Owner notifications** | Dependent on successful customer ingress — effectively blocked for Telegram |
| **Data loss** | None identified — messages not delivered to n8n, not lost in Alpstein DB |

---

## Root cause analysis

### RC-1 — Missing Telegram webhook registration

| Item | Detail |
|------|--------|
| **Mechanism** | Telegram delivers updates only to a registered webhook URL. Empty URL → no deliveries to n8n. |
| **Likely trigger** | n8n container recreate / runtime upgrade / workflow publish cycle without successful webhook re-bind |
| **Contributing factor** | Unified workflow uses inactive-path naming during E1.8; production cutover requires active publish + correct n8n public URL |

### RC-2 — n8n 2.x environment variable block in Code nodes

| Item | Detail |
|------|--------|
| **Mechanism** | n8n **2.x** defaults to blocking environment variable access inside nodes (`N8N_BLOCK_ENV_ACCESS_IN_NODE` not set → blocked). |
| **Affected node** | **Normalize Telegram Incoming** — uses `$env.ALPSTEIN_TELEGRAM_BUSINESS_ID` (and related env) |
| **Symptom** | Execution fails after Telegram Trigger even if webhook fires |
| **Fix** | Set `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` on n8n service (compose + `n8n/.env`) |

### Interaction

Either RC alone can cause “bot silent.” During this incident **both** were present: even after webhook repair, normalize would fail until env access was enabled.

---

## Evidence

| Evidence type | Result (no secrets recorded) |
|---------------|------------------------------|
| `getWebhookInfo` (pre-fix) | `url` empty / unset |
| `getWebhookInfo` (post-fix) | Webhook URL points at n8n production webhook path |
| n8n execution | **313** — completed successfully (post-fix) |
| Synthetic webhook test | **HTTP 200** |
| Backend access log / trace | `POST /api/v1/webhook/message` — **HTTP 200** |
| Container env (post-fix) | `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` |
| Compose | `docker-compose.yml` n8n service documents n8n **2.22.5** and env override |

**Not logged here:** bot tokens, webhook secrets, `N8N_BACKEND_API_TOKEN`, message bodies, chat IDs.

---

## Resolution

### 1. Telegram webhook re-registration

Operator procedure (no token values in logs):

1. **Unpublish** active unified ingress workflow in n8n UI (or CLI equivalent).
2. **Restart** `alpstein_n8n_compose`.
3. **Publish** workflow (activate production webhook registration).
4. **Restart** n8n again (per operator practice to ensure clean bind).

### 2. n8n 2.x Code node env access

| Location | Setting |
|----------|---------|
| `docker-compose.yml` | `N8N_BLOCK_ENV_ACCESS_IN_NODE: "false"` on `n8n` service |
| `n8n/.env` | `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` |

Recreate n8n container so env applies to runtime.

### 3. Postgres recovery

Compose recreate initially failed; **Postgres restored** per existing recovery runbook (`docs/ops/database-recovery.md`) before full stack validation.

### 4. No application changes

- No backend code changes  
- No Alembic migrations  
- No ERPNext changes  

---

## Validation

| Check | Result |
|-------|--------|
| Telegram webhook registered | **Pass** |
| Synthetic webhook request | **HTTP 200** |
| n8n execution **313** | **Success** |
| Backend `POST /api/v1/webhook/message` | **HTTP 200** |
| Live Telegram DM (operator) | **Recommended** — confirm in runbook §10 |

---

## Lessons learned

1. **n8n major/minor upgrades are ingress-critical** — treat 2.x upgrades as a gated release with env + webhook checklist, not image-only bump.
2. **`N8N_BLOCK_ENV_ACCESS_IN_NODE` is mandatory** for unified ingress Code nodes — document in compose, `.env.example`, and pre-deploy verification.
3. **Webhook registration is stateful** — container recreate or unpublish can clear Telegram’s view; always verify `getWebhookInfo` after deploy.
4. **Compose recreate can affect Postgres** — follow database recovery procedure before declaring stack healthy.
5. **Silent failure mode** — users see “bot dead”; backend health can remain green — monitor **n8n execution success rate** and **webhook registration**, not health endpoint alone.

---

## Follow-up actions

| ID | Action | Owner | Priority |
|----|--------|-------|----------|
| F-1 | Add pre-deploy check: `docker exec alpstein_n8n_compose env \| grep N8N_BLOCK_ENV_ACCESS_IN_NODE` | Ops | **P1** |
| F-2 | Add post-deploy `getWebhookInfo` + live DM to E1/E4 verification tables | Ops | **P1** |
| F-3 | Pin n8n upgrade checklist in `docs/deployment/` (env + webhook + smoke) | Archivist / Ops | **P2** |
| F-4 | Consider automated alert on n8n workflow error rate (Telegram trigger path) | Deferred | **P3** |
| F-5 | Update `n8n/.env.example` comment — **done** in repo | — | Done |

---

## Operations audit entry (concise)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-29 |
| **System** | Alpstein AI — unified customer ingress (Telegram) |
| **Runtime** | `alpstein_n8n_compose` @ n8n **2.22.5** |
| **Verdict** | **Resolved** — dual root cause (webhook + env block) |
| **Customer impact** | Telegram ingress unavailable until fix |
| **Code/DB change** | **None** — ops/config only |
| **Evidence** | Execution **313**, backend webhook **200**, webhook registered |
| **Doc** | This file + runbook §10 |

---

**Report status:** Draft for operator review — **not committed** unless explicitly requested.
