# T-e3.2b — Dead-letter persistence

**Status:** todo (blocked on E3.2a)

## Goal

Preserve permanently failed delivery/inbound operations in `dead_letter_events` without secret leakage.

## Requirements

- Migration `0016_dead_letter_events` (+ `delivery_events.status` value `dead_letter`)
- `DeadLetterService` with upsert uniqueness per scope
- Wire exhaustion from delivery PATCH and inbound replay
- Emit `replay_events.retry_exhausted` (E3.1 integration)

## Tests

- Exhausted retries create DL record
- No duplicate active DL per scope
- Tenant/business isolation on reads

## Design

[`docs/audits/e3-2-retry-dead-letter-design.md`](../../docs/audits/e3-2-retry-dead-letter-design.md) §4, §6
