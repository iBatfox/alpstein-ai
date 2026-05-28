# E3.4 — Ingress failure isolation (design)

**Branch:** `stabilization/runtime-baseline`  
**Phase:** E3 — Multi-Channel Operational Hardening  
**Status:** **Implemented** — see [`e3-4-ingress-failure-isolation.md`](e3-4-ingress-failure-isolation.md)  
**Prerequisites:** E3.1 replay protection, E3.2 retry/dead-letter, E3.3 adapter monitoring

---

## 1. Executive summary

E3.4 **formalizes and verifies** deterministic ingress failure isolation between **`telegram`** and **`website_chat`**. Failures in one adapter must not alter processing state, retry/dead-letter scope, or health evaluation of the peer adapter.

| Slice | Deliverable |
|-------|-------------|
| E3.4a | Failure isolation model — shared vs isolated components, propagation rules |
| E3.4b | Ingress observability — adapter-scoped ingress metrics + business isolation summary API |
| E3.4c | Failure containment rules — deterministic `containment_status` + optional ingress gate (env, default off) |

**Storage decision:** **No new tables for MVP.** Extend E3.3 derived read model with ingress-specific aggregates from existing tables. Optional env-gated ingress rejection requires no DDL.

**Non-goals:** circuit breakers with auto-recovery, queues, new containers, n8n workflow changes, cross-adapter bulkheads in PostgreSQL, dashboards.

---

## 2. Threat map

| # | Threat | Current state | E3.4 mitigation |
|---|--------|---------------|-----------------|
| 1 | Telegram ingress outage | Per-request failure; trace `failed` | Ingress metrics + contained status; peer unaffected |
| 2 | Website ingress outage | Same | Same |
| 3 | Retry storm (one adapter) | E3.1 lock + E3.2 inbound DL scoped by `channel` on lock/trace | Ingress retry counts per adapter; isolation summary |
| 4 | Dead-letter spike (one adapter) | DL rows scoped; channel via join | `inbound_dead_letter_count` / `delivery_dead_letter_count` split |
| 5 | Malformed payloads (adapter-specific) | HTTP 400 validation; no global state | Do not count as adapter degradation; document boundary |
| 6 | Shared backend resource contention | Single process, DB pool, OpenAI gateway shared | Document as **physical** risk; optional ingress gate reduces AI load on degraded adapter |
| 7 | False degradation propagation | E3.3 evaluates adapters independently | Explicit `isolation_status: intact` when only one adapter degraded |
| 8 | Delivery failure mistaken for ingress failure | E3.3 combines both in adapter `status` | Split `ingress_status` vs `delivery_status` in E3.4b |
| 9 | Cross-tenant leak | Existing tenant+business filters | Unchanged; mandatory on all new queries |

---

## 3. Failure isolation model (E3.4a)

### 3.1 Adapter boundary (MVP)

Same as E3.3:

| Adapter | `channel` value | Ingress | Outbound delivery |
|---------|-----------------|---------|-------------------|
| `telegram` | `telegram` | n8n → webhook | n8n PATCH delivery |
| `website_chat` | `website_chat` | n8n → webhook | n8n PATCH delivery |

An **ingress failure** is a backend-owned signal in the **inbound half** of the adapter lifecycle (webhook accept → trace/lock/retry/DL), not n8n transport errors before normalization.

### 3.2 What is isolated (must remain local)

| Component | Isolation mechanism | Propagates to peer? |
|-----------|---------------------|---------------------|
| Webhook request handling | Stateless per request; `channel` from normalized payload | **No** — peer requests independent |
| `message_traces` | `channel` column; scoped queries | **No** |
| `inbound_processing_locks` | Unique `(business_id, conversation_id, idempotency_key)`; `channel` on row | **No** — different conversations/channels |
| Inbound `retry_attempts` | `scope_type=inbound`; channel via `trace_id` → `message_traces.channel` | **No** |
| Inbound `dead_letter_events` | `scope_type=inbound`; channel via trace join | **No** |
| Delivery `retry_attempts` / DL | Channel via `delivery_events.channel` | **No** |
| Adapter health (E3.3) | Per-adapter aggregates | **No** — by design |
| Validation errors (malformed JSON) | HTTP 400; no trace row | **No** — not adapter state |

