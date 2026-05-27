# Project Status Documentation

**Doc status:** canonical (navigation layer)  
**As-of:** 2026-05-27

Living project status vs historical record.

**START HERE →** [`../architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md)

---

## Current tier (living documents)

| Document | Doc status | Role |
|----------|------------|------|
| [`current-state.md`](current-state.md) | runtime-derived | Regeneratable snapshot |
| [`next-steps.md`](next-steps.md) | **canonical** (queue) | Single open-work queue |
| [`completed.md`](completed.md) | **canonical** (changelog) | Accepted deliverables |
| [`decisions.md`](decisions.md) | **canonical** (ADRs) | Architecture decisions |
| [`documentation-topology-status.md`](documentation-topology-status.md) | canonical | Doc structure inventory |

**Runtime architecture (primary):** [`../architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md)

## How to use status docs safely (AI/engineer navigation)

When anything looks inconsistent, resolve in this order:

1. Runtime code (`backend/`, `n8n/workflows/`)
2. Orchestration layer (backend services + n8n normalize + ops runbooks)
3. Canonical runtime map (`../architecture/canonical-runtime-architecture.md`)
4. Current status docs (this folder: `current-state`, `completed`, `next-steps`)
5. Specs (`specs/`)
6. Historical / deprecated (`historical/`, archived plans)

---

## Historical tier (pending migration)

| Document | Doc status |
|----------|------------|
| [`engineering-archive.md`](engineering-archive.md) | archived |
| [`historical/engineering-audit-report.md`](historical/engineering-audit-report.md) | archived |
| [`historical/t11-ai-orchestration-plan.md`](historical/t11-ai-orchestration-plan.md) | archived |
| [`historical/t12-lead-notification-plan.md`](historical/t12-lead-notification-plan.md) | archived |
| [`t13-n8n-workflow-plan.md`](t13-n8n-workflow-plan.md) | archived |
| [`../architecture/deprecated/t11-prompt-builder-design.md`](../architecture/deprecated/t11-prompt-builder-design.md) | deprecated |
| [`historical/backlog.md`](historical/backlog.md) | deprecated |
| [`channel-source-attribution-design.md`](channel-source-attribution-design.md) | draft |

Subdirectories: [`current/`](current/), [`historical/`](historical/)
