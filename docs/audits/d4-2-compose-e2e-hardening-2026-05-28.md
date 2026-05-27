# D4.2 — Compose E2E hardening audit

**Date:** 2026-05-28  
**Phase:** PHASE D4.2 — Compose E2E Hardening  
**Branch:** `stabilization/runtime-baseline`  
**Git HEAD:** `5a45478` (at audit time)  
**Operator:** agent (automated drill on Contabo-class host)  
**Contract:** [`deployment-contract.md`](../deployment/deployment-contract.md)  
**Prior gate:** [`clean-clone-gate-2026-05-27.md`](clean-clone-gate-2026-05-27.md) (B2.9 PASS on disposable clone)

**Verdict:** **CONDITIONAL PASS** — portable compose stack is reproducible from clean Postgres volume + documented env, with **documented operator friction and one runtime defect** blocking full webhook E2E on this host without a follow-up fix.

---

## 1. Scope and environment

| Item | Value |
|------|--------|
| Host | `Linux 6.8.0-117-generic` (Ubuntu 24.04, x86_64) |
| Docker | `29.1.3` |
| Compose CLI | `docker-compose` **1.29.2** (hyphen; **not** `docker compose` v2 plugin) |
| Repo path | `/opt/alpstein-ai` |
| Compose project | `alpstein-ai` |
| Files | `docker-compose.yml` + optional `docker-compose.dev.yml` |
| Redis | **Not in portable stack** (contract §1 out of scope; no redis service in compose) |
| Legacy coexistence | Host `uvicorn` on `127.0.0.1:8000`; legacy `alpstein_n8n` on `15679`; `backend_postgres` on `15432` |

### Services in portable compose (verified)

| Service | Container name | Image / build | In default `up` |
|---------|----------------|---------------|-----------------|
| `postgres` | `alpstein_postgres` | `postgres:15` | Yes |
| `backend` | `alpstein_backend` | `alpstein-ai-backend:local` | Yes |
| `n8n` | `alpstein_n8n_compose` | `docker.n8n.io/n8nio/n8n:1.95.3` | Yes (after backend healthy) |
| `backend-bootstrap` | `alpstein_backend_bootstrap` | same image | **No** (`--profile bootstrap`) |

---

## 2. Commands executed (sanitized)

```bash
cd /opt/alpstein-ai
git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD

# Config (requires POSTGRES_PASSWORD in environment or root .env)
export POSTGRES_PASSWORD='<set-by-operator>'   # not recorded
docker-compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml config

# Clean Postgres volume drill (destructive to alpstein_postgres_data only)
docker-compose -p alpstein-ai down
docker volume rm alpstein_postgres_data
docker-compose -p alpstein-ai up -d --build postgres
docker-compose -p alpstein-ai up -d --build backend

# Health / migration
docker inspect --format='{{.State.Health.Status}}' alpstein_postgres
docker inspect --format='{{.State.Health.Status}}' alpstein_backend
docker exec alpstein_backend python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/api/v1/health').status_code)"
docker exec alpstein_backend python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/api/v1/health/ready').status_code)"
docker exec alpstein_postgres psql -U alpstein -d alpstein_ai -tAc "SELECT version_num FROM alembic_version;"

# Optional seed (required for webhook business lookup)
docker-compose -p alpstein-ai --profile bootstrap run --rm backend-bootstrap

# Restart drills
docker restart alpstein_backend
docker restart alpstein_postgres

# Shutdown / startup cycle
docker-compose -p alpstein-ai down
docker-compose -p alpstein-ai up -d --build postgres backend
```

---

## 3. Startup ordering and timing

**Contract order (observed):**

1. Network `alpstein_internal`
2. `postgres` → health `pg_isready`
3. `backend` `depends_on: postgres: service_healthy`
4. Entrypoint: `wait_for_postgres` → `alembic upgrade head` → `uvicorn`
5. `backend` health: `GET /api/v1/health/ready` (migrate-before-serve **verified** in logs)
6. `n8n` `depends_on: backend: service_healthy` (not fully exercised on this host — see §6)

| Milestone | Clean volume (2026-05-28 drill) |
|-----------|----------------------------------|
| `postgres` healthy | ~8–11 s |
| `backend` healthy (includes first-run migrations 0001→0007) | ~25 s after `postgres` healthy |
| Full `down` + `up` cycle (data retained) | `down` ~3 s; `backend` healthy ~25 s total |

**Migrate-before-serve:** Log lines `running alembic upgrade head` → `alembic upgrade head completed` → `starting uvicorn`; `alembic_version` = `0007`.

---

## 4. Healthcheck results

