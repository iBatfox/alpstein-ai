# T-f2.1 — ERPNext Lead Creation in Unified n8n Ingress (Phase F.2.1)

**Status:** done (superseded by F.2.2 export `f2.2-erpnext-lead-field-dedupe-v1`) (implementation in repo; operator promotion pending)  
**Branch:** `stabilization/runtime-baseline`

## Goal

After successful Alpstein backend write, non-blocking ERPNext Lead create/update in `alpstein-customer-ingress`.

## Scope

- Parallel tail on `POST Backend` success branch
- Dedupe: phone → email → external_id → name+channel+business
- Kill switch `ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED`
- Credential `erpnext_crm_api` (Header Auth: `token key:secret`)
- No backend / PostgreSQL changes

## Out of scope

- CRM scoring, routing, pipelines
- ERPNext ↔ PostgreSQL sync
- Blocking customer replies on ERP failure

## Deliverables

| Item | Status |
|------|--------|
| `scripts/n8n/build_e1_8_unified_workflow.py` F.2.1 nodes | Done |
| `n8n/workflows/e1_8_unified_customer_ingress_skeleton.json` | Done (`versionId` `f2.1-erpnext-lead-sync-v1`) |
| `docs/ops/n8n-erpnext-lead-sync.md` | Done |
| `docs/audits/f2-1-erpnext-lead-n8n-sync.md` | Done |
| Operator import + live tests | Pending |

## Tests

| # | Case | Expected |
|---|------|----------|
| 1 | New Telegram sender | One Lead in ERPNext |
| 2 | Same Telegram sender again | Same Lead updated, no duplicate |
| 3 | New Website sender | One Lead |
| 4 | No phone/email | Dedupe by `alpstein:dedupe:{channel}:{business}:{external_id}` in description |
| 5 | ERPNext down / wrong URL | Customer reply still succeeds; logger `outcome=failed` |
| 6 | Bad API auth | Same as 5 |

## Success criteria

- [ ] Workflow import on production n8n
- [ ] Credential bound; env flag `true` in staging first
- [ ] Six tests recorded in audit doc
- [ ] Alpstein gates unchanged (Telegram + Website)
