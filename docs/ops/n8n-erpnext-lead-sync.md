# n8n — ERPNext Lead sync (Phase F.2.1)

**Workflow:** `alpstein-customer-ingress`  
**Export:** `n8n/workflows/e1_8_unified_customer_ingress_skeleton.json`  
**`versionId`:** `f2.2-erpnext-lead-field-dedupe-v1`  
**Unified ingress runbook:** [`n8n-unified-customer-ingress-runbook.md`](n8n-unified-customer-ingress-runbook.md)

## Architecture

```text
POST Backend (Alpstein SoT) ──┬──► Shape Canonical Customer Reply → channel delivery (unchanged)
                              ├──► IF Notify Owner (unchanged)
                              └──► Prepare ERPNext Lead Payload → … → ERPNext Result Logger
                                   (continueOnFail on all HTTP nodes)
```

PostgreSQL remains source of truth. ERPNext receives a **CRM copy** only after `backend.success === true`.

## Kill switch

| Variable | Value | Effect |
|----------|-------|--------|
| `ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED` | `true` | ERPNext tail runs |
| (unset / other) | | Prepare node returns `[]` — no ERP calls |

Default in repo `.env.example`: **disabled** until operator enables after credential setup.

## ERPNext API

| Step | Method | Path |
|------|--------|------|
| Search | `GET` | `/api/resource/Lead?filters=…&fields=…&limit_page_length=1` |
| Create | `POST` | `/api/resource/Lead` |
| Update | `PUT` | `/api/resource/Lead/{name}` |

**Base URL:** `ERPNEXT_BASE_URL` (default `https://crm.alpstein-ai.ch`)

**Auth:** n8n credential **`erpnext_crm_api`** (type: Header Auth)

- Header name: `Authorization`
- Value: `token {api_key}:{api_secret}` (from ERPNext User → API Access)

Do **not** put keys in workflow JSON or git.

## Dedupe order (F.2.2 — field filters only)

Every tier includes `["alpstein_business_id", "=", business_id]`.

| Priority | Tier | Search filters |
|----------|------|----------------|
| 1 | `phone` | `mobile_no` = normalized digits |
| 2 | `email` | `email_id` = lowercased email |
| 3 | `chat_id` | `alpstein_channel`, `alpstein_chat_id` (Telegram chat id or website `visitor_id`) |
| 4 | `external_id` | `alpstein_channel`, `alpstein_external_user_id` |
| 5 | `name_channel_business` | `lead_name` = `{channel} / {business_id} / {name\|visitor}` |

**Do not** use `description` or free-text LIKE for dedupe.

Structured fields written on create/update: see [`erpnext-alpstein-lead-fields.md`](erpnext-alpstein-lead-fields.md).

Custom fields migration (one-time): [`scripts/erpnext/create_alpstein_lead_fields.py`](../../scripts/erpnext/create_alpstein_lead_fields.py).

## New nodes (7)

| Node | Type | Notes |
|------|------|-------|
| Prepare ERPNext Lead Payload | Code | Skips if disabled or backend not successful |
| Search ERPNext Lead | HTTP GET | 15s timeout, `continueOnFail` |
| Parse ERPNext Search | Code | |
| IF ERPNext Lead Exists | IF | |
| Prepare ERPNext Lead Update | Code | |
| Update ERPNext Lead | HTTP PUT | |
| Prepare ERPNext Lead Create | Code | |
| Create ERPNext Lead | HTTP POST | |
| ERPNext Result Logger | Code | `console.log` JSON — no PII bodies |

## Operator setup

1. ERPNext: create integration user (e.g. `n8n.integration@alpstein-ai.ch`) with API key + secret; roles with Lead create/read/write and Communication create/read. In ERPNext v15, `Inbox User` grants Communication create permission.
2. n8n UI → Credentials → Header Auth → name **`erpnext_crm_api`**.
3. Set in `n8n/.env` (or compose env):

```bash
ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED=false   # true only after smoke
ERPNEXT_BASE_URL=https://crm.alpstein-ai.ch
```

4. Regenerate export if needed: `python3 scripts/n8n/build_e1_8_unified_workflow.py`
5. Import workflow (same workflow ID `aYrRmAGKhP4TJbG9` on Contabo — update in place).
6. Re-bind **`erpnext_crm_api`** on all three HTTP nodes.
7. Enable flag in **staging** first; run tests in [`f2-1-erpnext-lead-n8n-sync.md`](../audits/f2-1-erpnext-lead-n8n-sync.md).

## Import (Contabo)

```bash
cd /opt/alpstein-ai
python3 scripts/n8n/build_e1_8_unified_workflow.py
docker cp n8n/workflows/e1_8_unified_customer_ingress_skeleton.json alpstein_n8n_compose:/tmp/e18-import.json
docker exec alpstein_n8n_compose n8n import:workflow --input=/tmp/e18-import.json
# UI: activate alpstein-customer-ingress; verify erpnext_crm_api on HTTP nodes
```

## Verification

| Check | Command / action |
|-------|------------------|
| Flag off | Telegram DM → no ERPNext execution branch (or empty after Prepare) |
| Flag on | New sender → Lead visible in ERPNext desk |
| Dedupe | Second message → same `name` (CRM-LEAD-…), updated description |
| Non-blocking | Stop ERPNext frontend → customer still gets Telegram reply |
| Logs | n8n execution → **ERPNext Result Logger** output `outcome: created\|updated\|failed` |

## Rollback

1. Set `ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED=false` and restart n8n.
2. Or re-import previous workflow export from `n8n/workflows/backups/` (if tagged).
3. Customer ingress unaffected either way.

## Evidence

Record execution IDs and pass/fail in [`f2-1-erpnext-lead-n8n-sync.md`](../audits/f2-1-erpnext-lead-n8n-sync.md) § Test evidence.
