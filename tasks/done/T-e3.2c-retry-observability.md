# T-e3.2c — Retry observability

**Status:** todo (blocked on E3.2b)

## Goal

Ops APIs for retry attempts and dead-letter rows.

## Requirements

- `GET /api/v1/observability/retries`
- `GET /api/v1/observability/dead-letter`
- Pydantic schemas (no forbidden fields)
- Update `specs/api/api-endpoints.md`

## Tests

- APIs scoped by tenant/business
- Filters: trace_id, delivery_id, conversation_id, event_type, scope_type
- No sensitive payload leakage
- E2/E3.1 continuity tests green

## Design

[`docs/audits/e3-2-retry-dead-letter-design.md`](../../docs/audits/e3-2-retry-dead-letter-design.md) §8
