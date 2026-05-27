# Clean-clone verification gate (B2.9)

**Date:** 2026-05-27  
**Operator:** agent (automated gate run)  
**Branch:** `stabilization/runtime-baseline`  
**Tag verified:** `baseline-b2.8-bootstrap` (`58ae7b4`)  
**Clone path:** `/tmp/alpstein-b29-clean-clone` (local clone from `/opt/alpstein-ai`)  
**Compose project:** `alpstein-ai`  
**Contract:** [`deployment-contract.md`](../deployment/deployment-contract.md) §13

**Verdict:** **PASS** — portable stack reproducible from clone + documented env. Live Contabo host runtime **not** exercised.

---

## Pass/fail summary

| Gate | Check | Result | Notes |
|------|--------|--------|-------|
| **G1** | Git clone, branch, tag, clean tree | **PASS** | HEAD = `baseline-b2.8-bootstrap` |
| **G2** | `docker-compose config` | **PASS** | With root `.env` |
| **G3** | Postgres up + healthy | **PASS** | `alpstein_postgres` |
| **G4** | Backend migrate + healthy + health URLs | **PASS** | Alembic 0001→0007; `/health` + `/ready` = 200 |
| **G5** | Bootstrap profile + prod refusal | **PASS** | Exit 0 seed; `production` refused (exit 1) |
| **G6** | n8n → `http://backend:8000` | **PASS** | `wget` ready JSON 200 |
| **G7** | `docker-compose down` | **PASS** | Stack stopped |

Contract §13 mapping: G1–G4 ≈ contract G1–G4; G5 ≈ bootstrap + demo data; G6 ≈ contract G6; G5 webhook (contract G5) **not run** — see limitations.

---

## Preconditions

1. Docker + `docker-compose` v1.29 available on host.
2. Root `.env` from `.env.example` with `POSTGRES_PASSWORD` set (not committed).
3. `n8n/.env` from `n8n/.env.example` with `N8N_ENCRYPTION_KEY`, basic auth, `N8N_BACKEND_API_TOKEN` aligned with root `.env`.
4. Fresh DB: `docker-compose -p alpstein-ai down -v` before gate (postgres volume recreated).

---

## Commands run (sanitized)

```bash
# G1 — clean clone
git clone /opt/alpstein-ai /tmp/alpstein-b29-clean-clone
cd /tmp/alpstein-b29-clean-clone
git checkout stabilization/runtime-baseline
git rev-parse HEAD baseline-b2.8-bootstrap

# Env (values not recorded — use local secrets)
cp .env.example .env    # edit POSTGRES_PASSWORD, tokens
cp n8n/.env.example n8n/.env   # edit N8N_ENCRYPTION_KEY, auth, N8N_BACKEND_API_TOKEN

# Preflight — fresh postgres volume
docker-compose -p alpstein-ai down -v

# G2
docker-compose -p alpstein-ai config

# G3
docker-compose -p alpstein-ai up -d postgres
docker inspect --format='{{.State.Health.Status}}' alpstein_postgres

# G4
docker-compose -p alpstein-ai up -d backend
docker inspect --format='{{.State.Health.Status}}' alpstein_backend
docker exec alpstein_backend python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/api/v1/health').status_code)"
docker exec alpstein_backend python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/api/v1/health/ready').status_code)"

# G5
docker-compose -p alpstein-ai --profile bootstrap run --rm backend-bootstrap
docker exec alpstein_postgres psql -U alpstein -d alpstein_ai -tAc "SELECT external_id FROM businesses ORDER BY 1;"
docker-compose -p alpstein-ai --profile bootstrap run --rm -e ALPSTEIN_AI_ENVIRONMENT=production backend-bootstrap
# Expected: exit 1, message "bootstrap refused"

# G6
docker-compose -p alpstein-ai up -d n8n
docker exec alpstein_n8n_compose wget -qO- --timeout=5 http://backend:8000/api/v1/health/ready

# G7
docker-compose -p alpstein-ai down
```

---

## Observed evidence

### Container health (peak)

| Container | Health / status |
|-----------|-----------------|
| `alpstein_postgres` | **healthy** |
| `alpstein_backend` | **healthy** |
| `alpstein_n8n_compose` | **running** |

### Backend entrypoint (excerpt)

```text
Running upgrade  -> 0001 … Running upgrade 0006 -> 0007, create leads
alembic upgrade head completed
starting uvicorn on 0.0.0.0:8000
```

### Health responses (in-container)

| Endpoint | HTTP | Body (truncated) |
|----------|------|------------------|
| `GET /api/v1/health` | 200 | `{"success":true,"data":{"status":"ok",...}}` |
| `GET /api/v1/health/ready` | 200 | `{"success":true,"data":{"status":"ready","db":"reachable",...}}` |

### Bootstrap (G5)

- Dev run: **exit 0** — `bootstrap: completed successfully`
- Businesses: `demo_barbershop_001`, `alpstein_ai_demo_001`
- Production env: **refused** — `ERROR: bootstrap refused` (exit 1, expected)

### n8n connectivity (G6)

```text
wget http://backend:8000/api/v1/health/ready → exit 0
{"success":true,"data":{"status":"ready",...,"db":"reachable"}}
```

No workflows imported or activated.

---

## Known limitations

| Item | Detail |
|------|--------|
| Clone source | Local path clone on gate host, not `git clone` from remote URL |
| Contract G5 webhook | **Not executed** — requires n8n workflow import + token + optional `OPENAI_API_KEY` |
| Host ports | Default compose has **no** `127.0.0.1:8000` bind; health checked in-container |
| Volume cleanup | `down -v` removed `alpstein_postgres_data`; `alpstein_n8n_data` **in use** by another container — not removed |
| Live Contabo | Host uvicorn `:8010`, legacy `alpstein_n8n` @ `15679` — **unchanged** |
| HTTPS / nginx | Not part of portable compose gate |
| HubSpot n8n | Not touched |

---

## Rollback / rerun

```bash
# Stop portable stack (keeps volumes)
docker-compose -p alpstein-ai down

# Full fresh rerun (postgres data loss)
docker-compose -p alpstein-ai down -v
# If n8n volume stuck: docker ps -a --filter volume=alpstein_n8n_data then stop conflicting container

rm -rf /tmp/alpstein-b29-clean-clone
```

RBU for portable baseline: git tag `baseline-b2.8-bootstrap` + this audit file.

---

## Phase B recommendation

**Portable deployment track (B2.0–B2.9):** **Complete** for compose-based clean clone on a Docker host with documented `.env` files.

**Not complete (explicitly out of gate scope):**

- Production cutover from Contabo host backend / legacy n8n
- End-to-end Gate 1 webhook smoke without manual n8n workflow steps
- Remote `git clone` on a second machine (recommended operator spot-check)

Suggested operator tag after acceptance: `baseline-b2.9-clean-clone-gate`.

---

## Related

- [`bootstrap-profile.md`](../deployment/bootstrap-profile.md)
- [`postgres-compose.md`](../deployment/postgres-compose.md)
- [`n8n-compose.md`](../deployment/n8n-compose.md)
