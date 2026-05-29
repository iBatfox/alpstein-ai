# E3.5d — PostgreSQL concurrency validation (rate limits)

**Branch:** `stabilization/runtime-baseline`  
**Status:** **COMPLETE** (2026-05-29)  
**Parent:** [`e3-5-rate-limiting.md`](e3-5-rate-limiting.md)

---

## Goal

Prove `RateLimitService` enforces limits correctly when two real PostgreSQL sessions race on the same `rate_limit_buckets` row via `SELECT ... FOR UPDATE`.

---

## Test design

**File:** `backend/tests/test_e3_5_rate_limit_postgres_concurrency.py`  
**Marker:** `@pytest.mark.postgres` (skipped without `ALPSTEIN_AI_DATABASE_URL`)

| Component | Approach |
|-----------|----------|
| Database | Live PostgreSQL + `alembic upgrade head` (session autouse) |
| Sessions | Two `AsyncSession` instances, each `async with session.begin()` |
| Synchronization | `asyncio.Barrier(2)` before `consume_ingress_request` |
| Service | Real `RateLimitService` — no mocked `execute` |
| Violation commit | Test patches `AsyncSessionLocal` to test engine (isolated violation path) |

### Transaction flow (scenario 1)

```text
Session A                          Session B
─────────                          ─────────
BEGIN                              BEGIN
barrier.wait()                     barrier.wait()
FOR UPDATE buckets (4 scopes)      FOR UPDATE buckets (blocks on A's locks)
count=0, not exceeded              …
increment → count=1                waits…
COMMIT                             acquires locks, count=1, exceeded
                                   _record_violation (isolated commit)
                                   ROLLBACK main txn
```

---

## Scenarios (all passed)

| # | Setup | Expected | Result |
|---|--------|----------|--------|
| 1 | `conversation_limit=1`, same conversation, 2 concurrent | 1 accept, 1 `RATE_LIMIT_EXCEEDED`, bucket=1, violations=1 | **PASS** |
| 2 | `conversation_limit=2`, same conversation, 2 concurrent | both accept, bucket=2, violations=0 | **PASS** |
| 3 | `conversation_limit=1`, different conversations | both accept, independent buckets | **PASS** |
| 4 | `business_limit=1`, telegram + website_chat | 1 accept, 1 reject @ business scope, bucket=1 | **PASS** |

---

## Commands run

```bash
cd backend
ALPSTEIN_AI_DATABASE_URL='postgresql+asyncpg://alpstein:***@127.0.0.1:15433/alpstein_ai' \
  .venv/bin/python -m pytest tests/test_e3_5_rate_limit_postgres_concurrency.py -v

.venv/bin/python -m pytest tests/ -q
# 547 passed, 4 skipped (postgres tests skip without URL)
```

---

## Bug found and fixed

**Issue:** Concurrent bucket creation when no row exists — `FOR UPDATE` on empty set does not serialize inserts; second transaction hit `UniqueViolationError` on `rate_limit_buckets_scope_window_unique`.

**Fix:** `RateLimitService._get_or_create_bucket` — insert inside `begin_nested()` savepoint; on `IntegrityError`, re-run `SELECT ... FOR UPDATE` and return existing row.

**File:** `backend/app/services/rate_limit_service.py`

---

## Rollout recommendation

| Flag | Recommendation |
|------|----------------|
| `ALPSTEIN_AI_RATE_LIMIT_ENABLED` | May enable in **staging** for soak testing with tuned limits |
| Production | After staging validation only; keep default `false` until ops sign-off |
| `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED` | Unchanged — still gated on E3.6 staging validation |

---

## What was not tested

- Load beyond two-session races
- Multi-instance backend horizontal scale (same DB assumption)
- n8n workflow backoff behavior under live 429
