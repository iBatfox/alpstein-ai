# T-e3.1b — Terminal delivery state machine

**Status:** done

## Goal

Replay-safe delivery PATCH; terminal states cannot be corrupted.

## Delivered

- `delivery_state_machine.py` — allowed transitions
- `DeliveryVisibilityService.report_status` — illegal transition no-op
- Tests: `test_delivery_state_machine.py`

## Audit

[`docs/audits/e3-1-retry-replay-protection.md`](../../docs/audits/e3-1-retry-replay-protection.md)
