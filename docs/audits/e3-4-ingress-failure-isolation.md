# E3.4 — Ingress failure isolation (implementation)

**Branch:** `stabilization/runtime-baseline`  
**Phase:** E3 — Multi-Channel Operational Hardening  
**Status:** **Implemented**  
**Design:** [`e3-4-ingress-failure-isolation-design.md`](e3-4-ingress-failure-isolation-design.md)

---

## Summary

Formalized adapter-scoped ingress failure isolation between **telegram** and **website_chat**. Extended E3.3 adapter APIs with ingress/delivery status split, business `isolation_summary`, and per-adapter `containment_status`. Optional ingress gate (default **off**) returns `503 ADAPTER_INGRESS_CONTAINED` for contained adapter only.

## APIs (extended)

| Method | Path | Change |
|--------|------|--------|
| GET | `/api/v1/observability/adapters` | + `isolation_summary`, ingress fields, containment |
| GET | `/api/v1/observability/adapters/{adapter}` | + peer snapshot, split statuses |
| POST | `/api/v1/webhook/message` | Optional `503 ADAPTER_INGRESS_CONTAINED` when gate enabled |

## Config

| Env | Default |
|-----|---------|
| `ALPSTEIN_AI_INGRESS_CONTAINMENT_ENABLED` | `false` |
| `ALPSTEIN_AI_INGRESS_MONITOR_FAILED_WARNING` | `3` |
| `ALPSTEIN_AI_INGRESS_MONITOR_FAILED_DEGRADED` | `10` |
| `ALPSTEIN_AI_INGRESS_MONITOR_INBOUND_DL_DEGRADED` | `1` |

## Files

- `backend/app/services/ingress_isolation_policy.py`
- `backend/app/services/adapter_monitoring_service.py` (extended)
- `backend/app/services/webhook_message_service.py` (optional gate)
- `backend/app/exceptions.py` (`AdapterIngressContainedError`)
- `backend/app/api/routes/webhook.py`
- `backend/app/schemas/adapter_health.py`
- `backend/app/schemas/adapter_health_mapper.py`
- `backend/app/core/config.py`
- `backend/tests/test_e3_4_ingress_isolation.py`
- `backend/tests/test_e3_4_ingress_containment_gate.py`
- `specs/api/api-endpoints.md`

## Validation

Run full backend pytest + E2 observability verifier after deploy.

## Deployment

- **No migration** — backend restart only
- Do **not** enable `ALPSTEIN_AI_INGRESS_CONTAINMENT_ENABLED` in production without ops review
