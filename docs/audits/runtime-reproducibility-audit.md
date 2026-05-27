# Runtime Reproducibility Audit

**Doc status:** audit (evidence-based, no implementation)  
**As-of:** 2026-05-27  
**Scope:** Runtime truth vs repository truth for reproducibility and deployment portability.

---

## 1) Executive finding

Repository truth and runtime truth are materially diverged. The canonical runtime docs describe a complete backend + n8n Telegram path, but the tracked git baseline currently includes only a small subset of backend/n8n artifacts and a large untracked runtime footprint. Reproducible deployment and safe rollback are therefore **not guaranteed** from repository state alone.

---

## 2) Runtime inventory (from canonical + ops docs)

### Backend runtime (documented as running)
- FastAPI webhook orchestration path with AI, PromptBuilder, lead/notification logic, HF-1 safety.
- Alembic migration chain `0001`..`0007`.
- PromptBuilder 8-section assembly and business-aware task instructions (P0/P1 done, HF-1 done).

### n8n runtime (documented as running)
- Test workflow path (T13) and Telegram customer ingress path (T14), with owner-notify branching.
- Runtime workflow IDs are managed in n8n UI; repo exports are commonly `active: false`.
- Host/container assumptions: docker-compose v1.29, gateway routing (`172.20.0.1:8010`), UFW allowlist rule.

### Observability / data
- PromptRun persistence in DB.
- Langfuse partial (dev/internal) with known metadata/tag drift.

---

## 3) Tracked vs untracked classification

### High-level git state (evidence)
- `tracked_changes`: **3** (all tracked deletions in `tasks/in-progress/`).
- `untracked_total`: **187**.
- Untracked by top-level prefix (largest):
  - `backend`: **78**
  - `tasks`: **67**
  - `n8n`: **6**
  - `specs`: **1** (entire tree appears untracked at root)
  - docs/additional root files also untracked.

### Backend classification
- Tracked backend files count: **13**.
- Tracked backend set is only prompt/orchestration-related service/test files (not full application baseline).
- Untracked backend includes app entrypoints, db layer, schemas, models, most services, requirements, scripts, and full test suite.

**Result:** backend runtime is partially outside tracked git history.

### n8n classification
- Tracked n8n workflows:
  - `n8n/workflows/backups/alpstein-incoming-message-test_gate2_2026-05-25.json`
  - `n8n/workflows/t13_workflow1_test_webhook_skeleton.json`
- Untracked n8n workflows:
  - `n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json`
  - `n8n/workflows/My_workflow.json`
- Untracked n8n runtime artifacts include compose and env examples.

**Result:** workflow governance and export parity are incomplete.

### Docs/tasks classification signals
- Canonical/runtime docs exist and are detailed.
- Task lifecycle drift visible: tracked deletions in `tasks/in-progress` while many task docs exist untracked under `tasks/done`.

---

## 4) Alembic / migration reproducibility

### Evidence
- Canonical map and `docs/ops/database-recovery.md` reference migration chain `0001`..`0007`.
- `git ls-files 'backend/alembic/versions/*.py'` currently returns no tracked migration files.
- `backend/alembic/` and `backend/alembic.ini` are untracked.

### Risk
- Migration replay cannot be guaranteed from tracked baseline.
- Fresh environment DB bootstrap from repo alone is not reproducible.
- Rollback sequencing is unsafe if revision history is not fully tracked.

---

## 5) Runtime-only dependencies and environment reproducibility

### Evidence
- Runtime docs rely on host/network specifics:
  - docker-compose v1.29
  - Docker subnet/gateway coupling (`172.20.0.1`)
  - UFW allow rule from container subnet to backend port
- `git ls-files '*env*'` shows only `docs/ops/n8n-env-credential-checklist.md` as tracked env-related artifact.
- `.env.example` files are untracked.

### Risk
- New host/environment cannot be reproduced deterministically.
- Runtime success depends on undocumented/unstaged operator state.
- Portability across Linux hosts/cloud VMs is weak.

---

## 6) n8n workflow governance and export discipline risks

### Evidence
- Canonical docs explicitly note runtime-vs-repo drift and `active:false` exports.
- Telegram T14 workflow export used in docs is untracked.
- Ad-hoc `My_workflow.json` exists untracked (non-canonical).

### Risk
- Runtime workflow state may diverge from reviewed repo state.
- Incident rollback cannot rely on repo-tagged workflow artifacts.
- Governance gates (T14.6 export/source-of-truth) remain open in effect.

---

