# Runtime Baseline Remediation Plan

**Doc status:** implementation sequencing plan (no fixes executed)  
**Phase:** Engineering Reproducibility + Deployment Portability  
**Input audit:** [`runtime-reproducibility-audit.md`](runtime-reproducibility-audit.md)  
**Date:** 2026-05-27

---

## Goal
Transform current runtime into a **reproducible, rollback-safe, repo-governed operational baseline** without architecture rewrite or feature expansion.

**Success measurement:** a clean clone can reproduce backend + migration + canonical n8n paths using tracked artifacts and docs-only steps, and rollback can be executed as one atomic bundle.

---

## Scope and constraints

### In scope

1. git truth normalization
2. tracked/untracked cleanup sequencing
3. canonical repo baseline stabilization
4. migration reproducibility
5. workflow governance stabilization
6. runtime/export parity
7. docker portability preparation (templates + docs discipline only)
8. deployment reproducibility readiness
9. rollback-safe commit grouping
10. implementation freeze boundaries

### Out of scope

- backend feature changes
- AI orchestration redesign
- PromptBuilder redesign
- Kubernetes/distributed runtime
- multi-agent runtime systems
- n8n workflow logic expansion
- creating new Docker artifacts beyond baseline tracking/governance

---

## Spec alignment

- In MVP: **yes** (stability, reproducibility, deployment safety are required for MVP operations)
- Primary specs:
  - `specs/mvp/mvp-scope.md`
  - `specs/architecture/system-architecture.md`
  - `specs/architecture/backend-architecture.md`
  - `specs/architecture/n8n-architecture.md`
  - `specs/database/database-architecture.md`
  - `specs/api/webhooks.md`
- Governing rules:
  - `AGENTS.md` (specs-first, small reviewable slices, no architecture rewrite)
  - `runtime-reproducibility-audit.md` reviewer criteria G1–G7

---

## Reproducibility and rollback contracts (must be defined first)

### Reproducible deployment unit (RDU)

RDU is valid only when all are tracked and versioned together:

1. backend runtime code required for webhook→AI path
2. Alembic chain + config for active schema
3. canonical n8n workflow exports for active paths
4. runtime templates (`.env.example`, compose/config templates without secrets)
5. canonical docs/runbooks that execute the deployment

### Rollback unit (RBU)

Rollback is one atomic bundle:

`git tag/commit` + `alembic revision target` + `n8n workflow export version` + `env template version` + rollback runbook reference.

No partial rollback is allowed for production-like verification.

---

## Execution phases

## Phase 0 — Freeze and policy gate

**Purpose:** prevent drift while baseline is normalized.

### Actions

- Declare **runtime freeze**:
  - no backend logic edits
  - no migration edits
  - no n8n workflow behavior edits
- Declare **workflow freeze**:
  - no runtime n8n UI edits except export/snapshot operations
  - no new ad-hoc workflow files
- Define and approve RDU/RBU contracts (above).

### Validation checkpoint V0

- Freeze note committed in docs.
- RDU/RBU accepted by reviewer.

### Rollback checkpoint R0

- If freeze cannot be enforced, stop remediation and return to audit-only mode.

### No-go conditions

- active feature work continues in parallel on same runtime artifacts
- inability to identify current active runtime workflow IDs

---

## Phase 1 — Inventory freeze with provenance

**Purpose:** capture exact runtime truth before normalization.

### Actions

- Inventory and classify all deployment-critical artifacts:
  - backend runtime files
  - `backend/alembic/**` and `alembic.ini`
  - n8n canonical workflow exports (T13/T14 active paths)
  - env template files
  - ops runbooks used for deployment/recovery
- Add provenance per artifact:
  - `tracked`
  - `runtime-only`
  - `host-only`
  - `UI-only`
  - `unknown-owner`

### Validation checkpoint V1

- Provenance matrix committed and reviewed.
- All critical artifacts have owners.

### Rollback checkpoint R1

- If inventory is incomplete, revert to Phase 0 freeze; do not import partial baseline.

### No-go conditions

- any critical path artifact remains `unknown-owner`
- inability to map runtime workflow to export filename/version

---

## Phase 2 — Git truth normalization (baseline import)

**Purpose:** make repo truth represent runtime truth for critical paths.

### Actions

- Track canonical backend baseline required for active runtime path.
- Track Alembic chain/config required for active schema.
- Track canonical n8n artifacts:
  - `docker-compose.yml`
  - `.env.example` (template only)
  - canonical workflow exports (scrubbed, versioned)
- Track `specs/**` and critical docs if currently detached/untracked.
- Resolve tracked/untracked classification drift for `tasks/` and deployment-critical docs.

### Safe commit boundaries

1. **C1:** policy + provenance docs only  
2. **C2:** backend + alembic baseline tracking only  
3. **C3:** n8n canonical exports + template files only  
4. **C4:** specs/docs/task-state reconciliation only

