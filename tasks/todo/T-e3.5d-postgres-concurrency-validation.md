# T-e3.5d — PostgreSQL concurrency validation (rate limits)

**Status:** todo  
**Phase:** E3.5 follow-up (does **not** block E3.5 merge)  
**Prerequisite:** E3.5a–E3.5c merged; Alembic head `0018` applied

## Goal

Prove `rate_limit_buckets` atomic enforcement under real PostgreSQL concurrency (`SELECT FOR UPDATE`), not mocks alone.

## Scope

Add an integration test (or staging verification harness) that exercises `RateLimitService.consume_ingress_request` against live Postgres with two concurrent DB sessions.

## Required test scenario

| Step | Expected |
|------|----------|
| Setup | Same `tenant_id`, `business_id`, adapter channel, `conversation_id`, same 60s window bucket |
| Limits | Set all scope limits high except one scope under test, **or** set global limits so effective cap is **1** for the exercised path (document chosen scope) |
| Concurrency | Two concurrent sessions call `consume_ingress_request` (or equivalent service entry) for the same scope/window |
| First request | Accepted; bucket incremented |
| Second request | Rejected with `RateLimitExceededError` / `RATE_LIMIT_EXCEEDED` |
| Final bucket | `request_count == 1` (not 2) |
| Violations | Exactly **one** row in `rate_limit_violations` for the rejection |

### Minimum assertions

- No lost update (count must not exceed limit under race).
- Violation row persists (isolated commit path) after webhook-style rollback on the losing session.
- Tenant/business filters on violation query still hold.

## Out of scope

- Redis, queues, load generators beyond two-session race.
- Enabling `ALPSTEIN_AI_RATE_LIMIT_ENABLED` in production.
- n8n workflow changes.

## Implementation notes

- Prefer `pytest` marker e.g. `@pytest.mark.postgres` or existing integration pattern if present; skip when `DATABASE_URL` unavailable.
- May use `asyncio.gather` with two `AsyncSessionLocal()` sessions and explicit transaction boundaries.
- Test file suggestion: `backend/tests/test_e3_5_rate_limit_postgres_concurrency.py`.

## Rollout gate (mandatory documentation)

**Do not set `ALPSTEIN_AI_RATE_LIMIT_ENABLED=true` in staging or production until this task passes.**

Default remains **`false`** in all environments until concurrency validation is green.

## Docs to update on completion

- `docs/audits/e3-5-rate-limiting.md` — mark concurrency validation complete
- `docs/ops/ingress-rate-limit-429.md` — remove or soften pre-validation gate note
- `docs/project-status/next-steps.md` — rollout enablement step

## Tests

- New Postgres concurrency test(s) as above
- Existing unit suite (`test_e3_5_*`) must remain green

## Acceptance

- [ ] Two-session race test passes against real PostgreSQL
- [ ] Documented evidence in task or audit note (command + result)
- [ ] Ops rollout note updated: flag may be enabled in staging **after** test pass