**Golden rule:** No global “business degraded” flag, shared lock, or cross-channel counter may gate peer ingress in MVP.

### 3.3 What is shared (failures can physically contend)

| Resource | Risk | E3.4 stance |
|----------|------|-------------|
| FastAPI worker / event loop | Slow requests block threads | Document; optional ingress gate on degraded adapter only |
| PostgreSQL connection pool | Many writes from one adapter | Document; no new pool per adapter in MVP |
| OpenAI via AI Gateway | Shared quota/latency | Optional ingress gate skips new AI for **contained** adapter only |
| Same `tenant_id` / `business_id` | Logical grouping only | Not a failure propagation path |
| n8n instance | Shared orchestration | Out of backend scope; n8n unchanged |

**Logical isolation is already present.** E3.4 adds **visibility** and **optional containment** for shared-resource pressure—not a runtime redesign.

### 3.4 Failure propagation matrix

| Failure type | Local adapter effect | Peer adapter effect | Spread signal |
|--------------|------------------------|---------------------|---------------|
| Telegram retry storm | Inbound DL, elevated `retry_count` | None on peer metrics | `isolation_status: intact` |
| Website delivery failures | Delivery DL, high failure rate | None on peer ingress | `isolation_status: intact` |
| Trace `failed` (AI error) on Telegram | `ingress_status: degraded` | Peer unchanged | intact if peer healthy |
| Malformed Telegram payload (400) | Single request rejected | None | Not counted in adapter metrics |
| DB unavailable | Both fail | **Physical** shared outage | `isolation_status: at_risk` (both adapters fail) |
| OpenAI timeout storm (both channels active) | Both may show `ingress_status: warning` | Correlated | `spread_risk: true` if both ingress degraded same window |

---

## 4. Ingress observability strategy (E3.4b)

### 4.1 Extend adapter metrics (no new tables)

Add **ingress dimension** to existing adapter read model:

| Field | Source | Window |
|-------|--------|--------|
| `ingress_recent_messages` | `message_traces` count by `channel` | Same as E3.3 |
| `ingress_failed_count` | `message_traces` where `status = failed` | Same |
| `ingress_retry_count` | `retry_attempts` where `scope_type=inbound`, join trace → channel | Same |
| `ingress_dead_letter_count` | `dead_letter_events` where `scope_type=inbound`, join trace → channel | Same |
| `ingress_replay_count` | `replay_events` where `source=webhook`, join trace → channel (informational) | Same |

Keep E3.3 delivery fields (`delivery_success_count`, etc.) unchanged for backward compatibility.

### 4.2 Split health dimensions

Evaluate **independently**, then expose:

| Field | Based on |
|-------|----------|
| `ingress_status` | Ingress metrics + ingress-specific thresholds |
| `delivery_status` | Existing E3.3 delivery metrics + delivery thresholds |
| `status` | **Combined** = worse of ingress and delivery (precedence: inactive → degraded → warning → healthy) |

Ingress thresholds (defaults, env-overridable):

| Variable | Default | Rule |
|----------|---------|------|
| `INGRESS_MONITOR_FAILED_WARNING` | 3 | `ingress_failed_count >= N` → warning |
| `INGRESS_MONITOR_FAILED_DEGRADED` | 10 | → degraded |
| `INGRESS_MONITOR_INBOUND_RETRY_WARNING` | 10 | Same as E3.3 retry warning for inbound-only count |
| `INGRESS_MONITOR_INBOUND_DL_DEGRADED` | 1 | Any inbound DL in window → degraded |