No commit mixes backend baseline import with workflow governance changes.

### Validation checkpoint V2

- `git status` clean for canonical baseline scope.
- Reviewer confirms G1, G2, G3, G4 evidence exists in tracked state.

### Rollback checkpoint R2

- Revert last normalization commit if unrelated files are swept in.
- Re-open artifact classification for that boundary only.

### No-go conditions

- secrets appear in tracked artifacts
- canonical export cannot be produced scrubbed
- migration chain still not fully tracked after C2

---

## Phase 3 — Workflow governance stabilization

**Purpose:** ensure n8n runtime can be restored from reviewed repo artifacts.

### Actions

- Define canonical naming/version policy for n8n exports:
  - workflow purpose
  - version stamp
  - runtime ID mapping registry
- Mark ad-hoc exports as non-canonical; archive or quarantine.
- Enforce “repo export = source of truth” for active operational workflows.

### Validation checkpoint V3

- Every active runtime workflow has:
  - one canonical tracked export
  - version mapping entry
  - rollback reference

### Rollback checkpoint R3

- If mapping fails for any active workflow, keep freeze and do not proceed to clone gate.

### No-go conditions

- active workflow exists only in UI state
- multiple conflicting exports claim canonical status

---

## Phase 4 — Migration reproducibility gate

**Purpose:** prove schema state is reproducible from tracked repo only.

### Actions

- Execute migration replay from clean environment using tracked `alembic` artifacts.
- Verify expected target revision for current runtime.
- Document downgrade posture (supported/unsupported paths) for rollback contract.

### Validation checkpoint V4

- replay success logged with expected revision chain
- downgrade posture explicitly documented

### Rollback checkpoint R4

- If replay fails, revert migration-baseline commits and re-import exactly missing migration artifacts.

### No-go conditions

- any runtime revision not present in tracked history
- downgrade unknown for operational rollback scenarios

---

## Phase 5 — Clean-clone reproducibility gate (hard pass/fail)

**Purpose:** validate deployment portability from tracked baseline.

### Actions

- Perform clean clone trial (no hidden local state).
- Execute documented steps only:
  - env template provisioning (without real secrets in repo)
  - migration replay
  - backend startup
  - n8n startup with canonical workflows
- Validate critical path smoke:
  - webhook receives normalized payload
  - backend returns expected envelope
  - workflow parity with tracked export

### Validation checkpoint V5 (must all pass)

- G1–G7 from audit reviewer section pass.
- Reproducibility report committed with command log + expected outputs.

### Rollback checkpoint R5

- If any step requires operator memory or undocumented host tweaks, fail gate and return to Phase 2/3 docs/governance fixes.

### No-go conditions

- clean clone depends on unstaged local scripts/files
- secret values required in repo to pass
- workflow behavior differs from canonical export

---

## Phase 6 — Deployment readiness packaging (no new infra)

**Purpose:** prepare conservative portability baseline for implementation freeze exit.

### Actions

- Consolidate docs:
  - runtime architecture anchor
  - migration recovery path
  - workflow governance rules
  - rollback procedure (atomic RBU)
- Define freeze exit criteria and sign-off checklist.
- Tag baseline candidate for reproducible release.

### Validation checkpoint V6

- Reviewer sign-off: reproducible baseline ready.
- Rollback rehearsal planned and linked to atomic RBU.

### Rollback checkpoint R6

- If docs contradict baseline artifacts, freeze remains active and release candidate rejected.

### No-go conditions

- unresolved contradiction between canonical docs and tracked artifacts
- no tagged baseline bundle

---

## Dependency ordering

`Phase 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6`

Hard dependencies:

- Phase 2 blocked by missing RDU/RBU approval.
- Phase 3 blocked by incomplete baseline import.
- Phase 4 blocked by absent tracked migration chain.
- Phase 5 blocked by unresolved workflow canonicalization.
- Phase 6 blocked by failed clean-clone gate.

Parallelization rule:

- only documentation drafting can run in parallel with validation evidence gathering.
- artifact import and governance normalization remain sequential for rollback clarity.

---

## Runtime freeze rules

During remediation window:

1. no feature PRs touching deployment-critical paths (`backend runtime`, `alembic`, `n8n canonical workflows`)
2. no direct runtime UI workflow edits unless the result is immediately exported and reconciled
3. no migration creation or modification beyond baseline capture
4. no prompt/AI behavior changes for remediation commits

Violation => automatic freeze reset to Phase 0.

---

## Workflow freeze rules

1. single canonical export per active workflow path
2. versioned filename and runtime ID map required
3. `active:false` export policy is acceptable only if runtime mapping doc is current
4. ad-hoc exports (e.g., personal/test files) must be quarantined from canonical path

---

## Validation matrix

