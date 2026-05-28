# T-e2.3 — Message uniqueness hardening

**Status:** done (pending review)  
**Branch:** `stabilization/runtime-baseline`

## Delivered

- Alembic `0010`: `idempotency_key`, conversation-scoped partial uniques, drop business-only unique
- `message_idempotency.build_inbound_idempotency_key`
- `MessageService.find_inbound_customer_message` + savepoint on insert race
- Webhook passes `message_timestamp` for hash fallback
- Tests: `test_message_inbound_dedup.py`

## Verification

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
# 414 passed (2026-05-28)
```
