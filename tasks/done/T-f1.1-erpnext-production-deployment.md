# T-f1.1 — ERPNext Production Deployment (Phase F.1.1)

**Status:** done (pending human acceptance)  
**Date:** 2026-05-29  
**Branch:** `stabilization/runtime-baseline`

## Goal

Deploy isolated ERPNext production stack at `https://crm.alpstein-ai.ch` without touching Alpstein AI runtime or PostgreSQL.

## Scope

- `/opt/alpstein-erpnext` via official `frappe_docker`
- MariaDB, Redis, workers, scheduler
- Host nginx + Let's Encrypt
- Loopback-only `127.0.0.1:18080`
- Verification + deployment report

## Out of scope

- ERPNext ↔ Alpstein integration
- CRM sync / adapters
- Alpstein compose / backend / n8n changes

## Success criteria

- [x] ERPNext at `https://crm.alpstein-ai.ch`
- [x] No public 3306/6379/8080/8000 for ERPNext
- [x] Alpstein stack regression pass
- [x] Deployment report in `docs/audits/`
- [ ] First backup (operator follow-up)
- [ ] Human acceptance

## Evidence

- [`docs/audits/f1-1-erpnext-production-deployment-2026-05-29.md`](../../docs/audits/f1-1-erpnext-production-deployment-2026-05-29.md)
- [`docs/ops/erpnext-production-deployment-runbook.md`](../../docs/ops/erpnext-production-deployment-runbook.md) — Evidence table

## Related

- Architecture: [`T-f1-erpnext-installation-operational-architecture.md`](T-f1-erpnext-installation-operational-architecture.md)
