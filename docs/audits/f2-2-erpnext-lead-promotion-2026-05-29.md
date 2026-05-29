# F.2.1 / F.2.2 — ERPNext Lead sync promotion report

**Date:** 2026-05-29  
**Workflow:** `alpstein-customer-ingress` (`aYrRmAGKhP4TJbG9`)  
**Export `versionId`:** `f2.2-erpnext-lead-field-dedupe-v1`

## Deployment summary

| Slice | Result |
|-------|--------|
| Lead model audit | [`f2-2-erpnext-lead-model-audit-2026-05-29.md`](f2-2-erpnext-lead-model-audit-2026-05-29.md) |
| Custom fields (29) | **Created** on `crm.alpstein-ai.ch` |
| Lead Source masters | Telegram, Website Chat, WhatsApp, Instagram |
| API user | `n8n.integration@alpstein-ai.ch` (keys in `/etc/alpstein/erpnext-n8n-api.env` only) |
| n8n credential | `erpnext_crm_api` imported (Header Auth) |
| Workflow build + import | **Done** — F.2.2 code in runtime export |
| `ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED` | `true` on `alpstein_n8n_compose` (compose env + recreate) |
| Alpstein PostgreSQL | **Unchanged** |
| Alpstein backend code | **Unchanged** |

## Migration summary

| | Count |
|---|------|
| Fields added | 29 |
| Fields skipped | 0 (first run) |

## Dedupe strategy

| | F.2.1 | F.2.2 |
|---|-------|-------|
| Tier 3 | `description` LIKE marker | `alpstein_channel` + `alpstein_chat_id` |
| Tier 4 | `lead_name` fallback | `alpstein_external_user_id` |
| Tier 5 | — | `lead_name` + `alpstein_business_id` |
| Identity storage | description lines | Custom fields |

## Workflow summary

| Item | Detail |
|------|--------|
| Nodes changed | Prepare / Parse / Update / Create ERPNext (same 7-node tail) |
| Search | `GET /api/resource/Lead?filters=[...]` with custom field filters |
| Telegram normalize | Adds `telegram_username`, `telegram_language_code` |
| `company_name` misuse | **Removed** — use `alpstein_business_id` |

Regenerate: `python3 scripts/n8n/build_e1_8_unified_workflow.py`

## Live test evidence

| # | Scenario | Result | Notes |
|---|----------|--------|-------|
| 1 | New Telegram → one Lead | **BLOCKED** | Backend `POST /api/v1/webhook/message` → **500** (`flow_id` NOT NULL on `conversations`) — ERPNext tail not reached |
| 2 | Same Telegram → update | **BLOCKED** | Same backend blocker |
| 3 | Website → Lead | **BLOCKED** | Same (`website_chat` conversation insert) |
| 4 | Website return → update | **BLOCKED** | Same |
| 5 | ERPNext auth failure | **NOT RUN** | Requires successful backend path first |
| 6 | ERPNext unavailable | **PARTIAL** | Stopped `alpstein-erpnext-frontend-1` → API **502**; restored |
| 7 | UTM in custom fields | **API PASS** | Direct POST with `first_touch_*` (Lead Source masters required for `source` Link) |
| 8 | Telegram metadata fields | **API PASS** | `CRM-LEAD-2026-00001` + filter by `alpstein_chat_id` |
| — | Field dedupe filter | **PASS** | `GET` with `alpstein_chat_id` + `alpstein_business_id` → 1 row |
| — | Unit tests | **PASS** | `pytest scripts/n8n/test_erpnext_lead_dedupe.py` → 6 passed |
| — | Alpstein health | **PASS** | backend 200, postgres healthy |

**n8n execution IDs:** Not captured — backend 500 prevented ERPNext branch execution in smokes.

## Operator follow-up

1. **Fix backend `flow_id`** on conversation create for demo tenant (separate task — blocks all ingress smokes).
2. Re-run [`scripts/ops/f22_erpnext_lead_sync_smoke.sh`](../../scripts/ops/f22_erpnext_lead_sync_smoke.sh) after backend fix.
3. Confirm `erpnext_crm_api` bound on three HTTP nodes in n8n UI after import.
4. Keep `ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED=false` until smokes pass if preferred.

## Reviewer findings

| Level | Finding | Mitigation |
|-------|---------|------------|
| **HIGH** | Backend `flow_id` NOT NULL breaks webhook → no ERPNext tail | Fix backend/seed before production CRM sync validation |
| **HIGH** | Shared VPS RAM (~5.8 GB) with ERPNext + Alpstein | Monitor OOM; see F.1.1 audit |
| **MEDIUM** | `source` Link requires Lead Source master | Masters created 2026-05-29 |
| **MEDIUM** | Workflow import **deactivates** briefly — must `publish:workflow` + port **15679** dev overlay | Documented in promotion steps |
| **LOW** | API keys in `/etc/alpstein/erpnext-n8n-api.env` only | Bind n8n credential; never commit |

## Commands (audit trail)

```bash
python3 scripts/n8n/build_e1_8_unified_workflow.py
docker cp n8n/workflows/e1_8_unified_customer_ingress_skeleton.json alpstein_n8n_compose:/tmp/f22-import.json
docker exec alpstein_n8n_compose n8n import:workflow --input=/tmp/f22-import.json
docker exec alpstein_n8n_compose n8n publish:workflow --id=aYrRmAGKhP4TJbG9
# n8n with ERPNext env + host port:
ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED=true ERPNEXT_BASE_URL=https://crm.alpstein-ai.ch \
  N8N_HOST_PORT=15679 docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps n8n
```
