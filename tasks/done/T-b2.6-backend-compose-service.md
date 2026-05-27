# T-b2.6 — Backend Service in Compose (B2.6)

**Status:** done (awaiting operator review)  
**Phase:** B2 — Deployment Portability  
**Depends on:** [`T-b2.5-backend-entrypoint-contract.md`](T-b2.5-backend-entrypoint-contract.md)  
**Rollback anchors:** `baseline-pre-b2.5`, `baseline-b2.5-entrypoint`

## Goal

Wire `backend` into root `docker-compose.yml` with postgres `depends_on` (healthy), internal DNS, and readiness healthcheck.

## Scope

- `docker-compose.yml` — `postgres` + `backend`
- `docker-compose.dev.yml` — optional `127.0.0.1:8000:8000`
- Root `.env.example` — compose backend vars
- Deployment docs + project status
- No n8n service, no Contabo changes, no migrations

## Deliverables

- [x] `backend` service: build, `alpstein_backend`, `depends_on` postgres healthy
- [x] `ALPSTEIN_AI_DATABASE_URL` → `@postgres:5432`
- [x] Healthcheck `GET /api/v1/health/ready` via httpx (no curl added)
- [x] Docs updated
- [x] Agent validation (2026-05-27): `config` OK; `up -d postgres backend` — postgres healthy, backend healthy; migrations 0001→0007; `/api/v1/health` + `/ready` 200 in-container; no secrets in logs. Dev overlay port 8000 skipped on host (port in use); use `BACKEND_HOST_PORT` or base compose.

## Acceptance

- [x] Migrations before uvicorn (entrypoint unchanged)
- [x] No secrets in git
- [x] No n8n in root compose
- [ ] Operator: tag `baseline-b2.6-compose` after review

## Rollback

```bash
docker-compose -p alpstein-ai down
git checkout baseline-b2.5-entrypoint -- docker-compose.yml docker-compose.dev.yml
```

Legacy host uvicorn `:8010` unaffected.

## Next

**B2.7** — n8n network integration (`BACKEND_BASE_URL=http://backend:8000`)