| Check | Gate | Evidence |
|---|---|---|
| RDU/RBU defined | V0 | policy section + reviewer approval |
| Artifact provenance complete | V1 | inventory matrix |
| Baseline tracked | V2 | clean `git status`, tracked file lists |
| Workflow canonicalization | V3 | export map table |
| Migration replayable | V4 | replay log + revision proof |
| Clean clone reproducible | V5 | command transcript + smoke checks |
| Docs/rollback package coherent | V6 | signed release checklist |

---

## Reproducibility milestones

### M1 — Contracted baseline
RDU/RBU accepted; freeze active.

### M2 — Tracked baseline
Backend + Alembic + n8n canonical artifacts tracked and reviewable.

### M3 — Governed workflows
Runtime workflows map deterministically to canonical exports.

### M4 — Replayable schema
Migration chain proven from clean environment.

### M5 — Portable deployment candidate
Clean-clone gate passes using docs-only steps.

### M6 — Rollback-safe baseline
Atomic rollback bundle validated and documented.

---

## Risk controls by focus area

| Focus area | Main risk | Control |
|---|---|---|
| git truth normalization | partial/stale import | strict commit boundaries C1–C4 |
| tracked/untracked cleanup | accidental broad sweep | provenance-first + reviewer gate |
| baseline stabilization | hidden runtime dependencies | clean-clone gate V5 |
| migration reproducibility | schema drift/rollback ambiguity | V4 replay + downgrade posture |
| workflow governance | UI/repo divergence | canonical mapping + freeze |
| runtime/export parity | non-deterministic state | versioned exports + parity checks |
| docker portability prep | host-coupled assumptions | template-only docs and explicit host assumptions |
| deployment readiness | false confidence | hard pass/fail G1–G7 |
| rollback-safe grouping | cross-layer rollback mismatch | atomic RBU contract |
| freeze boundaries | ongoing feature churn | freeze reset enforcement |

---

## Recommended task list

### P0 — Critical path

| ID | Task | Depends on | Done when | Suggested skill |
|----|------|------------|-----------|-----------------|
| RB-0 | Define/approve RDU + RBU contracts and freeze policy | — | V0 passed | alpstein-reviewer |
| RB-1 | Produce artifact provenance matrix (repo/runtime/UI/host owners) | RB-0 | V1 passed | alpstein-reviewer |
| RB-2 | Import canonical backend + Alembic baseline into tracked git | RB-1 | V2 backend+DB checks pass | alpstein-backend-engineer + alpstein-migration-engineer |
| RB-3 | Canonicalize n8n export governance and runtime mapping | RB-2 | V3 passed | alpstein-n8n-integration-engineer |
| RB-4 | Run migration reproducibility gate from clean env | RB-2 | V4 passed | alpstein-migration-engineer |
| RB-5 | Execute clean-clone reproducibility gate (hard pass/fail) | RB-3, RB-4 | V5 passed (G1–G7) | alpstein-reviewer |

### P1 — MVP complete

| ID | Task | Depends on | Done when | Suggested skill |
|----|------|------------|-----------|-----------------|
| RB-6 | Reconcile deployment-critical docs/tasks topology | RB-5 | V6 doc coherence pass | alpstein-reviewer |
| RB-7 | Tag rollback-safe baseline bundle and release checklist | RB-6 | M6 reached | alpstein-reviewer |

### P2 — Defer

| ID | Task | Depends on | Done when |
|----|------|------------|-----------|
| RB-8 | Optional non-critical docs/archive cleanup | RB-7 | post-baseline hygiene complete |

---

## Safe commit grouping

1. **Commit A:** RDU/RBU policy + freeze rules + provenance template  
2. **Commit B:** backend/alembic canonical baseline tracking  
3. **Commit C:** n8n canonical exports + mapping policy + template files  
4. **Commit D:** migration replay evidence + clean-clone gate evidence  
5. **Commit E:** docs/task reconciliation for deployment-critical paths  
6. **Commit F:** rollback-safe baseline tag/checklist docs

Each commit must be independently reviewable and reversible.

---

## No-go master conditions

Stop and do not continue implementation if any occur:

1. migration chain/config for active runtime schema is not fully tracked
2. active operational workflow not represented by canonical tracked export
3. clean-clone run requires undocumented host memory/manual hacks
4. remediation requires storing real secrets in repository artifacts
5. runtime freeze cannot be enforced

---

## Implementation freeze exit criteria

Freeze can be lifted only when:

- M1–M6 all reached
- G1–G7 all satisfied
- reviewer confirms rollback-safe baseline is reproducible from tracked artifacts only

Until then: remediation only, no feature expansion.

---

## Recommended next task

**RB-0** — Approve RDU/RBU contracts and freeze policy first; no artifact import should begin before this gate, to avoid false reproducibility confidence.

