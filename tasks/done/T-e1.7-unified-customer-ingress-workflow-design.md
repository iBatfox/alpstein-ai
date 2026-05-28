# T-e1.7 — Unified customer ingress workflow (design)

## Status

Done (2026-05-28) — **design only**, no runtime changes

## Goal

Design a unified customer ingress workflow that keeps separate channel entry points but shares the same business pipeline after channel normalization.

## Scope

- Review current Telegram and Website Chat n8n workflows
- Compare normalization, POST payload, owner notify, errors, observability
- Define unified topology, canonical intermediate schema, migration, rollback
- No workflow JSON changes in E1.7
- No production cutover in E1.7

## Deliverables

- [`docs/architecture/unified-customer-ingress-workflow.md`](../../docs/architecture/unified-customer-ingress-workflow.md)
- [`docs/ops/n8n-unified-customer-ingress-runbook.md`](../../docs/ops/n8n-unified-customer-ingress-runbook.md)
- This task file

## Constraints respected

- No backend code changes
- No DB changes
- No webhook path changes in design phase
- Telegram remains reference baseline
- Website Chat kill switch preserved in design (Website branch only)

## Open questions (for implementation task)

See architecture doc §16.
