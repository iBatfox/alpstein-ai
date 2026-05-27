# Postgres + backend + n8n compose (B2.2 / B2.6 / B2.7)

**Contract:** [`deployment-contract.md`](deployment-contract.md) §7–§8  
**Compose:** [`docker-compose.yml`](../../docker-compose.yml) (`postgres` + `backend` + `n8n`)  
**n8n detail:** [`n8n-compose.md`](n8n-compose.md)

Dedicated Alpstein PostgreSQL — **not** the legacy `backend_postgres` / `bitrix_app` instance.

---

## Service summary

### Postgres

| Attribute | Value |
|-----------|--------|
| Compose service name | `postgres` |
| Container name | `alpstein_postgres` |
| Image | `postgres:15` |
| Database | `alpstein_ai` |
| User | `alpstein` |
| Internal port | `5432` |
| Network | `alpstein_internal` |
| Volume | `alpstein_postgres_data` |
| Host port (default) | **none** |
| Host port (dev overlay) | `127.0.0.1:15433` → `5432` |

### Backend (B2.6)

| Attribute | Value |
|-----------|--------|
| Compose service name | `backend` |
| Container name | `alpstein_backend` |
| Build | `backend/Dockerfile` |
| Depends on | `postgres` healthy |
| Internal port | `8000` |
| Host port (dev overlay) | `127.0.0.1:8000` → `8000` |

---

## Environment variables

Set in repo root `.env` (copy from `.env.example`). **Never commit `.env`.**

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `POSTGRES_DB` | No | `alpstein_ai` | Database name |
| `POSTGRES_USER` | No | `alpstein` | Superuser for init |
| `POSTGRES_PASSWORD` | **Yes** | — | Postgres password |
| `POSTGRES_HOST_PORT` | No | `15433` | Dev overlay postgres only |
| `BACKEND_HOST_PORT` | No | `8000` | Dev overlay backend only |
| `ALPSTEIN_AI_ENVIRONMENT` | No | `development` | Backend Settings |
| `N8N_BACKEND_API_TOKEN` | For webhooks | — | Shared with n8n (when wired) |
| `OPENAI_API_KEY` | For live AI | — | Backend only |

`ALPSTEIN_AI_DATABASE_URL` is **constructed in compose** (not copied manually):

```text
postgresql+asyncpg://alpstein:<POSTGRES_PASSWORD>@postgres:5432/alpstein_ai
```

Host Alembic against dev postgres port (without backend container):

```text
ALPSTEIN_AI_DATABASE_URL=postgresql+asyncpg://alpstein:<POSTGRES_PASSWORD>@127.0.0.1:15433/alpstein_ai
```

---

## Healthchecks

**Postgres:**

```text
pg_isready -U alpstein -d alpstein_ai
```

**Backend** (inside container; DB `SELECT 1` only — no webhook/OpenAI):

```text
GET http://127.0.0.1:8000/api/v1/health/ready
```

Implemented via `httpx` in compose healthcheck `CMD-SHELL`. `start_period: 90s` allows first-run migrations.

---

## Operator commands (clean clone / dev)

From repo root:

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD; optional N8N_BACKEND_API_TOKEN, OPENAI_API_KEY

# Internal network only (no host ports)
docker-compose -p alpstein-ai config
docker-compose -p alpstein-ai up -d postgres backend
docker-compose -p alpstein-ai ps

# Dev overlay (localhost curl + psql)
docker-compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d postgres backend

curl -sS http://127.0.0.1:8000/api/v1/health
curl -sS http://127.0.0.1:8000/api/v1/health/ready
```

Verify health:

```bash
docker inspect --format='{{.State.Health.Status}}' alpstein_postgres
docker inspect --format='{{.State.Health.Status}}' alpstein_backend
```

Migrations run automatically on backend start (`docker-entrypoint.sh` → `alembic upgrade head`).

---

## Rollback

**Scope:** portable compose stack — does not affect legacy `backend_postgres` or live production.

1. Stop stack: `docker-compose -p alpstein-ai down`
2. **Data loss warning:** remove volume only after backup:  
   `docker volume rm alpstein_postgres_data`
3. Revert to tag `baseline-b2.5-entrypoint` to remove backend service from compose

RBU: compose file revision + volume snapshot ID.

---

## Out of scope

- n8n service in root compose (**B2.7**)
- Migrating data from `bitrix_app`
- Changing Contabo live services

---

## Related

- [`backend-image.md`](backend-image.md) — entrypoint, image build
- [`database-recovery.md`](../ops/database-recovery.md) — Alembic chain
- [`README.md`](README.md) — deployment doc index
