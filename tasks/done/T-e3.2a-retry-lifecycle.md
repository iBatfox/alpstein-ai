# T-e3.2a — Retry lifecycle

**Status:** todo (blocked on E3.2 design approval)

## Goal

Formal retry state machine, `retry_attempts` append log, configurable max retries for delivery PATCH and inbound lock replay.

## Requirements

- Migration `0015_retry_attempts` (or agreed id)
- `RetryLifecycleService`
- Extend `delivery_state_machine` + `DeliveryVisibilityService`
- Wire `InboundProcessingLockService` exhaustion counting
- Env: `ALPSTEIN_DELIVERY_MAX_RETRIES`, `ALPSTEIN_INBOUND_PROVIDER_RETRY_MAX`

## Tests

- Retry counter increments
- Max retry enforced
- Idempotent duplicate retry at cap
- E3.1 regression suite green

## Design

[`docs/audits/e3-2-retry-dead-letter-design.md`](../../docs/audits/e3-2-retry-dead-letter-design.md) §5–7
