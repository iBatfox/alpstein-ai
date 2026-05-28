# T-e2.5 — Observability API extensions

**Status:** done (pending review)  
**Branch:** `stabilization/runtime-baseline`

## Delivered

- `GET /api/v1/observability/traces/{trace_id}`
- `GET /api/v1/observability/traces` (lookup by inbound/external message id)
- `GET /api/v1/observability/conversations/{conversation_id}/traces`
- Webhook `data.trace` — `trace_id`, `correlation_id`, `processing_status`
- Tests: `test_observability_api.py`, webhook trace tests

## Verification

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```
