# E3.3 — Adapter monitoring (implementation)

**Branch:** `stabilization/runtime-baseline`  
**Phase:** E3 — Multi-Channel Operational Hardening  
**Status:** **Implemented**  
**Design:** [`e3-3-adapter-monitoring-design.md`](e3-3-adapter-monitoring-design.md)

---

## Summary

Backend-owned adapter health for **`telegram`** and **`website_chat`**, derived at read time from existing observability tables. No new migrations or runtime components.

## APIs

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/observability/adapters` | Webhook token |
| GET | `/api/v1/observability/adapters/{adapter}` | Webhook token |

Required query: `tenant_id`, `business_id`. Optional: `window_hours` (1–168, default 24).

## Status rules (E3.3c)

Precedence: `inactive` → `degraded` → `warning` → `healthy`.

Defaults (env `ALPSTEIN_AI_ADAPTER_MONITOR_*`):

- min sample: 5 traces
- degraded failure rate: 50%
- warning failure rate: 25%
- retry warning: 10
- pending warning: 5
- pending stale (zero delivered): 3

## Files

- `backend/app/services/adapter_health_policy.py`
- `backend/app/services/adapter_monitoring_service.py`
- `backend/app/schemas/adapter_health.py`
- `backend/app/schemas/adapter_health_mapper.py`
- `backend/app/api/routes/observability.py`
- `backend/app/core/config.py`
- `backend/tests/test_e3_3_adapter_monitoring.py`
- `backend/tests/test_e3_3_adapter_observability_api.py`
- `specs/api/api-endpoints.md`
- `scripts/verify/e2_observability_verification.py`

## Validation

- `496` pytest passed (backend/tests/)
- E2 observability verifier: 8/8 PASS (10 observability routes incl. adapters)
- E3.1 / E3.2 continuity tests green

## Deployment

- **No migration** — backend restart only
- Optional env tuning via `ALPSTEIN_AI_ADAPTER_MONITOR_*`

## Operator usage

```bash
curl -s -H "X-Alpstein-Webhook-Token: $TOKEN" \
  "$BASE/api/v1/observability/adapters?tenant_id=$TENANT&business_id=$BUSINESS"
```

Unknown adapter on detail route → `404 NOT_FOUND`.
