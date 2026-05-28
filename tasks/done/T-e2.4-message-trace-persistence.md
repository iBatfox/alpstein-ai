# T-e2.4 — Message trace persistence

**Status:** done (pending review)  
**Branch:** `stabilization/runtime-baseline`

## Delivered

- Alembic `0011_message_traces.py`
- `MessageTrace` model + `MessageTraceService`
- Webhook wiring: accepted → processing → completed / skipped_duplicate / failed
- Langfuse trace id captured when available (optional)
- Tests: `test_message_trace_service.py`, `test_webhook_message_trace.py`

## Verification

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```
