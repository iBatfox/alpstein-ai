# Documentation Tier Migration Plan

**Doc status:** canonical (migration plan)  
**As-of:** 2026-05-27  
**Phase:** 1.2 — structure first; **no bulk file moves** in this phase

Primary anchor: [`architecture/canonical-runtime-architecture.md`](architecture/canonical-runtime-architecture.md)

---

## Principles

1. **Runtime truth unchanged** — moves are path-only; no content rewrites that imply new behavior.
2. **Git history stability** — prefer `git mv` in small batches; one slice per PR.
3. **Entrypoints stable** — leave symlinks or stub README redirects at old paths until consumers updated.
4. **Markers before moves** — add `Doc status:` headers before relocating files.
5. **Low-risk first** — move empty-tier placeholders and clearly obsolete docs before large clusters.

---

## Phase 1.2 (complete in this slice)

- [x] Create tier directory scaffolding + README entrypoints
- [x] Create `docs/README.md`, `docs/architecture/README.md`
- [x] Create `docs/architecture/deprecated/README.md` (archive candidate list)
- [x] Add canonicality markers to priority docs
- [x] Publish `project-status/documentation-topology-status.md`

---

## Phase 1.3 — low-risk moves (recommended next)

| From | To | Risk | Preconditions |
|------|-----|------|----------------|
| `project-status/backlog.md` | `project-status/historical/backlog.md` | Low | Redirect note in old path stub |
| `project-status/t11-prompt-builder-design.md` | `architecture/deprecated/t11-prompt-builder-design.md` | Low | Already superseded banner |
| `project-status/t11-ai-orchestration-plan.md` | `project-status/historical/t11-ai-orchestration-plan.md` | Low | Slice done; update links in 3–5 files |
| `project-status/t12-lead-notification-plan.md` | `project-status/historical/t12-lead-notification-plan.md` | Low | Same |
| `project-status/engineering-audit-report.md` | `project-status/historical/engineering-audit-report.md` | Low | Point `current-state` to canonical map |

**Do not move yet:** `conversation-intent-policy-mvp.md`, ops runbooks, `canonical-runtime-architecture.md` (keep visible path).

---

## Phase 1.4 — conversational cluster (medium risk)

Group runtime-derived behavior docs under `docs/conversational/`:

| Current path | Target tier |
|--------------|-------------|
| `architecture/greeting-orchestration-mvp.md` | `conversational/orchestration/` |
| `architecture/conversation-intent-policy-mvp.md` | `conversational/policies/` |
| `architecture/pre-sales-contact-ownership.md` | `conversational/policies/` |
| `architecture/technical-pre-sales-behavior-mvp.md` | `architecture/deprecated/` (legacy appendix era) |
| `architecture/langfuse-tracing.md` | `architecture/runtime/` |

Update: canonical map § references, AGENTS.md spec lists (if any), Cursor skill paths.

---

## Phase 1.5 — ops tier (medium risk)

| Current path | Target |
|--------------|--------|
| `ops/n8n-runtime-start.md`, `n8n-https-reverse-proxy.md`, `database-recovery.md` | `ops/production/` |
| `ops/n8n-deployment-plan.md`, `post-t13-5-stabilization.md` | `ops/archived/` |
| `ops/telegram-customer-ingress.md` | Keep or merge with `n8n-workflow-telegram-customer-ingress.md` (duplicate cluster) |

---

## Phase 2 — canonical runtime subdirectory (optional)

If `canonical-runtime-architecture.md` grows or splits:

- `architecture/canonical/runtime-architecture.md` — main map
- `architecture/canonical/boundaries.md` — n8n/backend/DB boundaries extract

Only after Phase 1.3 link sweep. **Single file is sufficient for MVP.**

---

## Link update checklist (run before each move batch)

```bash
# Find references to a doc before git mv
rg -l 'backlog\.md|t11-prompt-builder-design' docs specs tasks .cursor
```

After each batch:

- [ ] `docs/README.md` paths
- [ ] `documentation-topology-status.md`
- [ ] `canonical-runtime-architecture.md` source index
- [ ] `project-status/current-state.md`
- [ ] `engineering-archive.md` (if historical links)

---

## Out of scope

- Moving `specs/` into `docs/`
- Renaming `tasks/` tree
- Deleting deprecated files
- Rewriting architecture content
