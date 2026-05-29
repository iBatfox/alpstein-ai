# T-f1 — ERPNext Installation & Operational Architecture (Phase F.1)

**Status:** done (design complete; deploy tracked in T-f1.1)  
**Branch:** `stabilization/runtime-baseline`

## Goal

Deliver production-ready ERPNext deployment architecture for `https://crm.alpstein-ai.ch` without Alpstein integration.

## Scope

- Architecture decision (Docker vs Bench)
- Server sizing, DB separation (MariaDB vs Alpstein PostgreSQL)
- Backup, update, hardening strategies
- Network / DNS / reverse proxy design
- Operator deployment runbook with commands
- Reviewer risk register

## Out of scope

- ERPNext ↔ Alpstein sync or adapters
- PostgreSQL ownership changes
- CRM API integration
- Observability integration into ERPNext

## Deliverables

| File | Status |
|------|--------|
| `docs/architecture/f1-erpnext-installation-operational-architecture.md` | Done |
| `docs/ops/erpnext-production-deployment-runbook.md` | Done |
| Production deploy on `144.91.113.184` | Done — see `T-f1.1-erpnext-production-deployment.md` |
| Evidence table in runbook | Updated 2026-05-29 |

## Success criteria

- [x] Architecture doc reviewed
- [x] ERPNext live at `https://crm.alpstein-ai.ch`
- [x] No public ERP DB/redis ports
- [x] Alpstein stack unchanged
- [ ] Backup tested once (operator)
- [ ] Task moved to `tasks/done/` after human acceptance

## Tests

- Manual: HTTPS, login, `ss -tlnp` port audit, Alpstein health regression
- Restore drill (staging or isolated volume)

## References

- User Phase F.1 charter (2026-05-29)
- `docs/ops/runtime-map.md`
- `docs/ops/n8n-https-reverse-proxy.md`
