# E3.1 — Retry and replay protection (implementation audit)

**Date:** 2026-05-28  
**Branch:** `stabilization/runtime-baseline`  
**Slices:** E3.1a, E3.1b, E3.1c — **implemented**

## Summary

Additive backend hardening for concurrent duplicate ingress, terminal-safe delivery PATCH, and replay observability. No queues, workers, or runtime redesign.

| Slice | Deliverable | Status |
|-------|-------------|--------|
| E3.1a | `inbound_processing_locks` + `InboundProcessingLockService` | Done |
| E3.1b | `delivery_state_machine` + no-op illegal PATCH | Done |
| E3.1c | `replay_events` + `GET /api/v1/observability/replays` | Done |

## Validation

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
# 467 passed (2026-05-28)

backend/.venv/bin/python scripts/verify/e2_observability_verification.py --run-pytest
```

Alembic head: **`0014`** (`replay_events`).

## E3.1a — In-flight replay protection

- Migration `0013_inbound_processing_locks.py`
- Unique scope: `(business_id, conversation_id, idempotency_key)`
- `WebhookMessageService`: acquire lock before AI; conflict → in-flight duplicate response (`is_duplicate=true`, no outbound)
- `MessageTraceService.record_duplicate_retry`: does not downgrade `accepted` / `processing` / `completed` to `skipped_duplicate`
- Tests: `test_inbound_processing_lock.py`, `test_e3_1a_inflight_replay.py`

## E3.1b — Terminal delivery state machine

- `delivery_state_machine.py` — `delivered` and `skipped` terminal; `failed` → `retrying` only
- `DeliveryVisibilityService.report_status` — illegal transition no-op (n8n-stable); records `illegal_transition` replay event (E3.1c)
- Tests: `test_delivery_state_machine.py`

## E3.1c — Replay observability

- Migration `0014_replay_events.py`
- `ReplayEventService.record` / `list_events` with tenant + business filters
- Webhook: `duplicate_retry`, `replay_ignored` (in-flight)
- Delivery PATCH: `illegal_transition` with `from_status` / `to_status` metadata (no secrets)
- API: `GET /api/v1/observability/replays` (webhook token)
- Tests: `test_e3_1c_replay_observability.py`

## Known tradeoffs

- Website hash idempotency may suppress legitimate repeated identical text (unchanged; document only).
- Stale `processing` locks: `expires_at` column present; sweeper not in MVP scope.
- Lock `record_replay_attempt` increments `replay_count` on lock row; detailed audit in `replay_events`.

## Ops rollout (operator)

1. `alembic upgrade head` (0013, 0014)
2. Restart backend on host / compose
3. `GET /api/v1/health` + one Gate 1 webhook (duplicate + normal)
4. Optional: query `GET /api/v1/observability/replays?tenant_id=…&business_id=…`

Rollback: deploy previous backend revision; downgrades `0014`/`0013` only if no production rows depend on new tables.

## Design reference

[`e3-1-retry-replay-protection-design.md`](e3-1-retry-replay-protection-design.md)
