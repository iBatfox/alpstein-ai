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
| **Unified customer ingress (E1.9 + E2 PATCH)** | `e1_8_unified_customer_ingress_skeleton.json` | `e2-delivery-outcome-patch-v1` | **`aYrRmAGKhP4TJbG9`** | **`true`** | **PRODUCTION** — includes delivery outcome PATCH nodes |
| Telegram (archived E1.9) | `t14_workflow_telegram_customer_ingress_skeleton.json` | — | `2lMuaSWD1XFOXLEK` | **`false`** | Renamed `…-telegram-archived-e1-9`; `isArchived=1` |
| Website Chat (archived E1.9) | `e1_6_workflow_website_chat_mvp_skeleton.json` | — | `hAJ3TFYn69in0vd5` | **`false`** | Renamed `…-website-chat-archived-e1-9`; webhook path archived |
| Telegram (stale imports) | same | various | `FHSgBtwDm9PyDAl2`, `61X8sCbW3pqoBRwI`, … | `false` | Deactivate extras before any re-activation |
| Website Chat duplicate (archived) | same | older import | `OnaY83T8YLRUB8SJ` | `false` | Renamed to `...-archived-e1-6-2`; keep inactive |

**Activation policy (Contabo):** Import from repo → re-bind credentials → activate **one** Telegram workflow → restart n8n → verify Telegram webhook 200 (not 403). See [`n8n-runtime-export-parity.md`](../../docs/ops/n8n-runtime-export-parity.md).

---

## Portable compose runtime (clean clone / E0)

| Path | Export file | Runtime workflow ID | `active` | Notes |
|------|-------------|---------------------|----------|-------|
| Telegram customer ingress | `t14_workflow_telegram_customer_ingress_skeleton.json` | `2lMuaSWD1XFOXLEK` (shared volume) | **false** (E0 post-test) | E0 remediation **2026-05-28**: portable `alpstein_n8n_compose` exec **222**; ingress owner on **15679** |

After operator import on a **fresh** volume, add rows here. On Contabo, portable n8n shares `alpstein_n8n_data` with legacy — IDs match legacy table above.

---

## Change log

| Date | Change | Operator |
|------|--------|----------|
| 2026-05-27 | C1 registry created; Contabo IDs from ops docs | audit |
| 2026-05-28 | E0 portable smoke; workflow deactivated post-test | audit |
| 2026-05-28 | E0 remediation exec **222**; portable owns 15679 during test | audit |
| 2026-05-28 | E1.6.6: Website Chat canonical ID fixed; duplicate archived; env kill switch semantics verified | audit |
| 2026-05-28 | E1.8: `alpstein-customer-ingress` imported inactive (`aYrRmAGKhP4TJbG9`); prod webhooks unchanged | audit |
| 2026-05-28 | E1.9: Production cutover — unified **active**; legacy archived/renamed | audit |
