# T-e2.6 — Delivery visibility

**Status:** done  
**Branch:** `stabilization/runtime-baseline`

## Goal

Persist outbound delivery lifecycle (`pending` → `delivered` / `failed` / …) and expose read/report observability APIs.

## Done

- Alembic `0012_delivery_events.py` + `DeliveryEvent` model
- `DeliveryVisibilityService` — create pending (idempotent by `outbound_message_id`), mark delivered/failed/skipped/retrying
- Webhook: `pending` on outbound AI save; `data.delivery` in response
- Observability: `GET /deliveries/{id}`, `GET /conversations/{id}/deliveries`, `PATCH /deliveries/{id}` (n8n reports channel outcome)
- Tests: `test_delivery_visibility_service.py`, `test_delivery_observability_api.py`, webhook trace wiring
- Docs/specs updated

## Follow-up

- n8n workflows: call `PATCH /api/v1/observability/deliveries/{delivery_id}` after Telegram Send / Website Respond

## Out of scope

Queues, dashboard, n8n PostgreSQL writes, backend channel send