Delivery thresholds: reuse E3.3 `adapter_monitor_*` delivery rules.

### 4.3 Business isolation summary

Extend **`GET /api/v1/observability/adapters`** response with top-level `isolation_summary`:

```json
{
  "success": true,
  "data": {
    "window_hours": 24,
    "isolation_summary": {
      "isolation_status": "intact",
      "spread_risk": false,
      "degraded_adapters": ["telegram"],
      "healthy_adapters": ["website_chat"],
      "inactive_adapters": []
    },
    "items": [ "... per adapter with ingress_* and containment_* ..." ]
  }
}
```

**`isolation_status` values:**

| Value | Meaning |
|-------|---------|
| `intact` | At most one adapter `degraded`, OR multiple degraded but `spread_risk=false` |
| `at_risk` | Two or more adapters `degraded` or `warning` with correlated ingress failure pattern (see §5.3) |
| `unknown` | Insufficient data (both inactive) |

**`spread_risk`:** `true` when ≥2 adapters have `ingress_status` in (`warning`, `degraded`) **and** both have `ingress_failed_count > 0` in window — suggests shared backend/AI pressure.

### 4.4 Detail route

**`GET /api/v1/observability/adapters/{adapter}`** adds:

- All ingress fields above
- `ingress_status`, `delivery_status`, `containment_status`
- `peer_adapter` snapshot (status + containment only — no PII)

No new route required unless approval prefers `GET /observability/ingress-isolation`; **recommend extending existing adapter APIs** to avoid proliferation.

---

## 5. Failure containment rules (E3.4c)

### 5.1 Containment status (per adapter)

Deterministic, derived from adapter + peer state:

| `containment_status` | Conditions |
|----------------------|------------|
| `normal` | Adapter `status` is `healthy` or `inactive` |
| `contained` | This adapter `degraded` or `warning`, peer `healthy` or `inactive` — failure localized |
| `peer_at_risk` | This adapter healthy, peer `degraded` — ops visibility only |
| `shared_at_risk` | Business `isolation_summary.spread_risk = true` |

**No automatic recovery.** Status recalculated on each read from DB aggregates.

### 5.2 Processing guarantees (always on)

These are **invariants** verified by tests, not new runtime logic:

1. Telegram inbound DL / lock / trace rows do not mutate website_chat rows.
2. Website retry storm increments website-scoped counters only.
3. E3.1 replay protection remains per `(conversation_id, idempotency_key)`.
4. Peer adapter E3.3 `status` unchanged when only one channel injects failures.

### 5.3 Optional ingress gate (env, default **off**)

When `ALPSTEIN_AI_INGRESS_CONTAINMENT_ENABLED=true`:

- Before orchestration in `WebhookMessageService.process_incoming_message`, evaluate **cached read** of adapter `ingress_status` for `request.channel` (same aggregates, short TTL in-process cache optional — default: query-less reuse of policy fn on recent metrics is too heavy; **simple approach:** evaluate containment from same service call used by observability, or skip gate if too costly and use precomputed degraded list — **MVP recommendation:** call `IngressIsolationService.should_accept_ingress(channel)` which runs lightweight count query OR reuses threshold check on last N minutes only for gate).

**Simpler MVP gate rule (recommended):**

Reject **new** ingress (HTTP **503**, `error.code=ADAPTER_INGRESS_CONTAINED`) only when:

- Env flag enabled, **and**
- Adapter has active inbound `dead_letter_events` in last 24h (`ingress_dead_letter_count > 0`), **and**
- `containment_status = contained`

Peer adapter ingress **never** rejected due to other adapter state.

**Default: flag off** — visibility-only MVP; gate is ops opt-in to protect shared AI/DB under inbound DL storm.

Malformed payload → still **400** (not 503).

### 5.4 What containment does **not** do

- Does not pause n8n workflows
- Does not delete or migrate DL rows
- Does not auto-retry or auto-heal
- Does not block delivery PATCH for contained adapter
- Does not affect other businesses/tenants

