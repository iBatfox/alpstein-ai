# E2 — End-to-end observability verification audit

**Date:** 2026-05-28  
**Branch:** `stabilization/runtime-baseline`  
**Slice:** E2.7 — verification only (no runtime redesign)

## Verification plan

| Area | Method |
|------|--------|
| Route registration | Static: FastAPI `app.routes` + pytest |
| Schema / migrations | Alembic head `0012`; `message_traces` + `delivery_events` in metadata |
| Inbound → trace → outbound → delivery | Webhook service tests (telegram + website_chat) |
| Duplicate retry | No new outbound/delivery; trace id preserved |
| Observability APIs | HTTP tests: trace + delivery GET/list; failed states |
| Tenant isolation | Cross-`business_id` GET → 404 |
| Langfuse | Optional: `langfuse_trace_id` on `mark_completed` when set; `None` when disabled |
| Runtime harness | `scripts/verify/e2_observability_verification.py` |

## Chain under test

```text
POST /api/v1/webhook/message
  → save inbound message
  → message_traces (accepted → processing → completed | skipped_duplicate | failed)
  → save outbound AI message (non-duplicate)
  → delivery_events (pending)
  → response: data.trace + data.delivery

n8n channel send (out of backend scope)
  → PATCH /api/v1/observability/deliveries/{id} (delivered | failed)

GET observability APIs (tenant_id + business_id scoped)
```

## Automated evidence

| Check | Location |
|-------|----------|
| Continuity pytest suite | `backend/tests/test_e2_observability_continuity.py` |
| E2.4 trace wiring | `backend/tests/test_webhook_message_trace.py` |
| E2.5 trace APIs | `backend/tests/test_observability_api.py` |
| E2.6 delivery APIs | `backend/tests/test_delivery_observability_api.py` |
| Runtime harness | `scripts/verify/e2_observability_verification.py` |

### Commands (developer / CI)

```bash
cd /opt/alpstein-ai/backend
.venv/bin/python -m pytest tests/test_e2_observability_continuity.py -q
.venv/bin/python -m pytest tests/ -q

cd /opt/alpstein-ai
PYTHONPATH=backend python3 scripts/verify/e2_observability_verification.py --run-pytest
```

### Production operator (post-deploy)

1. `alembic upgrade head` — confirm head `0012` on target DB.
2. `GET /api/v1/health` and readiness as per ops runbook.
3. Gate 1 test webhook — confirm `data.trace` and `data.delivery` when outbound saved.
4. `GET /api/v1/observability/traces/{trace_id}?tenant_id=…&business_id=…` — matches webhook `trace_id`.
5. After n8n send: `PATCH …/deliveries/{delivery_id}` with `status: delivered` (when wired).
6. Duplicate retry — `is_duplicate: true`, no new `data.delivery` on second call.

**Do not** modify HubSpot n8n (`integrationhubspot_n8n`). Alpstein n8n: `alpstein_n8n` @ `127.0.0.1:15679`.

## Results (code verification)

| Item | Status |
|------|--------|
| Observability routes registered | Verified (static + pytest) |
| Alembic head `0012` | Verified |
| Trace ↔ outbound ↔ delivery correlation | Verified (pytest) |
| Duplicate: no duplicate delivery row | Verified |
| Telegram + Website Chat paths | Verified (parametrized pytest) |
| Langfuse optional | Verified |
| Tenant/business isolation on GET | Verified |
| Failed trace / failed delivery visibility | Verified |

## Gaps / follow-up

| Gap | Owner | Notes |
|-----|-------|-------|
| n8n `PATCH` delivery after channel send | n8n / ops | Backend `pending` until PATCH; document in ingress workflow |
| Live Postgres integration test | optional future | Current suite uses mocked sessions |
| Production gate re-run with execution IDs | ops | Record in this doc when E2.7 promoted |

## Verdict

**PASS (code + test harness)** — E2 observability chain is consistent in backend tests and static runtime checks. Production sign-off requires operator gate + migration apply on target environment.
