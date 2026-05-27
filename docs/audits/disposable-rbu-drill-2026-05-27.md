# Disposable RBU drill report (Phase C)

**Date:** 2026-05-27  
**Type:** Operational rollback rehearsal (disposable only)  
**Operator:** agent  
**Environment:** `/tmp/alpstein-rbu-drill/repo` (clone from `/opt/alpstein-ai`)  
**Compose project:** `alpstein-rbu-drill` (disposable; shared container names `alpstein_*`)  
**Production (Contabo):** **not touched**

**Rollback target tested:** `baseline-b2.9-clean-clone-gate` (`f7cca06`)  
**Restore target:** `stabilization/runtime-baseline` @ `02a4ee8` (`baseline-c2-export-scrub-gate` tag)

---

## 1. Git state at drill start (working copy)

| Item | Value |
|------|--------|
| Branch | `stabilization/runtime-baseline` |
| HEAD | `02a4ee8` — `ops(gitignore): add runtime volume and backup exclusions` |
| Working tree | **dirty** — uncommitted C1/C2 docs, `scripts/n8n/export-scrub.sh`, `n8n/workflows/README.md`, `runtime-registry.md` |
| `baseline-b2.9-clean-clone-gate` | `f7cca06` |
| `baseline-c2-export-scrub-gate` | `02a4ee8` (same as HEAD — **no export-scrub commit**) |

**Diff `baseline-b2.9..HEAD`:** `.gitignore` only (+8 lines). No compose/Dockerfile/backend changes.

---

## 2. Pass/fail matrix

| Step | Check | Result | Notes |
|------|--------|--------|-------|
| 1 | Record HEAD/tags | **PASS** | See §1 |
| 2 | Clean git in **clone** | **PASS** | 0 dirty lines in drill clone |
| 2b | Clean git in **worktree** | **FAIL** | Uncommitted C1/C2 artifacts — see §4 |
| 3 | Start current stack | **PASS** | `postgres` + `backend` + `n8n` |
| 4 | Backend readiness | **PASS** | `/health` 200, `/ready` 200 |
| 5 | Migrations | **PASS** | Fresh volume: `0001→0007`; `alembic_version=0007` |
| 6 | Export scrub gate | **N/A / FAIL** | `scripts/n8n/export-scrub.sh` **not in git** at HEAD or b2.9 |
| 7 | Rollback to `baseline-b2.9` | **PASS** | `git checkout` in disposable clone |
| 8 | Rebuild/restart rollback stack | **PASS** | Image cache hit; healthy ~25s |
| 9 | Backend after rollback | **PASS** | 200/200; uvicorn only (no re-migrate log) |
| 10 | DB compatibility | **PASS** | Volume retained; `alembic_version=0007`; no downgrade needed |
| 11 | n8n → `backend:8000` | **PASS** | `wget` `/api/v1/health/ready` 200 |
| 12 | Runtime registry assumptions | **GAP** | `runtime-registry.md` / `workflows/README.md` **absent** at b2.9 tag |
| 13 | Webhook smoke | **PASS** | Direct `POST /api/v1/webhook/message` with container token (not n8n path) |
| 14 | Restore HEAD | **PASS** | Branch checkout; compose down |
| 15 | Document findings | **PASS** | This file |

---

## 3. Recovery timing (disposable stack)

| Phase | Elapsed | Notes |
|-------|---------|-------|
| Fresh stack (HEAD, new volume) | **~45 s** | Includes build cache, bootstrap profile, webhook |
| Rollback restart (b2.9, **existing** volume) | **~35 s** | No Alembic re-run; faster path |
| `docker-compose down` | **~5 s** | Volumes retained (except partial `down -v` on postgres only at start) |

**Operator estimate (documented procedure, clean clone):** 10–15 min including env setup, bootstrap, and manual n8n import — not exercised end-to-end in this drill.

---

## 4. Hidden dependency findings

| ID | Finding | Severity |
|----|---------|----------|
| H1 | **`export-scrub.sh` exists only in uncommitted worktree** — tag `baseline-c2-export-scrub-gate` does not point to scrub implementation | **High** |
| H2 | **C1 governance files** (`n8n-runtime-export-parity.md`, `workflows/README.md`, `runtime-registry.md`) not in git at b2.9/HEAD | **High** |
| H3 | Container names fixed (`alpstein_postgres`, `alpstein_backend`) — compose `-p` project does not isolate names; parallel drills collide | **Medium** |
| H4 | `alpstein_n8n_data` volume sometimes **in use** by another stack — `down -v` cannot remove | **Medium** |
| H5 | Webhook smoke requires **seeded** `demo_barbershop_001` (bootstrap profile) + aligned `N8N_BACKEND_API_TOKEN` in backend container | **Low** (documented) |
| H6 | n8n **workflow import/activate** not part of portable rollback — webhook via n8n not tested | **Low** (B2.9 known) |
| H7 | Rollback b2.9↔HEAD is **trivial** (gitignore only) — does not validate rollback to `b2.6` / `b2.5` with compose topology changes | **Medium** |

---

## 5. Manual-step findings

