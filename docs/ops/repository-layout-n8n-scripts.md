**Doc status:** canonical (repository layout)  
**Tier:** ops / governance  
**As-of:** 2026-05-27  
**Task:** E0 — Repository normalization: n8n script layout  
**Debt item:** **TD-D4-n8n-script-layout** — **closed** (documented; no file moves)

# Repository layout — n8n scripts vs verification harnesses

## Decision (summary)

**Keep the current paths.** No file moves in E0.

| Path | Ownership | Use when |
|------|-----------|----------|
| **`n8n/`** | n8n **runtime / deployment unit** | Compose, env examples, workflow exports, runtime-only operator scripts |
| **`n8n/workflows/`** | Canonical **workflow export** source of truth | Committed JSON; G-EXP-2 targets this tree |
| **`n8n/scripts/`** | Scripts that **require a live n8n container** | `docker exec`, credential import/export, Telegram credential verification |
| **`scripts/n8n/`** | Repo-level **n8n artifact governance** (no runtime) | Static checks/scrub of `n8n/workflows/*.json` before commit |
| **`scripts/verify/`** | **Cross-cutting** verification harnesses | Backend app, observability, multi-service drills (not n8n-subsystem-only) |
| **`backend/scripts/`** | Backend-owned ops | Seeds, SQL maintenance — out of scope for this note |

**Rule of thumb:** If it only makes sense after `docker exec … n8n`, it belongs under **`n8n/scripts/`**. If it validates git-tracked workflow JSON without contacting n8n, it belongs under **`scripts/n8n/`**. If it primarily exercises the **backend** (or backend + mocked DB), it belongs under **`scripts/verify/`**.

---

## Inventory (as-of E0 review)

### `n8n/` — runtime subsystem

| Path | Type | Runtime required? | Owner |
|------|------|-------------------|--------|
| `n8n/docker-compose.yml` | Legacy host compose | Yes (deploy) | n8n unit |
| `n8n/.env.example`, `n8n/.env.telegram.customer.example` | Env templates | No | n8n unit |
| `n8n/workflows/*.json` | Export SoT | No (files) | n8n unit |
| `n8n/workflows/README.md`, `runtime-registry.md` | Governance docs | No | n8n unit |
| `n8n/scripts/t14-import-customer-telegram-credential.sh` | Operator script | **Yes** (`alpstein_n8n`) | n8n unit |
| `n8n/scripts/t14-verify-telegram-bots.sh` | Operator script | **Yes** | n8n unit |

### `scripts/n8n/` — artifact governance (repo-level, n8n-scoped)

| Path | Type | Runtime required? | Owner |
|------|------|-------------------|--------|
| `scripts/n8n/export-scrub.sh` | G-EXP-2 gate (C2 / T14.6) | **No** — reads `n8n/workflows/` only | Repo governance (n8n domain) |

**Why not `n8n/scripts/`?** `export-scrub.sh` does not import/export via n8n CLI; it is a **pre-commit parity gate** on static JSON. Placing it under `scripts/n8n/` keeps `n8n/scripts/` reserved for **live runtime** operations and matches existing docs/tasks (T14.6, export parity runbook).

**Why not `scripts/verify/`?** `scripts/verify/` is reserved for **cross-cutting** harnesses (e.g. backend + observability). Workflow export scrub is **n8n-artifact-specific**; a future `scripts/verify/n8n/` subfolder is optional only if many cross-repo gates accumulate.

### `scripts/verify/` — cross-cutting verification

| Path | Type | Runtime required? | Owner |
|------|------|-------------------|--------|
| `scripts/verify/d3_runtime_trace_verification.py` | D3 trace harness | Optional (in-process backend; may mock DB) | Repo verification |

---

## FAQ

### Should `export-scrub.sh` move to `n8n/scripts/`?

**No (E0).** It does not run `n8n import:workflow` or `export:workflow`; it only validates/normalizes files under `n8n/workflows/`. Current path `scripts/n8n/export-scrub.sh` is intentional.

### Should `export-scrub.sh` move to `scripts/verify/`?

**No (E0).** That directory is for harnesses that are not owned by a single subsystem. Export scrub is n8n-workflow governance, not a full-stack E2E verifier.

### Should `d3_runtime_trace_verification.py` move under `n8n/`?

**No.** It imports `backend/app` and tests observability/webhook behavior — **backend-centric** verification.

---

## References (canonical)

| Doc | Section |
|-----|---------|
| [`n8n-runtime-export-parity.md`](n8n-runtime-export-parity.md) | G-EXP-2, `scripts/n8n/export-scrub.sh` |
| [`n8n/workflows/README.md`](../../n8n/workflows/README.md) | Export gate commands |
| [`n8n-env-credential-checklist.md`](n8n-env-credential-checklist.md) | `n8n/scripts/t14-*.sh` |
| [`deployment-contract.md`](../deployment/deployment-contract.md) | Portable vs legacy n8n layout |

---

## Follow-up (optional, not required for E0)

| ID | Item | Severity |
|----|------|----------|
| E0-F1 | Add `n8n/README.md` index pointing here + `workflows/README.md` | Minor |
| E0-F2 | If `scripts/verify/` grows, subdirs `scripts/verify/backend/`, `scripts/verify/n8n/` | Minor — only when >3 harnesses |

**No behavior change. No commit until operator review.**
