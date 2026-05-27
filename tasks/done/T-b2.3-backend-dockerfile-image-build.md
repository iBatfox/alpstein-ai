# T-b2.3 — Backend Dockerfile / Image Build (B2.3)

**Status:** done (image built and import-validated on dev host)  
**Phase:** B2 — Deployment Portability  
**Depends on:** [`T-b2.2-postgres-compose-service.md`](T-b2.2-postgres-compose-service.md)

## Goal

Reproducible backend container image without compose wiring or migrate-on-start.

## Scope

- `backend/requirements-prod.txt`, `backend/Dockerfile`, `backend/.dockerignore`
- `docs/deployment/backend-image.md`
- No root compose backend service, no readiness endpoint, no entrypoint migrations

## Deliverables

- [x] `requirements-prod.txt` (no pytest; adds uvicorn)
- [x] `Dockerfile` — python:3.12-slim-bookworm, user alpstein, port 8000
- [x] `.dockerignore`
- [x] Build: `docker build -f backend/Dockerfile -t alpstein-ai-backend:local backend`
- [x] Validation: `import app.main` in container without DB

## Acceptance

- [x] Image builds; pytest not in prod requirements
- [x] No secrets in image; no alembic in Dockerfile RUN
- [x] `docker-compose.yml` unchanged

## Rollback

`docker rmi alpstein-ai-backend:local` or revert Dockerfile commit.

## Next

**B2.4** — `GET /api/v1/health/ready` (backend code slice)