| Step | Documented? | Observed |
|------|-------------|----------|
| Create root `.env` + `n8n/.env` | Yes | Required before `up` |
| `docker-compose -p alpstein-ai up -d postgres backend` | Yes | Works |
| Bootstrap profile (demo data) | Yes | Required for webhook business_id |
| `scripts/n8n/export-scrub.sh` before commit | Documented in C2 | **Cannot run from git** — script missing |
| n8n credential re-bind after import | Yes | Skipped (no import in drill) |
| Telegram activate + n8n restart | Ops docs | Skipped |
| Update `runtime-registry.md` on activate | C1 policy | File not in git at rollback tag |

---

## 6. Rollback gaps

| Gap | Detail |
|-----|--------|
| **Tag/content mismatch** | `baseline-c2-export-scrub-gate` = gitignore commit; G-EXP-2 tooling not tagged |
| **Shallow rollback test** | b2.9→HEAD does not exercise Dockerfile/compose/entrypoint rollback |
| **No Alembic downgrade drill** | Forward-only; rollback to older schema revision not tested |
| **n8n volume + encryption key** | Changing `N8N_ENCRYPTION_KEY` on rollback not tested |
| **Registry RBU** | Runtime workflow IDs on Contabo not validated (by design) |
| **Production host** | Host uvicorn `:8010` / legacy `alpstein_n8n` path not in drill scope |

**What worked:** Git checkout `f7cca06` + `docker-compose up` on **same** postgres volume → backend healthy, DB at `0007`, n8n reaches backend, webhook 200.

---

## 7. Runtime drift findings

| Area | Drift |
|------|--------|
| Git vs ops claims | `current-state.md` references export-scrub script; **not committed** |
| C1 registry | Documents Contabo workflow IDs; **not in git** at tested tags |
| Local `My_workflow.json` | Gitignored; present on dev host; export-scrub warns |
| HEAD vs b2.9 runtime | **No drift** for portable compose (identical stack) |
| Live Contabo | Unknown — drill explicitly excluded |

---

## 8. Webhook smoke detail

**Method:** `POST http://127.0.0.1:8000/api/v1/webhook/message` from **inside** `alpstein_backend` using `N8N_BACKEND_API_TOKEN` from container env (after bootstrap).

| When | HTTP | Result |
|------|------|--------|
| HEAD stack | 200 | `success: true`, `reply_to_customer` present |
| After b2.9 rollback | 200 | Same |

**Not tested:** n8n test webhook path, Gate 1 duplicate, owner notify, Telegram ingress.

**Initial false negative:** 401 when token passed from host grep instead of container env — operator must use container-aligned token.

---

## 9. Recommended stabilization tasks

| Priority | Task | Owner |
|----------|------|--------|
| P0 | **Commit** `scripts/n8n/export-scrub.sh` + C2 task/docs | Operator |
| P0 | **Commit** C1 `n8n-runtime-export-parity.md`, `workflows/README.md`, `runtime-registry.md` | Operator |
| P0 | **Retag** `baseline-c2-export-scrub-gate` after real C2 commit (or new tag) | Operator |
| P1 | Clean worktree before Phase D / merge | Operator |
| P1 | Optional: compose project-specific `container_name` or drill doc warning (H3) | Backlog |
| P2 | Drill rollback to `baseline-b2.6-compose` with **fresh volume** | Next RBU drill |
| P2 | Document Alembic downgrade policy for non-adjacent tag rollback | migration-engineer |

---

## 10. Phase D readiness — GO / NO-GO

| Criterion | Status |
|-----------|--------|
| Portable compose rollback (adjacent tag b2.9) | **GO** |
| Export scrub gate reproducible from git | **NO-GO** until script committed |
| C1 parity docs in git | **NO-GO** until committed |
| Production cutover | **NO-GO** — out of scope |
| Operator RBU checklist matches disposable reality | **CONDITIONAL GO** |

### Verdict: **CONDITIONAL NO-GO** for Phase D production-adjacent work

**Proceed with Phase D planning** only after P0 stabilization commits and tag realignment.

**Allowed now:** Further disposable drills, C5 Telegram regression on canonical exports (with import), C6 clean-clone G5 extension — all on disposable stack.

---

## 11. Rollback / cleanup (drill environment)

```bash
docker-compose -p alpstein-rbu-drill down
# Optional full wipe:
docker-compose -p alpstein-rbu-drill down -v
rm -rf /tmp/alpstein-rbu-drill
```

Working copy at `/opt/alpstein-ai` was **not** checked out to b2.9 (drill used clone only).

---

## 12. Commands reference (sanitized)

```bash
git clone /opt/alpstein-ai /tmp/alpstein-rbu-drill/repo
cd /tmp/alpstein-rbu-drill/repo
# create .env + n8n/.env from examples

docker-compose -p alpstein-rbu-drill down -v   # partial; n8n volume may stick
docker-compose -p alpstein-rbu-drill up -d postgres backend n8n
docker inspect --format='{{.State.Health.Status}}' alpstein_backend

git checkout baseline-b2.9-clean-clone-gate
docker-compose -p alpstein-rbu-drill up -d postgres backend n8n

git checkout stabilization/runtime-baseline
docker-compose -p alpstein-rbu-drill down
```

Full log: `/tmp/alpstein-rbu-drill/drill.log` (on gate host; not committed).

---

## Related

- [`clean-clone-gate-2026-05-27.md`](clean-clone-gate-2026-05-27.md)
- [`n8n-runtime-export-parity.md`](../ops/n8n-runtime-export-parity.md)
- [`deployment-contract.md`](../deployment/deployment-contract.md) §11 RBU
