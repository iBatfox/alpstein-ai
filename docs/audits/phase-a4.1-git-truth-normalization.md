# Phase A4.1 — Git Truth Normalization Notes

**Status:** implementation notes (no commit yet)  
**Date:** 2026-05-27  
**Inputs:** `runtime-reproducibility-audit.md`, `runtime-baseline-remediation-plan.md`

## Objective

Normalize repository truth toward a canonical reproducible baseline without changing runtime behavior.

## Normalization actions executed in this slice

1. Updated `.gitignore` to protect secrets/local state and keep templates trackable.
2. Added explicit ignore policy for ad-hoc non-canonical workflow export (`n8n/workflows/My_workflow.json`).
3. Removed temp runtime garbage files under `tmp/`.
4. Created tracked task artifact for this implementation slice (`tasks/in-progress/t1.5-git-truth-normalization.md`).

## Classification notes

### Intended for tracking (canonical/reproducibility-critical)

- `backend/app/**` runtime backend code.
- `backend/alembic/**` and `backend/alembic.ini` migration reproducibility baseline.
- `backend/requirements.txt` dependency baseline.
- `backend/tests/**` reproducibility regression suite.
- `n8n/workflows/t13_workflow1_test_webhook_skeleton.json`.
- `n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json`.
- `n8n/docker-compose.yml` and `n8n/.env*.example` templates (no secrets).
- `specs/**` source-of-truth contracts.
- Deployment-critical docs under `docs/architecture/`, `docs/ops/`, `docs/project-status/`, `docs/audits/`.

### Intended for ignore (local-only / non-canonical)

- `.env`, `n8n/.env*` secret-bearing local env files (except explicit examples).
- `.venv/`, `venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.mypy_cache/`.
- `.codex/`, `.claude/` local agent state.
- `tmp/` temporary artifacts.
- `n8n/workflows/My_workflow.json` ad-hoc non-canonical export.

### Requires manual review before any add/commit

- `.cursor/**` changes outside `.cursor/skills/**` (tool-local vs project knowledge).
- `tasks/` lifecycle consistency (`todo`/`in-progress`/`done` duplicates and moved files).
- `schema_dbdesigner.sql` root-level source-of-truth decision vs generated snapshot.
- Any docs asserting old runtime behavior (must match current canonical runtime map).

### Runtime-critical (must not be excluded by ignore rules)

- `backend/alembic/versions/*.py` full revision chain.
- `backend/app/main.py`, webhook route/service path, prompt/orchestration services.
- Canonical workflow exports for active T13/T14 operational paths.
- `specs/**` and canonical architecture/runtime docs.

### Unsafe / no-go

- Any `.env` with real credentials.
- `n8n` workflow exports containing token literals.
- Local caches/editor metadata.
- Unreviewed broad sweeps that mix backend baseline import with workflow governance changes.

## PRE-COMMIT REVIEW (mandatory before git add/commit)

### Files intended for tracking (this slice)

- `.gitignore`
- `docs/audits/phase-a4.1-git-truth-normalization.md`
- `tasks/in-progress/t1.5-git-truth-normalization.md`

### Files intended for ignore (validated by policy)

- `.env`, `n8n/.env*` (except `*.example`)
- local tool/cache artifacts
- `tmp/**`
- `n8n/workflows/My_workflow.json`

### Files requiring manual review

- `.cursor/**` except `.cursor/skills/**`
- all `tasks/**` state reconciliation moves
- untracked backend/n8n/specs baseline import scope (must be split into safe commits)

### Files considered runtime-critical

- `backend/app/**`, `backend/alembic/**`, `backend/requirements.txt`
- canonical `n8n/workflows/t13*`, `n8n/workflows/t14*`
- `specs/**`, canonical runtime docs

### Files considered unsafe/no-go

- secret-bearing env files
- ad-hoc workflow exports with sensitive fields
- temporary and cache directories

## Commit grouping proposal (do not execute yet)

1. **A4.1-C1 (policy-only):** `.gitignore` + this A4.1 note + task file.
2. **A4.1-C2 (backend reproducibility baseline):** tracked `backend/app/**`, `backend/alembic/**`, `backend/requirements.txt`, backend tests.
3. **A4.1-C3 (workflow baseline):** canonical n8n exports/templates only.
4. **A4.1-C4 (contracts/docs reconciliation):** `specs/**` + deployment-critical docs/task-state reconciliation.

No giant commit. No mixed cross-layer commit boundaries.