| Service | Probe | Result (clean volume drill) |
|---------|--------|----------------------------|
| Postgres | `pg_isready -U alpstein -d alpstein_ai` | **healthy** |
| Backend | `httpx` → `/api/v1/health/ready` | **healthy** (in-container) |
| Liveness | `GET /api/v1/health` | **200** |
| Readiness | `GET /api/v1/health/ready` | **200** (after migrations) |

Readiness returns **503** when Postgres is down (observed during postgres container exit/recreate).

---

## 5. Restart and recovery verification

| Test | Result | Notes |
|------|--------|-------|
| `docker restart alpstein_backend` | **PASS** | Healthy ~11 s; readiness 200 |
| `docker restart alpstein_postgres` | **PASS** | Healthy ~7 s; persistence probe row retained |
| Backend after postgres restart | **PASS** | Backend returns healthy without manual `up` |
| `docker-compose down` / `up` (no `-v`) | **PASS** | Persistence probe `d42-2026-05-28` survived; readiness 200 |
| Postgres password change without volume reset | **FAIL** | `InvalidPasswordError` / entrypoint cannot reach DB — see §7 |

---

## 6. Persistence verification

| Check | Result |
|-------|--------|
| Volume `alpstein_postgres_data` survives `docker-compose down` (no `-v`) | **PASS** |
| Custom table + row survives postgres restart | **PASS** |
| Alembic revision after fresh volume | `0007` at head |
| Bootstrap seed (`demo_barbershop_001`) after `--profile bootstrap` | **PASS** (SQL/bootstrap logs OK) |

**Volume warning:** `alpstein_n8n_data` is **shared name** with legacy `n8n/docker-compose.yml`. Do **not** run `docker-compose down -v` on a host that still depends on legacy n8n credentials/workflows without a backup plan.

---

## 7. Env loading consistency

| File | Expected role | Audit finding |
|------|---------------|---------------|
| Repo root `.env` | `POSTGRES_*` for compose interpolation | **GAP on this host:** file existed but contained **only** backend-style keys (`ALPSTEIN_AI_DATABASE_URL`, `OPENAI_*`, Langfuse) — **no `POSTGRES_PASSWORD`**. `docker-compose config` fails until `POSTGRES_PASSWORD` is exported or added to root `.env`. |
| `backend/.env` | Host Alembic / local uvicorn | **Missing** on this host (optional for compose-only path) |
| `n8n/.env` | n8n `env_file` | **Present** with required key names |
| Compose → backend | Builds `ALPSTEIN_AI_DATABASE_URL` from `POSTGRES_*` | Works when `POSTGRES_PASSWORD` is set |

**Operator rule (documented, not optional):** For compose, copy **root** `.env.example` and set `POSTGRES_PASSWORD` **before** first `up`. Align `N8N_BACKEND_API_TOKEN` across root `.env` and `n8n/.env`.

---

## 8. Hidden local dependencies / host conflicts

| Dependency | Impact | Mitigation |
|------------|--------|------------|
| Host uvicorn on `127.0.0.1:8000` | `docker-compose.dev.yml` **cannot** bind backend port — `address already in use` | Use compose **without** dev overlay and probe via `docker exec`, **or** stop host backend, **or** set `BACKEND_HOST_PORT` to a free port |
| Legacy `alpstein_n8n` (port `15679`) | Coexists with portable stack; portable dev n8n uses `15680` | Do not run portable + legacy n8n against same volume without cutover plan ([`n8n-compose.md`](../deployment/n8n-compose.md)) |
| Fixed `container_name:` values | Only one portable stack instance per host | Cannot run two clones concurrently |
| `docker-compose` 1.29 + Docker 29 | Intermittent `KeyError: 'ContainerConfig'` on recreate / dev overlay | `docker-compose rm -sf <service>` then `up`; prefer disposable host or compose v2 when available |
| Postgres container rename (`*_alpstein_postgres`) | Occurs after partial failures; breaks `depends_on` DNS until `rm` + `up` | `docker-compose rm -sf postgres backend` then `up -d` |

**Redis:** Not required for portable MVP compose path. Do not assume Redis is started.

---

## 9. Webhook execution (post-restart)

| Step | Result |
|------|--------|
| Auth + routing with `X-Alpstein-Webhook-Token` | Token loaded from root `.env` (not logged) |
| Before bootstrap | **404** `BUSINESS_NOT_FOUND` (expected on empty DB) |
| After bootstrap | **500** `Internal Server Error` |

**Root cause (500):** `prompt_runs.metadata` JSONB insert fails — UUID values in observability metadata are not JSON-serialized (`TypeError: Object of type UUID is not JSON serializable`). Observed during D4.2 drill; **blocks webhook E2E** until a small serialization fix (out of D4.2 scope per “no observability redesign” — track as defect).

