# T-e2.2 — Conversation flow scoping (E2.2)

**Status:** done (pending review)  
**Branch:** `stabilization/runtime-baseline`

## Goal

Scope conversation lookup/creation to exactly one flow; prevent cross-flow reuse.

## Delivered

- Alembic `0009`: `conversations.flow_id` FK → `flows`, backfill from default flow, indexes
- `ConversationService`: lookup by `flow_id` + `channel` + `external_conversation_id` or customer fallback
- `validate_tenant_context(flow_id=…)` on message writes
- Webhook passes resolved flow into conversation + message paths
- Tests: `test_conversation_flow_scoping.py` + updates

## Verification

```bash
cd backend && .venv/bin/python -m pytest tests/test_conversation_flow_scoping.py tests/test_conversation_service.py tests/ -q
alembic upgrade head  # after deploy
```
