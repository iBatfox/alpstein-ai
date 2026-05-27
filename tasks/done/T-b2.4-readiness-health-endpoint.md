# T-b2.4 — Readiness health endpoint

**Status:** done  
**Phase:** B2 — Deployment Portability  
**Date:** 2026-05-27

## Goal

Add `/api/v1/health/ready` to verify backend readiness for orchestrated startup.

## Scope (small backend slice)

- Keep existing liveness behavior at `GET /api/v1/health` unchanged.
- Add readiness at `GET /api/v1/health/ready` that checks PostgreSQL connectivity with `SELECT 1`.
- No AI/OpenAI/Langfuse/n8n calls; no DB writes.

## Endpoint behavior summary

- `GET /api/v1/health`
  - returns `200` with the existing `{ success: true, data: { status: "ok", ... } }` envelope
  - does not require DB
- `GET /api/v1/health/ready`
  - returns `200` when DB is reachable (query succeeds and `SELECT 1` returns `1`)
  - returns non-2xx (`503`) with structured failure when DB is unreachable

## DB check implementation summary

- Implemented in `backend/app/api/routes/health.py`
- Uses existing async DB/session infrastructure:
  - `session: AsyncSession = Depends(get_db_session)`
  - executes `SELECT 1` via `await session.execute(text("SELECT 1"))`
  - validates result via `scalar_one_or_none()`
- Failure path:
  - catches any exception during connectivity/query
  - returns `success: false`, `error.code: "DATABASE_ERROR"`, `error.message` without leaking secrets

## Test summary

- Updated `backend/tests/test_health.py`
- Added readiness tests with mocked DB dependency override:
  - success path: dummy session returns `scalar_one_or_none() == 1`
  - failure path: dummy session raises on `execute()`
- Liveness test continues to assert the exact existing response JSON.

## Validation commands/results

```bash
cd /opt/alpstein-ai/backend
./.venv/bin/pytest tests/test_health.py -q
```

Result:
- `3 passed`

## Rollback note

- Orchestrators can temporarily rely on liveness (`/api/v1/health`) if readiness probes cause issues.
- Safe rollback is reverting the backend code slice that introduced `/api/v1/health/ready`.

## Remaining drift before B2.5

- Readiness checks DB connectivity only (no optional strict mode revision check yet).
- Docker-compose backend wiring / readiness-dependent orchestration remains deferred to later B2 phases.

