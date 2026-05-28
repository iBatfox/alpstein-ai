# T-e3.1a — In-flight replay protection

**Status:** done

## Goal

One processing owner per inbound idempotency scope; concurrent duplicates cannot double-process AI.

## Delivered

- Alembic `0013` — `inbound_processing_locks`
- `InboundProcessingLockService` — acquire / release / replay_count
- `WebhookMessageService` — lock before AI; in-flight conflict path
- `MessageTraceService.record_duplicate_retry` — no downgrade of active traces
- Tests: `test_inbound_processing_lock.py`, `test_e3_1a_inflight_replay.py`

## Audit

[`docs/audits/e3-1-retry-replay-protection.md`](../../docs/audits/e3-1-retry-replay-protection.md)
