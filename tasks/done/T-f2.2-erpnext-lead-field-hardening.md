# T-f2.2 — ERPNext Lead field hardening + F.2.1 promotion

**Status:** done (pending human acceptance — live n8n smokes blocked by backend `flow_id`)  
**Date:** 2026-05-29

## Goal

Replace description-based ERPNext dedupe with custom Lead fields and field filters; promote workflow `aYrRmAGKhP4TJbG9`.

## Deliverables

| Item | Path |
|------|------|
| Lead audit | `docs/audits/f2-2-erpnext-lead-model-audit-2026-05-29.md` |
| Promotion report | `docs/audits/f2-2-erpnext-lead-promotion-2026-05-29.md` |
| Migration script | `scripts/erpnext/create_alpstein_lead_fields.py` |
| Ops doc | `docs/ops/erpnext-alpstein-lead-fields.md` |
| Workflow builder | `scripts/n8n/build_e1_8_unified_workflow.py` |
| Dedupe tests | `scripts/n8n/test_erpnext_lead_dedupe.py` |
| Smoke script | `scripts/ops/f22_erpnext_lead_sync_smoke.sh` |

## Success criteria

- [x] Custom fields on ERPNext Lead
- [x] Field-based dedupe in workflow export
- [x] Workflow imported to `aYrRmAGKhP4TJbG9`
- [x] API user + n8n credential (host secrets only)
- [ ] Full live tests 1–5 (blocked — backend `flow_id` 500)
- [ ] Human acceptance

## Related

- `tasks/done/T-f2.1-erpnext-lead-n8n-workflow.md` (superseded export version)
