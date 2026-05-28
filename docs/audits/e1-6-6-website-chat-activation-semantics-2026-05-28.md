# E1.6.6 — Website Chat activation semantics verification

**Date:** 2026-05-28  
**Scope:** n8n runtime/workflow governance only (no backend/Telegram/AI changes)

## Objective

Replace ambiguous workflow-active semantics with explicit runtime kill switch behavior:

- `ALPSTEIN_WEBSITE_CHAT_ENABLED=true` -> production webhook responds and execution continues to backend
- `ALPSTEIN_WEBSITE_CHAT_ENABLED=false` -> workflow returns 503 disabled response and does not call backend

---

## 1) Runtime workflow inspection

Website Chat workflows found in runtime DB:

- `wuQM4a8vFOC1OBHB` — `alpstein-incoming-message-website-chat` (canonical)
- `OnaY83T8YLRUB8SJ` — duplicate import from earlier smoke

Webhook registration for production path:

- `alpstein/website-chat/incoming` owned by `wuQM4a8vFOC1OBHB`

Conclusion: duplicate existed in workflow table, but webhook path owner was canonical workflow ID.

---

## 2) Duplicate cleanup

Duplicate workflow handled safely:

- `OnaY83T8YLRUB8SJ` forced inactive
- renamed to archive marker: `alpstein-incoming-message-website-chat-archived-e1-6-2`

Canonical workflow retained:

- `wuQM4a8vFOC1OBHB` with canonical name `alpstein-incoming-message-website-chat`

No Telegram workflows changed.

---

## 3) Production kill-switch verification

Target URL:

- `https://n8n.alpstein-ai.ch/webhook/alpstein/website-chat/incoming`

### A) Disabled state (`ALPSTEIN_WEBSITE_CHAT_ENABLED=false`)

Steps:

1. Set `ALPSTEIN_WEBSITE_CHAT_ENABLED=false` in `n8n/.env`
2. Recreate `alpstein_n8n` so env is reloaded
3. POST probe payload to production URL

- HTTP: `503`
- Response body:
  - `success: false`
  - `error.code: WEBSITE_CHAT_DISABLED`
- Execution evidence:
  - latest Website Chat execution `258` (success)
  - execution payload contains `Respond Website Chat Disabled`
  - execution payload does **not** include `POST Backend`

### B) Enabled state (`ALPSTEIN_WEBSITE_CHAT_ENABLED=true`)

Steps:

1. Set `ALPSTEIN_WEBSITE_CHAT_ENABLED=true` in `n8n/.env`
2. Recreate `alpstein_n8n` so env is reloaded
3. POST probe payload to same production URL

- HTTP: `200`
- Website Chat execution evidence:
  - before enabled probe: latest execution `258`
  - after enabled probe: new execution `259` (`status=success`)
  - execution payload includes `POST Backend`
  - execution payload does not include disabled responder path

---

## 4) Final activation semantics status

**PASS**

Behavior is now unambiguous and explicit:

- env kill switch true -> backend-backed Website Chat flow runs
- env kill switch false -> deterministic 503 disabled response; backend not called

Canonical Website Chat workflow for operations:

- **ID:** `hAJ3TFYn69in0vd5`
- **Name:** `alpstein-incoming-message-website-chat`

---

## 5) Non-scope confirmations

- No backend changes
- No AI/orchestration changes
- No Telegram workflow changes
- No endpoint path redesign
