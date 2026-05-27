# Alpstein Project Archivist — Reference

Read only sections relevant to the sweep scope.

## Canonical sources of truth

| Topic | Canonical path | Archivist role |
|-------|----------------|----------------|
| **Runtime architecture** | `docs/architecture/canonical-runtime-architecture.md` | Primary runtime map; wins over other docs on behavior |
| Documentation topology | `docs/project-status/documentation-topology-status.md` | Tier inventory and migration state |
| Documentation index | `docs/README.md` | Navigation and truth hierarchy |
| API / webhook contract | `specs/api/webhooks.md` | Do not edit; link from status docs |
| Prompt section order | `specs/architecture/prompt-builder-rules.md` | Note superseded drafts |
| Intent behavior | `docs/architecture/conversation-intent-policy-mvp.md` | Sync status when CIP tasks close |
| Greeting | `docs/architecture/greeting-orchestration-mvp.md` | Sync when greeting tasks close |
| n8n Telegram ingress | `docs/ops/n8n-workflow-telegram-customer-ingress.md` | Ops verification evidence |
| What shipped | `docs/project-status/completed.md` | Append on task acceptance |
| Snapshot | `docs/project-status/current-state.md` | Regenerate from evidence |
| What's next | `docs/project-status/next-steps.md` | Single queue, no contradictions |
| Engineering history | `docs/project-status/engineering-archive.md` | Milestone updates |
| Architecture decisions | `docs/project-status/decisions.md` | ADRs only |
| Execution truth | `tasks/done/*`, `tasks/todo/*`, `tasks/in-progress/*` | Hygiene + sync |

## Project-status file roles

```text
docs/project-status/
  current-state.md             ← regeneratable snapshot (quarterly or after major slice)
  completed.md                 ← append-only changelog of accepted work
  next-steps.md                ← open queue + recommended next task
  engineering-archive.md       ← long-form history with explicit status labels
  historical/engineering-audit-report.md ← audit findings; use contradiction checklist
  decisions.md                 ← ADR log
  historical/backlog.md        ← stale checklist; historical only
  t*-*.md                      ← slice plans; banner if superseded
```

## Evidence collection commands

Run as needed for the sweep (from repo root):

```bash
# Task folder inventory
find tasks/todo tasks/in-progress tasks/done -name '*.md' | sort

# Duplicate detection (same basename in todo and done)
comm -12 \
  <(find tasks/todo -name '*.md' -exec basename {} \; | sort) \
  <(find tasks/done -name '*.md' -exec basename {} \; | sort)

# Test count (backend)
cd backend && pytest --collect-only -q 2>/dev/null | tail -1

# Migration head
ls backend/alembic/versions/*.py 2>/dev/null | sort

# Recent done tasks
ls -t tasks/done/*.md | head -20
```

Adjust paths if backend layout differs. Record commands actually run in the archivist report.

## current-state.md section template

Use this structure when regenerating:

```markdown
# Alpstein AI — Current State

**As-of:** YYYY-MM-DD

## Project Phase
[One paragraph: phase, main blocker if any]

## Specifications
[Complete vs gaps — specs layer only]

## Backend
### Existing
- [bullet list from code + done tasks]
### Missing / deferred
- [honest gaps only]

## AI Layer
### Existing
- …
### Missing / deferred
- …

## n8n / integrations
### Existing
- …
### Missing / deferred
- …

## Database
[Migrations rev range, entities, known deferrals]

## Tests
[N count, key suites]

## Governance
[AGENTS.md, skills list — factual]
```

Keep concise. Prefer bullets over narrative.

## completed.md entry template

```markdown
- [Past tense deliverable] — [`path/to/key/file`](relative/path); [evidence: N tests green / exec ID / gate passed].
```

One deliverable per bullet. Cite task file when helpful: [`tasks/done/Txx-….md`](../../tasks/done/…).

## next-steps.md rules

1. **Top:** `## Recommended next task: **ID**` with one-line rationale.
2. **Done callouts:** brief pointers to `tasks/done/` — not full re-documentation.
3. **Open tables:** only IDs still in `tasks/todo/` or explicitly deferred.
4. **Remove** sections whose work is in `tasks/done/` (e.g. "spec only — not implemented" after CIP-B done).
5. **Reference table** at bottom for ops/architecture docs — links only.

## Archive candidates (check each sweep)

Known duplicate or obsolete patterns:

| Pattern | Action |
|---------|--------|
| Task in both `todo/` and `done/` | Remove or move todo copy; keep `done/` |
| `tasks/todo/CIP-*.md` when CIP done in `done/` | Archive todo |
| `tasks/todo/t13-n8n-workflow-slice.md` when done copy exists | Archive todo |
| `docs/project-status/historical/backlog.md` all open | Banner obsolete or merge into next-steps |
| `docs/architecture/deprecated/t11-prompt-builder-design.md` | Banner: superseded by `specs/architecture/prompt-builder-rules.md` |
| Raw user-prompt task filenames in `todo/` | Rename on next touch; do not block sweep |

## Status label glossary

Use consistently in `engineering-archive.md` and sweep reports:

| Label | Meaning |
|-------|---------|
| **implemented** | Shipped and verified in code/ops |
| **partial** | Started or dev-only; not production-complete |
| **deferred** | Explicitly out of current slice; documented reason |
| **planned** | Spec or task exists; no implementation |
| **obsolete** | Superseded; keep for history with banner |
| **experimental** | Dev-only or smoke; not production policy |

## Milestone triggers for engineering-archive.md

Update archive when any of these close:

- Major slice (T11, T12, T13, T14, CIP-A/B/C/D)
- Infrastructure milestone (n8n HTTPS, Telegram ingress, Langfuse)
- Demo separation or data refactor affecting onboarding story
- Documentation restructuring (per audit §12)

Minor task closures → update `completed.md` + `current-state.md` only unless user requests full archive pass.

## Sibling skills

| Skill | When to use instead |
|-------|---------------------|
| `alpstein-task-planner` | Decompose new work; do not plan in archivist sweep |
| `alpstein-reviewer` | Review code diffs; archivist reviews doc truth only |
| `alpstein-backend-engineer` | Fix code issues found during evidence gathering |
| `alpstein-n8n-integration-engineer` | Verify n8n exports and ops runbooks in code |

## AGENTS.md sync checklist

After task acceptance, confirm:

- [ ] `tasks/done/` contains accepted task file
- [ ] No duplicate in `tasks/todo/` or `tasks/in-progress/`
- [ ] `completed.md` entry added
- [ ] `current-state.md` reflects new Existing/Missing
- [ ] `next-steps.md` promoted next task; removed stale "not implemented"
- [ ] Superseded plan docs bannered if applicable

## Known drift patterns (2026-05 audit)

Use as regression checklist:

- CIP marked "not implemented" in next-steps while CIP-B in done
- current-state says T13 missing / stub reply / 252 tests
- backlog.md contradicts completed.md
- Langfuse tag `demo_barbershop_001` vs doc `alpstein_ai_demo_001`
- Operator context docs vs History Safety (HF-1) not yet implemented

Fix docs to match evidence; log code fixes as follow-up tasks.