## 7) Specs/docs/tasks drift

### Evidence
- Canonical runtime map references broader code/migration surface than currently tracked.
- `docs/project-status/next-steps.md` contains duplicate metadata header blocks and stale link path to `engineering-audit-report.md` root path (now historical path).
- Task lifecycle mismatch: `tasks/in-progress` tracked files shown as deleted while related `tasks/done` copies are untracked.

### Risk
- AI/engineer onboarding may follow inconsistent source paths.
- Task audit trail is not reliably represented in tracked history.

---

## 8) Rollback safety risks

1. **Missing tracked migration baseline**: DB rollback/replay cannot be trusted from repo.
2. **Workflow state outside git**: n8n rollback depends on UI/runtime state and ad-hoc exports.
3. **Env/network coupling**: rollback success depends on host firewall/network assumptions not captured as tracked infra baseline.
4. **Partial code baseline**: restoring a prior commit may not reflect the runtime actually running.

---

## 9) Deployment reproducibility blockers

1. Backend full source tree not tracked in canonical baseline.
2. Alembic chain and config not tracked.
3. n8n compose/env/workflow exports not fully tracked.
4. Specs tree appears untracked from current repo state.
5. Task lifecycle metadata partially detached from tracked history.

---

## 10) Canonical repo baseline proposal (no implementation, proposal only)

Define a baseline that must be fully tracked before claiming reproducibility:

1. **Backend minimum baseline**
   - `backend/app/**` full runtime code
   - `backend/alembic/**` + `backend/alembic.ini`
   - dependency lock/baseline (`requirements.txt`)
2. **n8n minimum baseline**
   - `n8n/docker-compose.yml`
   - `n8n/.env.example` templates
   - canonical workflow exports for T13/T14 (scrubbed, versioned)
3. **Contracts/specs baseline**
   - full `specs/**` tracked
4. **Task/docs governance baseline**
   - `tasks/{todo,in-progress,done}` consistent tracked state
   - docs links/paths aligned to current topology and historical tiering

---

## 11) Cleanup sequencing proposal (no implementation, proposal only)

1. **Inventory freeze**
   - Snapshot current runtime code/workflow/migration/env artifacts.
2. **Baseline import to git**
   - Bring backend/alembic/n8n/specs canonical artifacts into tracked history.
3. **Reproducibility gate**
   - Verify fresh clone can run migrations and boot backend+n8n with docs-only instructions.
4. **Workflow governance gate**
   - Enforce canonical workflow export discipline (T14.6-style gate).
5. **Task/docs reconciliation**
   - Resolve in-progress/done tracking mismatches; patch broken historical links.
6. **Rollback rehearsal**
   - Document and test rollback path using tracked artifacts only.

---

## 12) Deployment portability blockers (priority)

### Critical
- Untracked backend runtime baseline.
- Untracked alembic migration chain.
- Untracked T14 workflow export(s) used in operational docs.

### Important
- Env templates and compose artifacts not consistently tracked.
- Task lifecycle tracking drift (`in-progress` deletions vs untracked `done` entries).
- Docs links/path hygiene gaps (`next-steps` stale reference path).

### Minor
- Non-canonical ad-hoc workflow exports (`My_workflow.json`) still present.

---

## 13) Evidence consulted

- `git status --porcelain=v1` (tracked/untracked classification)
- `git ls-files` counts and listings:
  - `backend/**`, `n8n/**`, `docs/**`, `tasks/**`
  - `backend/alembic/versions/*.py`
  - `n8n/workflows/*.json`
  - `*env*`
- `docs/architecture/canonical-runtime-architecture.md`
- `docs/project-status/current-state.md`
- `docs/project-status/next-steps.md`
- `docs/project-status/completed.md`
- `docs/ops/n8n-runtime-start.md`
- `docs/ops/database-recovery.md`
- `docs/ops/n8n-workflow-telegram-customer-ingress.md`

---

## Reviewer section (alpstein-reviewer)

### A) Confirmed findings

- **Runtime-vs-repo divergence is real and high impact.** The audit correctly identifies that operationally referenced backend/n8n artifacts are not fully represented in tracked git state.
- **Migration reproducibility is currently unsafe.** The cited absence of tracked Alembic chain/config in the current tracked baseline is a hard blocker for clean-clone DB replay/rollback confidence.
- **n8n governance risk is correctly prioritized.** Runtime workflow state and export discipline are insufficiently controlled for deterministic rollback.
- **Host-coupled networking assumptions are a true portability risk.** Docker gateway/UFW coupling and environment-local assumptions reduce portability across hosts.
- **Task/docs lifecycle drift is valid.** The mismatch between tracked `in-progress` and untracked/detached `done` artifacts is a reproducibility governance issue, not just docs hygiene.

