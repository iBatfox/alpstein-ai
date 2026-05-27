# T-b2.5 — Backend Entrypoint Contract (B2.5)

**Status:** done (awaiting operator review)  
**Phase:** B2 — Deployment Portability  
**Depends on:** [`T-b2.4-readiness-health-endpoint.md`](T-b2.4-readiness-health-endpoint.md) (if present), [`T-b2.3-backend-dockerfile-image-build.md`](T-b2.3-backend-dockerfile-image-build.md)  
**Baseline tag:** `baseline-pre-b2.5`

## Goal

Deterministic backend container startup: wait for postgres → `alembic upgrade head` → `exec uvicorn`.

## Scope

- `backend/docker-entrypoint.sh`
- `backend/Dockerfile` ENTRYPOINT wiring
- Deployment docs + contract §10 lifecycle
- No root compose `backend` service (B2.6)
- No live Contabo changes

## Ownership

| Concern | Owner |
|---------|--------|
| Migrate-then-serve | **Backend container entrypoint** (this slice) |
| Postgres availability | Postgres service / operator |
| Separate migration job | **Not** in MVP — deferred |
| Compose `depends_on` | **B2.6** |

## Deliverables

- [x] `docker-entrypoint.sh` — `set -eu`, pg_isready wait, alembic, exec uvicorn
- [x] Dockerfile — `postgresql-client`, ENTRYPOINT, no build-time migrations
- [x] Docs updated

## Acceptance

- [x] Migration failure exits before uvicorn
- [x] No secrets logged
- [x] `docker-compose.yml` still postgres-only
- [x] Agent validation: `docker build`, migration-failure exit 1, no uvicorn on failure, no secret keywords in logs
- [ ] Operator: full stack smoke with postgres + backend container (manual, B2.6 prep)

## Rollback

Revert entrypoint commit; rebuild image; previous tag `baseline-pre-b2.5` or prior image digest.

## Next

**B2.6** — Add `backend` service to root `docker-compose.yml`
