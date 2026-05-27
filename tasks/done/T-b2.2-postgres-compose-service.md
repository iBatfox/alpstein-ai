# T-b2.2 — Postgres Compose Service (B2.2)

**Status:** done (awaiting operator verification on clean clone)  
**Phase:** B2 — Deployment Portability  
**Depends on:** [`T-b2.1-deployment-governance-artifacts.md`](T-b2.1-deployment-governance-artifacts.md)

## Goal

Introduce dedicated portable PostgreSQL ownership via compose — postgres service only.

## Scope

- Root `docker-compose.yml` + optional `docker-compose.dev.yml`
- Env template updates for `POSTGRES_*`
- Ops doc `docs/deployment/postgres-compose.md`
- No backend Dockerfile, backend service, runtime changes, or legacy DB migration

## Deliverables

- [x] `docker-compose.yml` — `postgres:15`, healthcheck, volume, internal network
- [x] `docker-compose.dev.yml` — dev-only `127.0.0.1:15433`
- [x] `.env.example` — `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST_PORT`
- [x] `backend/.env.example` — URL alignment notes
- [x] `docs/deployment/postgres-compose.md`
- [x] Contract + project-status updates

## Acceptance

- [x] Compose defines postgres only
- [x] Healthcheck `pg_isready`
- [x] Database `alpstein_ai`
- [x] No backend container / Dockerfile / runtime code changes
- [x] Legacy `backend_postgres` not referenced
- [ ] Operator: `docker-compose -p alpstein-ai up -d postgres` on dev machine

## Rollback

`docker-compose -p alpstein-ai down` then `docker volume rm alpstein_postgres_data` after backup decision.

## Next

**B2.3** — Backend Dockerfile (image only; not wired into root compose until B2.6)
