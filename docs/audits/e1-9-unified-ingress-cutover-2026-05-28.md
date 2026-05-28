# E1.9 — Unified customer ingress production cutover

**Date:** 2026-05-28  
**Verdict:** **PASS WITH NOTES**  
**Design:** [`unified-customer-ingress-workflow.md`](../architecture/unified-customer-ingress-workflow.md)  
**Runbook:** [`n8n-unified-customer-ingress-runbook.md`](../ops/n8n-unified-customer-ingress-runbook.md)

---

## Summary

Production customer ingress now runs through a **single active workflow** `alpstein-customer-ingress` on `alpstein_n8n_compose`. Legacy Telegram and Website Chat workflows are **inactive**, **archived**, and **renamed** (not deleted).

**Website path (Option A):** Widget example updated to unified path  
`/webhook/alpstein/unified-customer-ingress/website-chat/incoming`.  
Legacy path `alpstein/website-chat/incoming` no longer has an active owner (**HTTP 500** after archival path migration).

---

## Workflow IDs

| Role | ID | Name | `active` | `isArchived` |
|------|-----|------|----------|--------------|
| **Production unified** | `aYrRmAGKhP4TJbG9` | `alpstein-customer-ingress` | **true** | false |
| Legacy Telegram | `2lMuaSWD1XFOXLEK` | `alpstein-incoming-message-telegram-archived-e1-9` | false | true |
| Legacy Website | `hAJ3TFYn69in0vd5` | `alpstein-incoming-message-website-chat-archived-e1-9` | false | true |
| Test webhook | `2qfhWKtgbDy6YeTh` | `alpstein-incoming-message-test` | true | — |

---

## Pre-flight (PASS)

| Check | Result |
|-------|--------|
| Backend `GET /api/v1/health/ready` | **200** |
| n8n → backend ready | **200** |
| Legacy Website smoke `alpstein/website-chat/incoming` | **200** |
| Legacy Telegram inject `alpstein-telegram-customer-trigger/webhook` | **200** |
| Unified `active` before cutover | **false** |
| Workflow backups | `n8n/workflows/backups/e1-9-cutover-2026-05-28/` |

---

## Preparation

| Step | Result |
|------|--------|
| Credential fix (customer vs owner bot) | **Done** — DB patch: Trigger/Send → `alpsteinai_0001bot`; Owner Notify → `AlpsteinAIbot` |
| Bot separation verify | **PASS** — `SEPARATION_VERIFIED=yes` |
| Widget example URL | **Updated** — `website-widget/example.html` → unified path |
| `ALPSTEIN_WEBSITE_CHAT_ENABLED` | `true` on compose n8n |

**Note:** Re-import by name alone mapped customer nodes to owner bot; cutover required explicit credential ID binding in n8n SQLite.

---

## Cutover smokes

### Telegram (unified webhook inject)

| Field | Value |
|-------|--------|
| URL | `http://127.0.0.1:15679/webhook/alpstein-telegram-customer-trigger-unified-inactive/webhook` |
| Secret | `aYrRmAGKhP4TJbG9_e1800001-0000-4000-8000-000000000001` |
| HTTP | **200** |
| Execution IDs | **290**, **294**, **297**, **298** on workflow `aYrRmAGKhP4TJbG9` |

### Website Chat (unified path)

| Field | Value |
|-------|--------|
| URL | `http://127.0.0.1:15679/webhook/alpstein/unified-customer-ingress/website-chat/incoming` |
| HTTP | **200** |
| Response | `success: true`, `correlation_id`, `message.text` present |
| Execution IDs | **291**, **297** on `aYrRmAGKhP4TJbG9` |

### Backend POST evidence

```
POST /api/v1/webhook/message HTTP/1.1" 200 OK  (from n8n 172.21.0.4)
```

### Business context evidence

Execution data for unified runs (**290** / **291**) contains:

- `Add Business Context` node output
- `operator_business_context` in POST payload
- String `Alpstein AI demo business` in execution blob

---

## Post-cutover state

| Check | Result |
|-------|--------|
| Active workflows | `alpstein-customer-ingress` + test only |
| Unified Telegram inject | **200** |
| Unified Website path | **200** |
| Legacy Website prod path | **500** (no active owner — expected after cutover) |
| Legacy workflows archived | **yes** (`isArchived=1`) |

---

## Rollback backups

| Location | Contents |
|----------|----------|
| `n8n/workflows/backups/e1-9-cutover-2026-05-28/` | Pre-cutover exports: `aYrRmAGKhP4TJbG9.json`, `2lMuaSWD1XFOXLEK.json`, `hAJ3TFYn69in0vd5.json` |
| `n8n/workflows/backups/e1-9-cutover-2026-05-28/post-cutover/` | Post-cutover exports (same IDs) |
| Volume | `database.sqlite.bak-e19` on `alpstein_n8n_data` (if present) |

**Rollback:** Deactivate `aYrRmAGKhP4TJbG9`; reactivate and restore webhook paths on archived workflows; re-import pre-cutover JSON from backup dir; restart n8n; point widget to legacy Website path.

---

## Notes (PASS WITH NOTES)

1. **Live Telegram DM** not verified in this cutover — only webhook inject. Operator should send one DM to `@alpsteinai_0001bot` and confirm `getWebhookInfo` URL matches unified registration after activation.
2. **Telegram webhookId** remains `alpstein-telegram-customer-trigger-unified-inactive` (non-prod label; URL works when workflow active).
3. **Inactive legacy Website workflow** still executed on prod path until webhook path was moved to `alpstein/archived-e1-9/website-chat/incoming` + restart (known n8n `active=false` ≠ unregister behavior, per E1.6.6).
4. **Deployed widgets** outside repo must be updated to unified Website URL (example.html only updated in git).
5. Brief **n8n SQLITE_READONLY** incident during credential patch — fixed with `chown 1000:1000` on volume DB.

---

## Files changed (repo)

- `website-widget/example.html` — unified webhook URL
- `n8n/workflows/e1_8_unified_customer_ingress_skeleton.json` — `versionId` → `e1.9-unified-customer-ingress-v1`
- `scripts/n8n/build_e1_8_unified_workflow.py` — version bump
- `docs/audits/e1-9-unified-ingress-cutover-2026-05-28.md` (this file)
- `docs/ops/n8n-unified-customer-ingress-runbook.md`
- `n8n/workflows/runtime-registry.md`
- `docs/project-status/current-state.md`, `next-steps.md`
- `tasks/done/T-e1.9-unified-ingress-production-cutover.md`
