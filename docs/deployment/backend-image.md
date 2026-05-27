# Backend container image (B2.3–B2.6)

**Contract:** [`deployment-contract.md`](deployment-contract.md)  
**Dockerfile:** [`backend/Dockerfile`](../../backend/Dockerfile)  
**Entrypoint:** [`backend/docker-entrypoint.sh`](../../backend/docker-entrypoint.sh)  
**Compose:** [`docker-compose.yml`](../../docker-compose.yml) service `backend`  
**Production deps:** [`backend/requirements-prod.txt`](../../backend/requirements-prod.txt)

Reproducible backend image with **migrate-then-serve** at container start, orchestrated by root compose **B2.6+**.

---

## Lifecycle ownership (B2.5)

| Step | Owner | When |
|------|--------|------|
| Postgres healthy | `postgres` service / operator | Before backend container start |
| Optional TCP wait | `docker-entrypoint.sh` (`pg_isready`) | Container start |
| `alembic upgrade head` | **Backend container entrypoint** | Every backend container start |
| `uvicorn` | **Backend container entrypoint** (`exec`) | After successful migration |
| Readiness probe | `GET /api/v1/health/ready` (B2.4) | Compose healthcheck + operator |
| Compose start order | `depends_on: postgres` (healthy) | B2.6 |

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

### Compose stack (B2.6)

From repo root (`.env` with `POSTGRES_PASSWORD` set):

```bash
docker-compose -p alpstein-ai config
docker-compose -p alpstein-ai up -d postgres backend

# Dev overlay — localhost curl
docker-compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d postgres backend

curl -sS http://127.0.0.1:8000/api/v1/health
curl -sS http://127.0.0.1:8000/api/v1/health/ready

docker inspect --format='{{.State.Health.Status}}' alpstein_backend
docker-compose -p alpstein-ai logs backend
```

Compose healthcheck (inside container, no curl/wget — uses **httpx** already in image):

```text
python -c "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/health/ready', timeout=5.0); r.raise_for_status()"
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

## Compose service summary (B2.6)

| Attribute | Value |
|-----------|--------|
| Service name | `backend` |
| Container name | `alpstein_backend` |
| Image | `alpstein-ai-backend:local` (build) |
| Depends on | `postgres` (`service_healthy`) |
| Database URL host | `postgres` (not host gateway) |
| Internal port | `8000` |
| Host port (default) | **none** |
| Host port (dev overlay) | `127.0.0.1:8000` |

Environment interpolated from repo root `.env` (see `.env.example`): `ALPSTEIN_AI_DATABASE_URL`, `ALPSTEIN_AI_ENVIRONMENT`, `N8N_BACKEND_API_TOKEN`, `OPENAI_API_KEY`.

## Out of scope

- n8n service in root compose (**B2.7**)
- Live Contabo host uvicorn replacement
- n8n workflow changes

---

## Related

- [`postgres-compose.md`](postgres-compose.md)
- [`backend/.env.example`](../../backend/.env.example)
