# T-e1.8 — Unified customer ingress (inactive implementation)

## Status

Done (2026-05-28) — **PASS WITH NOTES**

## Goal

Implement `alpstein-customer-ingress` as inactive workflow JSON + runtime import without production cutover.

## Deliverables

- [x] `n8n/workflows/e1_8_unified_customer_ingress_skeleton.json`
- [x] `scripts/n8n/build_e1_8_unified_workflow.py`
- [x] `scripts/n8n/export-scrub.sh` canonical entry
- [x] Import on `alpstein_n8n_compose` — ID **`aYrRmAGKhP4TJbG9`**, `active: false`
- [x] [`docs/audits/e1-8-unified-ingress-inactive-implementation-2026-05-28.md`](../../docs/audits/e1-8-unified-ingress-inactive-implementation-2026-05-28.md)
- [x] Runbook, registry, project status updates

## Constraints respected

- No activation of unified workflow
- Production Telegram (`2lMuaSWD1XFOXLEK`) and Website (`hAJ3TFYn69in0vd5`) remain active
- Non-prod webhook paths; unified website path returns 404 while inactive
- No backend/DB/compose config changes

## Notes for E1.9

- Re-bind `alpsteinai_0001bot` on customer Telegram nodes after import
- Follow cutover sequence in audit doc § E1.9
