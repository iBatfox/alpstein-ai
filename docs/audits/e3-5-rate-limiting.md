# E3.5 — Rate limiting (implementation)

**Branch:** `stabilization/runtime-baseline`  
**Status:** **Accepted — merge allowed; concurrency validation follow-up open**  
**Design:** [`e3-5-rate-limiting-design.md`](e3-5-rate-limiting-design.md)  
**Follow-up:** [`T-e3.5d-postgres-concurrency-validation.md`](../../tasks/todo/T-e3.5d-postgres-concurrency-validation.md)

## Summary

Backend-owned ingress rate limiting for `telegram` and `website_chat` using PostgreSQL atomic counters. Reject-only **429** `RATE_LIMIT_EXCEEDED`; no queues or Redis.

## Deliverables

| Slice | Status | Notes |
|-------|--------|-------|
| E3.5a | Done | Migrations `0017`/`0018`, models, `RateLimitPolicy` |
| E3.5b | Done | `RateLimitService`, webhook wiring post-duplicate, feature flag default off |
| E3.5c | Done | `GET /api/v1/observability/rate-limits`, adapter `rate_limit_violation_count` |

## Flow order (webhook)

```text
validate → resolve business/tenant → flow/customer/conversation → save message
→ trace → if duplicate → return (no rate limit)
→ rate limit check/increment → if exceeded → 429
→ E3.4 optional ingress gate → 503
→ AI orchestration
```

## Configuration

| Env | Default |
|-----|---------|
| `ALPSTEIN_AI_RATE_LIMIT_ENABLED` | `false` |
| `ALPSTEIN_AI_RATE_LIMIT_WINDOW_SECONDS` | `60` |
| `ALPSTEIN_AI_RATE_LIMIT_TENANT_LIMIT` | `1000` |
| `ALPSTEIN_AI_RATE_LIMIT_BUSINESS_LIMIT` | `300` |
| `ALPSTEIN_AI_RATE_LIMIT_ADAPTER_TELEGRAM_LIMIT` | `120` |
| `ALPSTEIN_AI_RATE_LIMIT_ADAPTER_WEBSITE_CHAT_LIMIT` | `120` |
| `ALPSTEIN_AI_RATE_LIMIT_CONVERSATION_LIMIT` | `30` |

## Deployment

1. `alembic upgrade head` (through `0018`)
2. Deploy backend with flag **off**
3. **Rollout gate:** keep `ALPSTEIN_AI_RATE_LIMIT_ENABLED=false` in **all** environments until [`T-e3.5d-postgres-concurrency-validation.md`](../../tasks/todo/T-e3.5d-postgres-concurrency-validation.md) passes (real PostgreSQL two-session race test)
4. After E3.5d green: enable in staging with tuned limits; production only after staging review

## Tests

- `backend/tests/test_e3_5_rate_limit_policy.py` — unit/policy
- `backend/tests/test_e3_5_rate_limiting.py` — mocked wiring/API
- **Gap (E3.5d):** `SELECT FOR UPDATE` concurrency **not** verified against live Postgres yet

## Rollback

Set `ALPSTEIN_AI_RATE_LIMIT_ENABLED=false`. Tables may remain; no runtime dependency when disabled.