### B) Missing or weak findings

1. **Provenance confidence gap (methodological).**  
   The audit relies heavily on one git working state snapshot (`status`, `ls-files`) but does not explicitly state whether this repository is intentionally sparse/minimal, partially imported, or expected to be complete. This uncertainty should be called out as a finding because it affects severity interpretation.

2. **Rollback definition is underspecified.**  
   “Rollback” is mentioned as a risk, but no minimum rollback contract is defined (e.g., restore app code + DB schema revision + n8n workflow version + env template version as one atomic set). Without this definition, go/no-go decisions can drift.

3. **Secrets governance risk is incomplete.**  
   The audit flags env reproducibility, but it should explicitly separate:
   - reproducibility templates (`.env.example`, non-secret defaults), vs
   - secret distribution/rotation ownership (out-of-git).
   Without this split, teams may over-correct by pushing sensitive runtime values into repo workflows.

4. **n8n export determinism is not fully qualified.**  
   It flags untracked exports, but does not require deterministic canonical naming/versioning policy (which file is canonical, how runtime ID maps to export file, how to deprecate ad-hoc exports).

5. **Clean-clone acceptance criteria are implied, not explicit.**  
   The audit proposes a gate but does not define concrete pass/fail checks (commands, expected outputs, and artifact checksums/version references).

6. **Migration safety should include downgrade posture.**  
   Replay is covered; downgrade safety/irreversibility checks are not explicitly listed. This is important for operational rollback confidence.

### C) Critical risks (must resolve before implementation phase)

- **CR-1: Non-reproducible backend baseline** — fresh clone cannot be trusted to represent runtime behavior.
- **CR-2: Non-reproducible DB schema state** — migration chain/config not consistently tracked in baseline.
- **CR-3: Non-governed n8n runtime state** — operationally relevant workflows are not guaranteed to be restorable from reviewed repo artifacts.
- **CR-4: Ambiguous rollback unit** — no agreed atomic rollback bundle across backend + DB + workflow + env template versions.
- **CR-5: Secrets/process ambiguity** — risk of either leaking secrets into reproducibility artifacts or failing to document secret injection path sufficiently for redeploy.

### D) Recommended correction to cleanup order

Current sequencing is close, but should be adjusted to reduce false confidence:

1. **Define reproducibility and rollback contracts first (policy gate).**  
   Establish exact “reproducible deployment unit” and “rollback unit” before importing artifacts.  
2. **Inventory freeze with provenance annotation.**  
   Snapshot runtime artifacts and label source-of-truth ownership per artifact (repo/runtime/UI/host).  
3. **Baseline import to git (backend + alembic + n8n + specs + minimal env templates).**  
4. **Workflow governance normalization.**  
   Canonicalize n8n export naming/version mapping and retire ad-hoc exports before clone tests.  
5. **Clean-clone reproducibility gate (hard pass/fail).**  
   Validate from empty clone using docs-only steps.  
6. **Task/docs reconciliation and topology cleanup.**  
   Align historical vs canonical docs once runtime reproducibility is proven.  
7. **Rollback rehearsal last, on the stabilized baseline.**  
   Rehearse rollback only after artifact governance and clone reproducibility pass; otherwise rehearsal evidence is non-portable.

### E) Go / No-Go criteria before implementation phase

#### Go only if all criteria are met

- **G1:** Backend runtime code needed for webhook→AI path is fully tracked in repo baseline.
- **G2:** Alembic chain + config required for runtime schema state is tracked and replayable from clean clone.
- **G3:** Canonical n8n workflow exports for active operational paths are tracked, versioned, and mapped to runtime usage.
- **G4:** `.env.example`-style templates exist for required runtime variables (no secrets), with clear secret injection process documented outside code.
- **G5:** Fresh-clone procedure succeeds end-to-end with documented commands and expected checks.
- **G6:** Rollback contract is defined and validated against tracked artifacts only.
- **G7:** Task/docs state does not contradict canonical runtime mapping for deployment-critical paths.

#### No-Go triggers

- Missing tracked migration baseline for current runtime schema.
- Active operational n8n workflows not represented by canonical tracked exports.
- Reproducibility relying on undocumented host-local assumptions or operator memory.
- Any requirement to copy real secrets into repository artifacts to make deployment “work.”


