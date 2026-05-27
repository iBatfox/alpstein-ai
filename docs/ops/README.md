# Operations Documentation

**Doc status:** canonical (navigation layer)  
**As-of:** 2026-05-27 (D4.5)

Runbooks describe **how to operate** the runtime described in [`../architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md).

**START HERE →** [`../architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md)

**Operational SoT (post-D4):** Portable Docker Compose backend (`http://backend:8000`) — not stale host `:8010`. Policy: [`operational-ingress-policy.md`](operational-ingress-policy.md). Wrap-up: [`../audits/d4-operational-wrap-up-2026-05-27.md`](../audits/d4-operational-wrap-up-2026-05-27.md).

---

## Production runbooks (current paths)

| Document | Doc status | Topic |
|----------|------------|-------|
| [`operational-ingress-policy.md`](operational-ingress-policy.md) | **canonical** (ops) | Single backend ingress (OPS-C1 / D4) |
| [`n8n-runtime-export-parity.md`](n8n-runtime-export-parity.md) | **canonical** (ops) | Workflow export governance (Phase C) |
| [`n8n-runtime-start.md`](n8n-runtime-start.md) | runtime-derived | Legacy host n8n Docker runtime |
| [`n8n-https-reverse-proxy.md`](n8n-https-reverse-proxy.md) | runtime-derived | HTTPS edge |
| [`n8n-env-credential-checklist.md`](n8n-env-credential-checklist.md) | **canonical** (ops) | Env vars and credentials |
| [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md) | runtime-derived | Test webhook workflow |
| [`n8n-workflow-telegram-customer-ingress.md`](n8n-workflow-telegram-customer-ingress.md) | runtime-derived | Telegram ingress workflow |
| [`telegram-customer-ingress.md`](telegram-customer-ingress.md) | runtime-derived | Normalize mapping (duplicate cluster) |
| [`database-recovery.md`](database-recovery.md) | runtime-derived | DB recovery |

---

## Tier directories (target)

| Directory | Purpose |
|-----------|---------|
| [`production/`](production/) | Live runbooks (future home) |
| [`migration/`](migration/) | Recovery and migration guides |
| [`archived/`](archived/) | Retired one-time checklists |

See [`../MIGRATION-PLAN.md`](../MIGRATION-PLAN.md) Phase 1.5.

---

## Archived / historical (at ops root until moved)

- [`n8n-deployment-plan.md`](n8n-deployment-plan.md) — **deprecated** (T13.0 design)
- [`post-t13-5-stabilization.md`](post-t13-5-stabilization.md) — **archived** (one-time gate)

Index: [`../architecture/deprecated/README.md`](../architecture/deprecated/README.md)

---

## Runtime truth hierarchy (ops)

If an ops doc conflicts with another doc:

1. Runtime code (`backend/`, `n8n/workflows/`)
2. Orchestration reality (n8n workflow behavior + backend service boundaries)
3. Canonical runtime map (`docs/architecture/canonical-runtime-architecture.md`)
4. Ops runbooks (`docs/ops/*.md`)
5. Specs (`specs/`) and historical docs
