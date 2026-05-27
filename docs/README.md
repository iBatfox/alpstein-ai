# Alpstein AI — Documentation Index

**Doc status:** canonical (navigation layer)  
**As-of:** 2026-05-27  
**Phase:** 1.2 — documentation topology stabilization

This index defines **where to read** and **what tier of truth** each area represents. It does not replace runtime evidence.

---

## Start here

**START HERE →** [`architecture/canonical-runtime-architecture.md`](architecture/canonical-runtime-architecture.md)

| Question | Read first |
|----------|------------|
| What is the **actual runtime architecture** today? | [`architecture/canonical-runtime-architecture.md`](architecture/canonical-runtime-architecture.md) |
| What shipped? | [`project-status/completed.md`](project-status/completed.md) |
| What is the current snapshot? | [`project-status/current-state.md`](project-status/current-state.md) |
| What is next? | [`project-status/next-steps.md`](project-status/next-steps.md) |
| How do I run n8n / Telegram / backend? | [`ops/`](ops/) runbooks (see [`ops/README.md`](ops/README.md) if present) |
| What are API/DB contracts? | [`specs/`](../specs/) (contracts; runtime wins on conflict) |

---

## Runtime truth hierarchy

When documents conflict, trust in this order:

1. **Runtime code** — `backend/`, `n8n/workflows/`
2. **Orchestration layer** — backend services (`WebhookMessageService`, `AiReplyOrchestrationService`, `PromptBuilderService`) + n8n normalize/runbooks (how code is used in ops)
3. **Canonical runtime map** — [`architecture/canonical-runtime-architecture.md`](architecture/canonical-runtime-architecture.md)
4. **Project status (current tier)** — `project-status/current-state.md`, `completed.md`, `next-steps.md`
5. **Ops runbooks** — `docs/ops/` (production paths)
6. **Runtime-derived architecture docs** — `docs/architecture/*.md` (behavior detail; verify against map)
7. **Specs** — `specs/` (intended contracts; mark drift if implementation differs)
8. **Historical / deprecated** — `project-status/` plans, `architecture/deprecated/`, slice plans

Chat history is **not** project state.

---

## Documentation tiers (target layout)

Physical migration is **incremental** — see [`MIGRATION-PLAN.md`](MIGRATION-PLAN.md). Current paths remain valid until moved.

```text
docs/
├── README.md                          ← this file
├── MIGRATION-PLAN.md                  ← tier migration plan
├── architecture/
│   ├── README.md                      ← architecture index
│   ├── canonical-runtime-architecture.md   ← PRIMARY canonical runtime map
│   ├── canonical/                     ← future: stable platform architecture
│   ├── runtime/                     ← future: runtime-derived behavior docs
│   ├── deprecated/                    ← archive index (no deletes yet)
│   └── experiments/                 ← future: non-production experiments
├── conversational/                    ← future: prompts, orchestration, policies
├── ops/
│   ├── (current runbooks at ops root)
│   ├── production/                    ← future: live runbooks
│   ├── migration/                     ← future: migration/recovery guides
│   └── archived/                      ← future: retired ops notes
└── project-status/
    ├── (current status at root)
    ├── current/                       ← future: living status docs
    └── historical/                    ← future: audits, slice plans, archive
```

**Specs** (`specs/`) remain the contract layer outside `docs/` — not relocated in Phase 1.2.

---

## Deprecated and experimental areas

| Area | Status | Index |
|------|--------|-------|
| Early MVP backlog checklists | deprecated | [`project-status/historical/backlog.md`](project-status/historical/backlog.md) |
| Superseded design drafts | deprecated | [`architecture/deprecated/README.md`](architecture/deprecated/README.md) |
| Completed slice plans (T11–T13) | archived / historical | [`project-status/documentation-topology-status.md`](project-status/documentation-topology-status.md) |
| Ad-hoc n8n export `My_workflow.json` | experimental / non-canonical | repo `n8n/workflows/` |

Do not use deprecated docs for planning or onboarding.

---

## Topology and drift

Full inventory, duplicate clusters, and migration steps:

→ [`project-status/documentation-topology-status.md`](project-status/documentation-topology-status.md)

---

## Agent rules

Implementation and doc updates follow [`AGENTS.md`](../AGENTS.md). Archivist sweeps use skill `alpstein-project-archivist`.
