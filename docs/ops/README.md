# Operations Documentation

**Doc status:** canonical (navigation layer)  
**As-of:** 2026-05-28 (OPS-H1)

Runbooks describe **how to operate** the runtime described in [`../architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md).

**START HERE →** [`runtime-map.md`](runtime-map.md) (ports, containers, allowed/forbidden commands)

**Architecture map →** [`../architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md)

**Operational SoT (post-D4):** Portable Docker Compose backend (`http://backend:8000`) — not stale host `:8010`. Policy: [`operational-ingress-policy.md`](operational-ingress-policy.md). Wrap-up: [`../audits/d4-operational-wrap-up-2026-05-27.md`](../audits/d4-operational-wrap-up-2026-05-27.md).

**Repository layout (n8n scripts):** [`repository-layout-n8n-scripts.md`](repository-layout-n8n-scripts.md) — E0 / **TD-D4-n8n-script-layout** closed.

---

## Repository paths (scripts vs `n8n/`)

| Path | Purpose |
|------|---------|
| [`n8n/`](../../n8n/) | n8n runtime unit: compose, env examples, [`workflows/`](../../n8n/workflows/) exports |
| [`n8n/scripts/`](../../n8n/scripts/) | Operator scripts that need a **live n8n container** |
| [`scripts/n8n/`](../../scripts/n8n/) | Repo **workflow JSON** gates (e.g. `export-scrub.sh` — no n8n runtime) |
| [`scripts/verify/`](../../scripts/verify/) | **Cross-cutting** verification harnesses (e.g. D3 backend trace) |

---

## Production runbooks (current paths)

| Document | Doc status | Topic |
|----------|------------|-------|
| [`e4-release-controller-runbook.md`](e4-release-controller-runbook.md) | spec (pre-impl) | E4 release automation operator skeleton |
| [`n8n-update-notification-runbook.md`](n8n-update-notification-runbook.md) | design | n8n upstream release Telegram alert (notify-only) |
| [`runtime-map.md`](runtime-map.md) | **canonical** (ops) | Canonical topology, ports, compose v2 rule (OPS-H1) |
| [`runtime-surface-hardening.md`](runtime-surface-hardening.md) | runtime-derived | OPS-H1 inventory and hardening notes |
| [`n8n-unified-customer-ingress-runbook.md`](n8n-unified-customer-ingress-runbook.md) | **canonical** (ops) | Production unified ingress (E1.9) |
| [`operational-ingress-policy.md`](operational-ingress-policy.md) | **canonical** (ops) | Single backend ingress (OPS-C1 / D4) |
| [`n8n-runtime-export-parity.md`](n8n-runtime-export-parity.md) | **canonical** (ops) | Workflow export governance (Phase C) |
| [`n8n-runtime-start.md`](n8n-runtime-start.md) | runtime-derived | Legacy host n8n Docker runtime |
| [`n8n-https-reverse-proxy.md`](n8n-https-reverse-proxy.md) | runtime-derived | HTTPS edge |
| [`n8n-env-credential-checklist.md`](n8n-env-credential-checklist.md) | **canonical** (ops) | Env vars and credentials |
| [`n8n-workflow1-test-webhook.md`](n8n-workflow1-test-webhook.md) | runtime-derived | Test webhook workflow |
| [`n8n-workflow-telegram-customer-ingress.md`](n8n-workflow-telegram-customer-ingress.md) | runtime-derived | Telegram ingress workflow |
| [`n8n-workflow-website-chat-mvp.md`](n8n-workflow-website-chat-mvp.md) | runtime-derived | Website Chat MVP ingress workflow |
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
