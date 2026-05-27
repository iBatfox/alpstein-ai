# Postgres compose service (B2.2)

**Contract:** [`deployment-contract.md`](deployment-contract.md) §7  
**Compose:** [`docker-compose.yml`](../../docker-compose.yml) (postgres only)

Dedicated Alpstein PostgreSQL — **not** the legacy `backend_postgres` / `bitrix_app` instance.

---

## Service summary

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

---

## Environment variables

Set in repo root `.env` (copy from `.env.example`). **Never commit `.env`.**

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `POSTGRES_DB` | No | `alpstein_ai` | Database name |
| `POSTGRES_USER` | No | `alpstein` | Superuser for init |
| `POSTGRES_PASSWORD` | **Yes** | — | Postgres password |
| `POSTGRES_HOST_PORT` | No | `15433` | Dev overlay only |

Backend URL (when running Alembic from host against dev overlay):

```text
ALPSTEIN_AI_DATABASE_URL=postgresql+asyncpg://alpstein:<POSTGRES_PASSWORD>@127.0.0.1:15433/alpstein_ai
```

Backend URL (future backend container on same compose network):

```text
ALPSTEIN_AI_DATABASE_URL=postgresql+asyncpg://alpstein:<POSTGRES_PASSWORD>@postgres:5432/alpstein_ai
```

`POSTGRES_PASSWORD` must match the password segment in `ALPSTEIN_AI_DATABASE_URL`.

---

## Healthcheck

```text
pg_isready -U alpstein -d alpstein_ai
```

Compose marks the service healthy when PostgreSQL accepts connections. Interval 5s, 5 retries, 10s start period.

If you change `POSTGRES_USER` or `POSTGRES_DB` from defaults, update the healthcheck in `docker-compose.yml` to match.

---

## Operator commands (clean clone / dev)

From repo root:

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD (and optional POSTGRES_HOST_PORT)

# Production-style (no host port)
docker-compose -p alpstein-ai config
docker-compose -p alpstein-ai up -d postgres
docker-compose -p alpstein-ai ps
docker-compose -p alpstein-ai exec postgres pg_isready -U alpstein -d alpstein_ai

# Dev overlay (localhost psql / host Alembic)
docker-compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d postgres
```

Verify health:

```bash
docker inspect --format='{{.State.Health.Status}}' alpstein_postgres
```

Schema is **empty** after first start — run migrations from `backend/` (B2.5+ entrypoint; manual until then):

```bash
cd backend
export ALPSTEIN_AI_DATABASE_URL=postgresql+asyncpg://alpstein:YOUR_PASSWORD@127.0.0.1:15433/alpstein_ai
alembic upgrade head
```

---

## Rollback

**Scope:** B2.2 postgres stack only — does not affect legacy `backend_postgres` or live production.

1. Stop stack: `docker-compose -p alpstein-ai down`
2. **Data loss warning:** remove volume only after backup decision:  
   `docker volume rm alpstein_postgres_data`
3. Revert git commit containing `docker-compose.yml` if removing the slice entirely

RBU for postgres-only: compose file revision + volume snapshot ID (if data must be preserved).

---

## Out of scope (B2.2)

- Backend container / Dockerfile
- n8n service in root compose (stays in `n8n/docker-compose.yml` until B2.7)
- Migrating data from `bitrix_app`
- Changing Contabo live services

---

## Related

- [`database-recovery.md`](../ops/database-recovery.md) — Alembic chain after empty DB
- [`README.md`](README.md) — deployment doc index
