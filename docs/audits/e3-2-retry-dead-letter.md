# E3.2 — Retry / dead-letter (implementation audit)

**Date:** 2026-05-28  
**Branch:** `stabilization/runtime-baseline`  
**Status:** implemented

## Summary

Deterministic retry accounting and dead-letter persistence without queues or runtime redesign.

| Slice | Deliverable |
|-------|-------------|
| E3.2a | `retry_attempts`, `RetryLifecycleService`, delivery retry cap on repeated `failed` PATCH |
| E3.2b | `dead_letter_events`, `dead_letter` delivery status, inbound lock exhaustion |
| E3.2c | `GET /observability/retries`, `GET /observability/dead-letter` |

## Validation

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
# 475 passed (2026-05-28)

backend/.venv/bin/python scripts/verify/e2_observability_verification.py --run-pytest
# 9/9 PASS, Alembic head 0016
```

## Key behavior

- **Repeated `failed` PATCH** increments `delivery_events.retry_count` and appends `retry_attempts` even if n8n never sends `retrying`.
- At max retries (env `ALPSTEIN_AI_DELIVERY_MAX_RETRIES`, default 3): `delivery_events.status = dead_letter`, `dead_letter_events` upsert, `replay_events.retry_exhausted`.
- **Terminal delivery errors** (`chat_not_found`, `invalid_chat_id`, env list) dead-letter on first `failed`.
- **Inbound provider redelivery:** `inbound_processing_locks.replay_count`; at max (`ALPSTEIN_AI_INBOUND_PROVIDER_RETRY_MAX`, default 5) → inbound dead-letter + `retry_exhausted`.
- **E3.1 preserved:** `delivered` terminal guard, in-flight replay, `replay_events` for duplicate/illegal PATCH.
- **OpenAI:** no in-process retry (documented out of scope).

## Migrations

- `0015_retry_attempts`
- `0016_dead_letter_events`

## Ops rollout

1. `cd backend && alembic upgrade head`
2. Restart backend
3. Optional env: `ALPSTEIN_AI_DELIVERY_MAX_RETRIES`, `ALPSTEIN_AI_INBOUND_PROVIDER_RETRY_MAX`, `ALPSTEIN_AI_DELIVERY_TERMINAL_ERROR_TYPES`
4. Smoke: one delivery `failed` PATCH storm in staging; query `GET /observability/dead-letter`

## Follow-up (not in E3.2)

- n8n workflow branch on `retrying` / `dead_letter` for transport retry loops
- OpenAI retry/dead-letter worker (future task)
- Dead-letter resolution API
- Lock TTL sweeper for stale `processing`
