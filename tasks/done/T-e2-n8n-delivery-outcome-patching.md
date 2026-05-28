# T-e2-n8n — Delivery outcome PATCH wiring

## Status

Done (2026-05-28) — repo + docs; runtime import pending operator

## Goal

Wire `alpstein-customer-ingress` to PATCH delivery outcome after Telegram/Website transport.

## Deliverables

- [x] `Prepare Delivery PATCH` + `PATCH Delivery Outcome` nodes in unified workflow export
- [x] `scripts/n8n/build_e1_8_unified_workflow.py` updated (`versionId`: `e2-delivery-outcome-patch-v1`)
- [x] [`docs/n8n/delivery-outcome-patching.md`](../../docs/n8n/delivery-outcome-patching.md)
- [x] `n8n/.env.example` observability UUID vars
- [x] G-EXP-2 pass; backend delivery API tests pass (17)

## Operator follow-up

1. Set `ALPSTEIN_OBSERVABILITY_TENANT_ID` + `ALPSTEIN_OBSERVABILITY_BUSINESS_ID` in n8n env
2. Re-import unified workflow; restart n8n
3. Smoke PATCH via Website + verify GET delivery status