---

## 6. Implementation slices (after approval)

### E3.4a — Failure isolation model

- `backend/app/services/ingress_isolation_policy.py` — shared/isolated matrix, containment + spread evaluation
- Unit tests for propagation/containment rules (pure functions)

### E3.4b — Ingress observability

- Extend `AdapterMonitoringService` with ingress aggregates + `isolation_summary`
- Extend Pydantic schemas + `GET /observability/adapters` (+ detail)
- Update `specs/api/api-endpoints.md`

### E3.4c — Failure containment

- Wire containment into adapter responses
- Continuity tests: simulate telegram failures, assert website metrics/status unchanged
- Optional ingress gate in `WebhookMessageService` behind env flag
- Update E2 verifier route field checks if response shape extended (same routes)

---

## 7. API contract changes (summary)

### List — additive fields

Per item:

```text
ingress_status, delivery_status, containment_status
ingress_failed_count, ingress_retry_count, ingress_dead_letter_count
ingress_status_reasons[], delivery_status_reasons[]  (optional split)
```

Top-level:

```text
isolation_summary { isolation_status, spread_risk, degraded_adapters[], healthy_adapters[], inactive_adapters[] }
```

### Errors (only if gate enabled)

```json
{
  "success": false,
  "error": {
    "code": "ADAPTER_INGRESS_CONTAINED",
    "message": "Ingress temporarily not accepted for this adapter"
  }
}
```

---

## 8. Transaction boundaries

- **Observability reads:** same as E3.3 — read-only, multiple aggregates, tenant+business scoped.
- **Ingress gate (optional):** read-only check before write path; no cross-adapter locks.
- **No new writes** for isolation visibility.

---

## 9. Observability ownership

| Layer | Role |
|-------|------|
| **n8n** | Unchanged; per-channel workflows |
| **WebhookMessageService** | Optional gate only (E3.4c, flag off default) |
| **AdapterMonitoringService** | Extended with ingress aggregates + isolation summary |
| **IngressIsolationPolicy** | Pure containment/spread rules |

---

## 10. Required tests (acceptance)

1. Telegram ingress failures do not change website_chat adapter metrics in same business.
2. `isolation_summary.isolation_status = intact` when only telegram degraded.
3. `spread_risk = true` only when both adapters show ingress failures in window.
4. Ingress vs delivery status split correct on fixture data.
5. E3.1 / E3.2 / E3.3 / E2.7 suites remain green.
6. If gate enabled: telegram 503 does not block website webhook; flag off preserves current behavior.

---

## 11. Risks and rollback

| Risk | Mitigation |
|------|------------|
| Combined `status` semantics change | Document as max(ingress, delivery); add split fields |
| Gate rejects legitimate traffic | Default off; narrow rule (inbound DL present) |
| Query load | Reuse E3.3 query batch; defer indexes |
| False `spread_risk` | Conservative rule; ops interprets with peer metrics |

**Rollback:**

- Visibility-only: remove extended fields + policy module; no migration.
- With gate: set `ALPSTEIN_AI_INGRESS_CONTAINMENT_ENABLED=false` or revert webhook check.

---

## 12. Rollout (operator)

1. Deploy backend (no migration if visibility-only).
2. `GET /api/v1/observability/adapters?tenant_id=…&business_id=…` — inspect `isolation_summary` and per-adapter `containment_status`.
3. Enable ingress gate only after ops review.

---

## 13. Approval checklist

- [x] No new tables for MVP agreed
- [x] Extend E3.3 APIs (not new route) agreed
- [x] Ingress vs delivery status split acceptable
- [x] `isolation_summary` / `containment_status` semantics acceptable
- [x] Optional ingress gate (default **off**) acceptable
- [x] n8n unchanged

**Implemented:** see [`e3-4-ingress-failure-isolation.md`](e3-4-ingress-failure-isolation.md).
