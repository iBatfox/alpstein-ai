# T-e3.6c — Spam observability

**Status:** todo (blocked on E3.6b)

## Goal

Operators can answer why traffic was blocked/throttled without message content.

## Design

[`docs/audits/e3-6-anti-spam-protection-design.md`](../../docs/audits/e3-6-anti-spam-protection-design.md) §7

## Requirements

- `GET /api/v1/observability/spam-decisions` (tenant_id + business_id required)
- `GET /api/v1/observability/spam-containments`
- Optional adapter fields: `spam_decision_count`, `spam_containment_count`
- Update `specs/api/api-endpoints.md`, `specs/database/database-schema.md`
- Update E2 verifier route list + Alembic head when migrations land
- No PII/secrets/prompts in responses

## Tests

- List API tenant scoping
- Forbidden field rejection
- Adapter metric extension
- E2 observability verifier green

## Out of scope

Dashboard UI
