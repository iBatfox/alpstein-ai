# F.2.2a — Fix URLSearchParams in ERPNext Lead Prepare node

**Date:** 2026-05-29  
**Failure:** Executions **337–339** — `ReferenceError: URLSearchParams is not defined` in **Prepare ERPNext Lead Payload**  
**Fix:** `scripts/n8n/build_e1_8_unified_workflow.py` — `buildQuery()` + `encodeURIComponent`  
**Export `versionId`:** `f2.2a-erpnext-query-fix-v1`

## Validation (repo)

```bash
python3 scripts/n8n/build_e1_8_unified_workflow.py
grep -R "URLSearchParams" n8n/workflows/          # 0 matches
grep -c "encodeURIComponent" n8n/workflows/e1_8_unified_customer_ingress_skeleton.json  # 3
```

## Promotion (operator / agent 2026-05-29)

```bash
docker cp n8n/workflows/e1_8_unified_customer_ingress_skeleton.json alpstein_n8n_compose:/tmp/e18-f22a-import.json
docker exec alpstein_n8n_compose n8n import:workflow --input=/tmp/e18-f22a-import.json
docker exec alpstein_n8n_compose n8n publish:workflow --id=aYrRmAGKhP4TJbG9
docker restart alpstein_n8n_compose
```

Live export check: **0** `URLSearchParams`, **1** `buildQuery` in published workflow.

## Smoke test evidence

| Check | Result | Notes |
|-------|--------|-------|
| Live workflow code | **PASS** | Export from n8n confirms fix |
| Post-fix Telegram exec ID | pending | Operator: DM `@alpsteinai_0001bot` → record exec ID |
| ERPNext Lead created/updated | pending | Desk verify after successful exec |
| No ReferenceError in Prepare node | pending | Confirm in execution log |
