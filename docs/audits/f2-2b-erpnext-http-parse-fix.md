# F.2.2b — ERPNext HTTP response parsing fix

**Date:** 2026-05-29  
**Prior failure:** Executions **342** (+ 337–339 URLSearchParams) — `Search ERPNext Lead` / `Create ERPNext Lead` error: `Cannot read properties of undefined (reading 'status')`  
**Export `versionId`:** `f2.2b-erpnext-http-parse-fix-v1`

## Root cause

1. **n8n HTTP Request node (v4.2)** crashed internally when the upstream response/credential path left `response` undefined — error surfaced as reading **`.status`**, not in our Code parsers.
2. **Parsers** assumed flat `item.data` / `item.statusCode` only; did not handle `returnFullResponse` shapes (`body.data`, `response.body`, transport errors).
3. **Search failure → Create** path could create duplicate Leads when search never succeeded.

## Fix

| Change | Detail |
|--------|--------|
| Replace ERP HTTP Request nodes | **Search / Create / Update** → **Code** nodes using `httpRequestWithAuthentication('httpHeaderAuth')` + credential **`erpnext_crm_api`** |
| Shared helpers | `getHttpStatus`, `getHttpError`, `unwrapHttpBody`, `getErpnextListRows`, `getErpnextDocName`, `isHttpFailure` |
| Search safety | **IF ERPNext Search OK** → on failure **ERPNext Search Failed Logger** (`outcome: search_failed`) — **no Create** |
| Logger | Uses helpers; outcomes `created` / `updated` / `failed` / `search_failed` |

## HTTP response shapes (documented)

| Case | Shape after Search/Create/Update Code node |
|------|---------------------------------------------|
| Success GET list | `{ statusCode: 200, body: { data: [...] }, data: [...] }` |
| Success GET empty | `{ statusCode: 200, body: { data: [] }, data: [] }` |
| Success POST/PUT | `{ statusCode: 200, body: { data: { name: 'CRM-LEAD-…', … } }, data: { name, … } }` |
| HTTP 401/403 | `{ statusCode: 401/403, body: { … }, error: true }` → `isHttpFailure` true |
| Transport (DNS, timeout) | `{ __transport_error: true, message: '…', statusCode: null }` |

## Promotion (2026-05-29)

```bash
python3 scripts/n8n/build_e1_8_unified_workflow.py
docker cp n8n/workflows/e1_8_unified_customer_ingress_skeleton.json alpstein_n8n_compose:/tmp/e18-f22b-import.json
docker exec alpstein_n8n_compose n8n import:workflow --input=/tmp/e18-f22b-import.json
docker exec alpstein_n8n_compose n8n publish:workflow --id=aYrRmAGKhP4TJbG9
docker restart alpstein_n8n_compose
```

Live export check: Search/Create/Update are **Code** nodes with `httpRequestWithAuthentication`.

## Smoke test evidence

| Check | Date | Exec ID | Result | ERPNext Lead |
|-------|------|---------|--------|--------------|
| First Telegram DM | | pending | | |
| Second DM (dedupe) | | pending | | |
| No `.status` ReferenceError | | pending | | |

## API reachability (no secrets)

From `alpstein_n8n_compose`: `GET https://crm.alpstein-ai.ch/api/method/ping` → **200** `{"message":"pong"}`.
