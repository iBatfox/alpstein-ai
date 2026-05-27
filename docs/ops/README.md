# Operations Documentation

**Doc status:** canonical (navigation layer)  
**As-of:** 2026-05-27

Runbooks describe **how to operate** the runtime described in [`../architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md).

---

## Production runbooks (current paths)

| Document | Doc status | Topic |
|----------|------------|-------|
| [`n8n-runtime-start.md`](n8n-runtime-start.md) | runtime-derived | n8n Docker runtime |
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
