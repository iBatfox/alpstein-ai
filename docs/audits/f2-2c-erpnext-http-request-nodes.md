# F.2.2c — ERPNext HTTP Request nodes (replace Code `httpRequestWithAuthentication`)

**Date:** 2026-05-29  
**Workflow:** `alpstein-customer-ingress` (`aYrRmAGKhP4TJbG9`)  
**Export `versionId`:** `f2.2c-erpnext-http-request-nodes-v3`  
**Prior failure:** Execution **344** — `helpers.httpRequestWithAuthentication` not supported in Code node

## Root cause

1. **F.2.2b** moved Search/Create/Update to Code nodes using `this.helpers.httpRequestWithAuthentication`, which n8n **2.22.5 disallows** in the Code node sandbox (exec **344**).
2. **F.2.2c v1** restored `n8n-nodes-base.httpRequest` v4.2 but used `predefinedCredentialType` + `genericAuthType` (invalid pairing); Header Auth requires **`genericCredentialType`** + **`genericAuthType: httpHeaderAuth`**.
3. **Datetime format:** ERPNext MariaDB rejects ISO-8601 with `Z` on custom Datetime fields (`first_message_at` / `last_message_at`) → HTTP 500 on create/update. Fixed with `erpnextDateTime()` in Prepare / Prepare Update.

## Builder changes

| Area | Change |
|------|--------|
| Search / Create / Update | `n8n-nodes-base.httpRequest` v4.2, `genericCredentialType` + `httpHeaderAuth`, `fullResponse` + `neverError`, timeout 15s, `continueOnFail` + `continueRegularOutput` |
| Prepare ERPNext Lead Payload | Kept Code; added `erpnextDateTime()`; still `buildQuery` + `encodeURIComponent` (no `URLSearchParams`) |
| Parse / IF Search OK / Search Failed Logger / Result Logger | Unchanged safety: `search_failed` → no Create |
| Removed | `SEARCH_ERPNEXT_LEAD`, `CREATE_ERPNEXT_LEAD`, `UPDATE_ERPNEXT_LEAD` Code blocks |

## Promotion (operator)

```bash
python3 scripts/n8n/build_e1_8_unified_workflow.py
docker stop alpstein_n8n_compose
docker run --rm -v alpstein_n8n_data:/home/node/.n8n \
  -v /opt/alpstein-ai/n8n/workflows/e1_8_unified_customer_ingress_skeleton.json:/tmp/e18-import.json:ro \
  --env-file /opt/alpstein-ai/n8n/.env -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
  docker.n8n.io/n8nio/n8n:2.22.5 import:workflow --input=/tmp/e18-import.json
docker run --rm -v alpstein_n8n_data:/home/node/.n8n --env-file /opt/alpstein-ai/n8n/.env \
  docker.n8n.io/n8nio/n8n:2.22.5 publish:workflow --id=aYrRmAGKhP4TJbG9
docker run --rm -v alpstein_n8n_data:/home/node/.n8n --env-file /opt/alpstein-ai/n8n/.env \
  docker.n8n.io/n8nio/n8n:2.22.5 update:workflow --id=aYrRmAGKhP4TJbG9 --active=true
docker start alpstein_n8n_compose
# After start:
docker exec alpstein_n8n_compose n8n publish:workflow --id=aYrRmAGKhP4TJbG9
docker restart alpstein_n8n_compose
```

**Live export check (2026-05-29):** Search/Create/Update = `httpRequest`; `genericCredentialType` + `httpHeaderAuth`; **0** `httpRequestWithAuthentication` in export.

## Smoke evidence

| Check | Result |
|-------|--------|
| `grep httpRequestWithAuthentication n8n/workflows/` | **0** |
| `grep URLSearchParams n8n/workflows/` (workflow) | **0** |
| Telegram inject → ERPNext Lead create | **CRM-LEAD-2026-00007** (`alpstein_chat_id` 8000048945) |
| Same chat second message | Same lead **00007**, `conversation_count` 2 → 3 (no duplicate row) |
| Website inject | **CRM-LEAD-2026-00006** / **00008** (visitor ids from smoke script) |
| Customer path | HTTP 200 on webhook inject; backend POST 200 in logs |

| Scenario | Execution ID (approx.) | Lead ID |
|----------|------------------------|---------|
| First Telegram (smoke script) | **357** | CRM-LEAD-2026-00007 |
| Second Telegram (same chat, dedupe) | **361** | CRM-LEAD-2026-00007 (updated) |

**Note:** `scripts/ops/f22_erpnext_lead_sync_smoke.sh` lead-count helper returned 0 while ERPNext had rows (filter/query timing); use ERPNext list API or n8n execution UI for confirmation.

## Search-failure gate (preserved)

Exec **344** showed `outcome: search_failed` and Create skipped. IF **ERPNext Search OK** + **ERPNext Search Failed Logger** unchanged in F.2.2c.

## Open items

- Operator: one **live Telegram DM** to `@alpsteinai_0001bot` and record execution ID + Lead name in UI (inject path validated).
- Duplicate `erpnext_crm_api` credentials in n8n DB (two rows); consider deduplicating in n8n UI.