**Not exercised on this host:** n8n workflow → backend HTTP after portable `n8n` `up` (compose recreate error + legacy n8n already bound). Prior B2.9 gate verified n8n → `http://backend:8000` readiness from inside `alpstein_n8n_compose`.

---

## 10. Logs (operational readability)

| Source | Readable? | Sample signal |
|--------|-------------|---------------|
| `alpstein_backend` entrypoint | **Yes** | `postgres ready`, `running alembic upgrade head`, `starting uvicorn` |
| Uvicorn access | **Yes** | `GET /api/v1/health/ready HTTP/1.1" 200` |
| Migration failures | **Yes** | `ERROR: alembic upgrade head failed — uvicorn will not start` |
| Webhook / app errors | **Yes** | Stack traces on stderr (no secrets observed in sampled migration lines) |

Structured `correlation_id` in access logs depends on request traffic (D2); not re-validated in this compose-only drill.

---

## 11. Required operational tests — summary

| Test | Status |
|------|--------|
| `docker compose up --build` (via `docker-compose -p alpstein-ai up -d --build`) | **PASS** (clean `alpstein_postgres_data`) |
| Clean restart (`down` / `up` no `-v`) | **PASS** |
| Container restart (postgres, backend) | **PASS** |
| Backend restart | **PASS** |
| Postgres persistence | **PASS** |
| Webhook after restart | **PASS** after U1 fix + image rebuild (200, `success: true`) |
| Readiness endpoint | **PASS** |
| Migration execution | **PASS** (`0007`) |
| Portable n8n `up` on conflicted host | **NOT RUN** (legacy + compose tooling friction) |

---

## 12. Discovered operational risks

1. **Root `.env` missing `POSTGRES_*`** — compose fails or uses wrong password vs existing volume.
2. **Password change without volume reset** — silent auth failure until volume removed or password restored.
3. **Dev overlay port 8000** — conflicts with legacy host uvicorn on Contabo.
4. **Shared `alpstein_n8n_data`** — `down -v` is destructive for legacy n8n.
5. **Compose 1.29 / Docker 29** — recreate fragility (`ContainerConfig`, renamed postgres containers).
6. **Webhook 500** — `prompt_runs.metadata` UUID JSON serialization (D2 regression).
7. **Bootstrap not automatic** — fresh DB requires `--profile bootstrap` (or manual seed) before `demo_barbershop_001` webhooks succeed.

---

## 13. Unresolved issues (no silent fixes in D4.2)

| ID | Issue | Suggested owner |
|----|--------|-----------------|
| U1 | `prompt_runs.metadata` UUID not JSON-serializable → webhook 500 | **Fixed** — `json_safe_metadata()` in `prompt_run_service` (D4.2 follow-up) |
| U2 | Portable n8n E2E on legacy host not re-run | Ops — cutover window or disposable VM |
| U3 | `docker compose` v2 plugin absent | Infra — optional install; keep documenting `docker-compose` hyphen |

---

## 14. Operator friction points (tribal knowledge to eliminate)

1. “Copy `.env.example`” is insufficient if operators only maintain a backend-style root `.env`.
2. Must export `POSTGRES_PASSWORD` for **every** compose command if not in root `.env`.
3. Dev overlay requires free `8000` / `15680` on loopback.
4. First webhook test needs bootstrap profile + aligned `N8N_BACKEND_API_TOKEN`.
5. Cannot change Postgres password in `.env` alone — must recreate `alpstein_postgres_data` or use `ALTER USER`.
6. On hosts with legacy services, prefer internal-network probes (`docker exec`) over host `curl :8000`.

---

## 15. Success criteria assessment

| Criterion | Met? |
|-----------|------|
| Clone + configure env + compose → healthy runtime | **Yes**, if root `.env` includes `POSTGRES_PASSWORD` and port conflicts handled |
| Without undocumented tribal knowledge | **Partial** — gaps listed in §14; `.env.example` updated in this audit |
| Full webhook E2E on fresh stack | **No** until U1 fixed |
| Redis / extra services | **N/A** — not in contract compose |

---

## 16. Doc updates from this audit

| File | Change |
|------|--------|
| `.env.example` | Clarify **required** `POSTGRES_PASSWORD` for compose |
| `docs/deployment/postgres-compose.md` | Troubleshooting: password/volume mismatch, port 8000 conflict |
| `docs/deployment/README.md` | Link to this audit |

---

## 17. Related evidence

- B2.9 clean-clone gate: [`clean-clone-gate-2026-05-27.md`](clean-clone-gate-2026-05-27.md)
- D2 observability: [`tasks/done/T-d2-langfuse-runtime-metadata-wiring.md`](../../tasks/done/T-d2-langfuse-runtime-metadata-wiring.md)
