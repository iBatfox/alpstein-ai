# n8n runtime workflow registry

**Purpose:** Map **reviewed git exports** to **runtime workflow IDs** on a given host.  
**Rule:** Update this file whenever import/activate changes production or staging IDs.  
**Secrets:** No tokens, chat IDs, or credential values here.

**Canonical exports:** [`README.md`](README.md)

---

## Contabo legacy runtime (as of 2026-05-27)

> Portable compose (`alpstein_n8n_compose`) is separate. Do not assume IDs below exist on a clean clone.

| Path | Export file | `versionId` | Runtime workflow ID | `active` | Notes |
|------|-------------|-------------|---------------------|----------|-------|
| Test webhook (T13.5) | `t13_workflow1_test_webhook_skeleton.json` | `t13-5-owner-notify-v5` | `2qfhWKtgbDy6YeTh` | ops | Gate 2 passed — see ops doc |
| Telegram customer ingress | `t14_workflow_telegram_customer_ingress_skeleton.json` | `t14-alpstein-ai-greeting-v1` | `2lMuaSWD1XFOXLEK` | ops | Deactivated post-test; duplicate imports exist — **only one** may be active per bot |
| Telegram (stale imports) | same | various | `FHSgBtwDm9PyDAl2`, `61X8sCbW3pqoBRwI`, … | `false` | Deactivate extras before any re-activation |

**Activation policy (Contabo):** Import from repo → re-bind credentials → activate **one** Telegram workflow → restart n8n → verify Telegram webhook 200 (not 403). See [`n8n-runtime-export-parity.md`](../../docs/ops/n8n-runtime-export-parity.md).

---

## Portable compose runtime (clean clone)

| Path | Export file | Runtime workflow ID | `active` | Notes |
|------|-------------|---------------------|----------|-------|
| (none by default) | — | — | — | B2.9 gate: no import/activate in automated path |

After operator import, add rows here for that environment.

---

## Change log

| Date | Change | Operator |
|------|--------|----------|
| 2026-05-27 | C1 registry created; Contabo IDs from ops docs | audit |
