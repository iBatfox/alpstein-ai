# T-e3.5d — PostgreSQL concurrency validation (rate limits)

**Status:** done  
**Phase:** E3.5 follow-up  
**Completed:** 2026-05-29  
**Audit:** [`docs/audits/e3-5d-postgres-concurrency-validation.md`](../../docs/audits/e3-5d-postgres-concurrency-validation.md)

## Goal

Prove `rate_limit_buckets` atomic enforcement under real PostgreSQL concurrency (`SELECT FOR UPDATE`), not mocks alone.

## Delivered

- `backend/tests/test_e3_5_rate_limit_postgres_concurrency.py` — 4 scenarios, `@pytest.mark.postgres`
- `backend/pytest.ini` — postgres marker registration
- Bug fix: `_get_or_create_bucket` nested savepoint + `IntegrityError` recovery

## Acceptance

- [x] Two-session race test passes against real PostgreSQL (4 scenarios)
- [x] Documented evidence in audit note (command + result)
- [x] Ops rollout note updated: staging enablement allowed after test pass

## Rollout

`ALPSTEIN_AI_RATE_LIMIT_ENABLED` may be enabled in **staging** for soak testing. Production remains off until staging review. Spam flag unchanged.
