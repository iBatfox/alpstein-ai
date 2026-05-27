# Backend container image (B2.3–B2.5)

**Contract:** [`deployment-contract.md`](deployment-contract.md)  
**Dockerfile:** [`backend/Dockerfile`](../../backend/Dockerfile)  
**Entrypoint:** [`backend/docker-entrypoint.sh`](../../backend/docker-entrypoint.sh)  
**Production deps:** [`backend/requirements-prod.txt`](../../backend/requirements-prod.txt)

Reproducible backend image with **migrate-then-serve** at container start. Root `docker-compose.yml` adds the `backend` service in **B2.6** only.

---

## Lifecycle ownership (B2.5)

| Step | Owner | When |
|------|--------|------|
| Postgres healthy | `postgres` service / operator | Before backend container start |
| Optional TCP wait | `docker-entrypoint.sh` (`pg_isready`) | Container start |
| `alembic upgrade head` | **Backend container entrypoint** | Every backend container start |
| `uvicorn` | **Backend container entrypoint** (`exec`) | After successful migration |
| Readiness probe | `GET /api/v1/health/ready` (B2.4) | Orchestrator / operator |

**Not in scope:** separate migration-only container, init containers, Kubernetes.

---

## Entrypoint behavior

Script: `backend/docker-entrypoint.sh`

```text
1. WAIT_FOR_POSTGRES (default true) → pg_isready loop (bounded)
2. Require ALPSTEIN_AI_DATABASE_URL
3. alembic upgrade head  → exit 1 on failure (uvicorn never runs)
4. exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

| Property | Behavior |
|----------|----------|
| Shell | `#!/bin/sh` with `set -eu` |
| Secrets | Never printed; only host/port/attempt counts logged |
| Wait loop | Max 30 attempts, 2s delay (configurable); fails loudly |
| Migration failure | Non-zero exit; process stops |
| Image build | **No** `alembic upgrade` during `docker build` |

### Entrypoint environment (optional)

| Variable | Default | Purpose |
|----------|---------|---------|
| `WAIT_FOR_POSTGRES` | `true` | Set `false` to skip `pg_isready` wait |
| `POSTGRES_HOST` | `postgres` | Wait target host |
| `POSTGRES_PORT` | `5432` | Wait target port |
| `POSTGRES_USER` | `alpstein` | `pg_isready -U` |
| `POSTGRES_WAIT_MAX_ATTEMPTS` | `30` | Bounded wait (~60s default) |
| `POSTGRES_WAIT_DELAY_SECONDS` | `2` | Sleep between attempts |

Required for migrations (from `backend/.env.example`):

- `ALPSTEIN_AI_DATABASE_URL`

---

## Image summary

| Attribute | Value |
|-----------|--------|
| Base image | `python:3.12-slim-bookworm` |
| Python | **3.12** |
| Workdir | `/app` |
| User | `alpstein` (uid 1000, non-root) |
| Exposed port | `8000` |
| ENTRYPOINT | `/app/docker-entrypoint.sh` |
| Extra OS packages | `libpq5`, `postgresql-client` (`pg_isready`) |

---

## Production dependencies

See `requirements-prod.txt` — runtime only; **pytest** excluded (use `requirements.txt` for dev/CI).

---

## Build

```bash
docker build -f backend/Dockerfile -t alpstein-ai-backend:local backend
```

---

## Validation

### Build + import (no DB)

```bash
docker build -f backend/Dockerfile -t alpstein-ai-backend:local backend

docker run --rm --entrypoint python alpstein-ai-backend:local \
  -c "import app.main; print('import ok')"
```

### Migration failure blocks uvicorn

```bash
docker run --rm \
  -e WAIT_FOR_POSTGRES=false \
  -e ALPSTEIN_AI_DATABASE_URL=postgresql+asyncpg://alpstein:bad@127.0.0.1:1/nodb \
  alpstein-ai-backend:local
# Expect: alembic error, exit code != 0, no "starting uvicorn"
```

### Full manual smoke (operator — B2.6 prep)

```bash
# Terminal 1 — postgres (see postgres-compose.md)
docker-compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d postgres

# Terminal 2 — backend container (not in compose yet)
docker run --rm -p 8000:8000 \
  --network alpstein_internal \
  -e WAIT_FOR_POSTGRES=true \
  -e POSTGRES_HOST=postgres \
  -e ALPSTEIN_AI_DATABASE_URL=postgresql+asyncpg://alpstein:YOUR_PASSWORD@postgres:5432/alpstein_ai \
  -e ALPSTEIN_AI_ENVIRONMENT=development \
  -e N8N_BACKEND_API_TOKEN=dev-token \
  alpstein-ai-backend:local

curl -sS http://127.0.0.1:8000/api/v1/health/ready
```

---

## `.dockerignore`

Excludes: `.venv`, `tests/`, `scripts/`, `.env`, caches.

---

## Rollback

| Action | Effect |
|--------|--------|
| Revert `docker-entrypoint.sh` + Dockerfile ENTRYPOINT | Image returns to uvicorn-only CMD (B2.3) |
| `docker rmi alpstein-ai-backend:local` | Drop local image |
| Git tag `baseline-pre-b2.5` | Known pre-entrypoint baseline |

RBU: image digest + entrypoint script revision.

---

## Out of scope

- `backend` in root `docker-compose.yml` (**B2.6**)
- Live Contabo host uvicorn replacement
- n8n workflow changes

---

## Related

- [`postgres-compose.md`](postgres-compose.md)
- [`backend/.env.example`](../../backend/.env.example)
