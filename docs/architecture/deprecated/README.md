# Deprecated & Archive Candidates

**Doc status:** canonical (archive index)  
**As-of:** 2026-05-27

**Rule:** Listed documents are **not deleted** in Phase 1.2. Do not use for runtime truth or planning. Prefer [`../canonical-runtime-architecture.md`](../canonical-runtime-architecture.md) and [`../../project-status/next-steps.md`](../../project-status/next-steps.md).

---

## Obsolete checklists

| Document | Current path | Reason | Target tier |
|----------|--------------|--------|-------------|
| Alpstein AI Backlog | [`../../project-status/backlog.md`](../../project-status/backlog.md) | All P0 items shipped or superseded; contradicts `completed.md` | `project-status/historical/` |

---

## Superseded design drafts

| Document | Current path | Superseded by | Target tier |
|----------|--------------|---------------|-------------|
| T11.7 Prompt Builder design note | [`../../project-status/t11-prompt-builder-design.md`](../../project-status/t11-prompt-builder-design.md) | [`specs/architecture/prompt-builder-rules.md`](../../../specs/architecture/prompt-builder-rules.md) | `architecture/deprecated/` |
| Technical pre-sales behavior MVP | [`../technical-pre-sales-behavior-mvp.md`](../technical-pre-sales-behavior-mvp.md) | CIP-B intent path + [`conversation-intent-policy-mvp.md`](../conversation-intent-policy-mvp.md); legacy appendix still in code for non-demo businesses | `architecture/deprecated/` |

---

## Completed slice plans (historical)

| Document | Current path | Slice status | Target tier |
|----------|--------------|--------------|-------------|
| T11 AI orchestration plan | [`../../project-status/t11-ai-orchestration-plan.md`](../../project-status/t11-ai-orchestration-plan.md) | T11 done | `project-status/historical/` |
| T12 lead/notification plan | [`../../project-status/t12-lead-notification-plan.md`](../../project-status/t12-lead-notification-plan.md) | T12 done | `project-status/historical/` |
| T13 n8n workflow plan | [`../../project-status/t13-n8n-workflow-plan.md`](../../project-status/t13-n8n-workflow-plan.md) | T13.1–T13.5 done; T13.6–T13.7 deferred | `project-status/historical/` |

---

## Abandoned / non-canonical experiments

| Item | Location | Reason |
|------|----------|--------|
| `My workflow 2` n8n export | `n8n/workflows/My_workflow.json` | Ad-hoc; not ops runbook canonical |
| Duplicate todo task copies | *(removed 2026-05-27)* | CIP-A/B, t13 todo duplicates deleted in archivist sweep |

---

## Historical migrations & ops notes

| Document | Current path | Reason | Target tier |
|----------|--------------|--------|-------------|
| n8n Deployment Plan (T13.0 design) | [`../../ops/n8n-deployment-plan.md`](../../ops/n8n-deployment-plan.md) | Pre-implementation design; T13.0-impl done | `ops/archived/` |
| Post–T13.5 stabilization | [`../../ops/post-t13-5-stabilization.md`](../../ops/post-t13-5-stabilization.md) | One-time gate checklist | `ops/archived/` |

---

## Duplicate clusters (consolidate later; do not delete)

| Cluster | Files | Recommendation |
|---------|-------|----------------|
| Telegram ingress mapping | `ops/telegram-customer-ingress.md` + `ops/n8n-workflow-telegram-customer-ingress.md` | Merge mapping into workflow runbook or cross-link only |
| Project “current state” | `current-state.md` + `engineering-archive.md` + canonical map | **canonical map** for architecture; **current-state** for snapshot; archive for history |
| Intent / pre-sales | `conversation-intent-policy-mvp.md` + `technical-pre-sales-behavior-mvp.md` | Keep intent as runtime-derived; deprecate technical-pre-sales doc |

---

## Superseded by specs (do not duplicate in docs/)

| Topic | Canonical contract |
|-------|-------------------|
| Webhook payload | `specs/api/webhooks.md` |
| Prompt section order | `specs/architecture/prompt-builder-rules.md` |
| Database schema | `specs/database/database-schema.md` |
| MVP scope | `specs/mvp/mvp-scope.md` |

---

## Migration

See [`../../MIGRATION-PLAN.md`](../../MIGRATION-PLAN.md) Phase 1.3–1.5. No physical moves required to use this index.
