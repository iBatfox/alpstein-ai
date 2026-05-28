# E3.3 — Adapter monitoring (design)

**Branch:** `stabilization/runtime-baseline`  
**Phase:** E3 — Multi-Channel Operational Hardening  
**Status:** **Implemented** — see implementation notes in [`e3-3-adapter-monitoring.md`](e3-3-adapter-monitoring.md)  
**Prerequisites:** E2.5–E2.7 observability, E3.1 replay protection, E3.2 retry/dead-letter

---

## 1. Executive summary

E3.3 adds **adapter-level operational visibility** for MVP channels **Telegram** and **Website Chat**, derived entirely from existing PostgreSQL observability tables. Operators can answer “which adapter is healthy?” via read APIs—no Grafana, Prometheus, queues, or dashboards.

| Slice | Deliverable |
|-------|-------------|
| E3.3a | Adapter health model + `AdapterMonitoringService` (derived metrics) |
| E3.3b | `GET /api/v1/observability/adapters` and `GET /api/v1/observability/adapters/{adapter}` |
| E3.3c | Deterministic status rules (`healthy` / `warning` / `degraded` / `inactive`) |

**Storage decision:** **No new tables in MVP.** Metrics are computed at read time from `message_traces`, `delivery_events`, `retry_attempts`, and `dead_letter_events` within a configurable time window.

---

## 2. Threat map

| # | Threat | Mitigation |
|---|--------|------------|
| 1 | Telegram delivery degradation invisible | Aggregate `delivery_events` by `channel = telegram` |
| 2 | Website delivery degradation invisible | Same for `website_chat` |
| 3 | Retry spikes | Count `retry_attempts` in window, attributed to channel via joins |
| 4 | Dead-letter growth | Count `dead_letter_events` in window (active + newly seen), by channel |
| 5 | Adapter inactivity (no ingress) | `message_traces` count in window; `inactive` if zero |
| 6 | False **healthy** when deliveries stuck `pending` | Treat high `pending` with zero `delivered` as **warning** (PATCH/reporting gap) |
| 7 | Cross-tenant leak | All queries filter `tenant_id` + `business_id`; adapter path validates channel |
| 8 | Low sample → noisy rates | Minimum message threshold before rate-based rules apply |
| 9 | Inbound DL/retry mis-attributed | Join `trace_id` → `message_traces.channel` for inbound scope rows |

---

## 3. Adapter monitoring model

### 3.1 What is an “adapter” (MVP)

An **adapter** is the operational view of a **canonical ingress/delivery channel** the backend already stores:

| Adapter key | Source `channel` values | Notes |
|-------------|-------------------------|--------|
| `telegram` | `telegram` | Customer ingress + outbound delivery |
| `website_chat` | `website_chat` | Website widget ingress + respond path |

**Out of scope for E3.3 metrics:** `test`, `whatsapp`, `instagram` (not in active MVP runtime focus). APIs return only configured adapters; unknown `{adapter}` → `404`.

This is **not** a new runtime component—it is a **read model** over existing rows.

### 3.2 Signal sources (no new storage)

| Metric | Primary source | Attribution |
|--------|----------------|-------------|
| `recent_messages` | `message_traces` | `channel`, `created_at` in window |
| `delivery_success_count` | `delivery_events` | `status = delivered`, `channel` |
| `delivery_failure_count` | `delivery_events` | `status IN (failed, dead_letter)` |
| `delivery_pending_count` | `delivery_events` | `status = pending` (stale reporting signal) |
| `retry_count` | `retry_attempts` | Delivery: join `delivery_events` on `scope_type=delivery` + `scope_id`; Inbound: join `message_traces` on `trace_id` |
| `dead_letter_count` | `dead_letter_events` | Delivery: join `delivery_events`; Inbound: join `message_traces` on `trace_id`; filter `last_seen_at` or `created_at` in window |
| `last_activity_at` | `MAX(message_traces.created_at, delivery_events.updated_at)` per channel | Best-effort “last seen” |

Optional (E3.3c, still derived):

| Metric | Source |
|--------|--------|
| `replay_duplicate_count` | `replay_events` where `source=webhook`, join `trace_id` → channel (informational only) |

### 3.3 Why no new tables

Existing tables already capture channel on ingress (`message_traces.channel`, `delivery_events.channel`) and time series via `created_at` / `updated_at`. Adapter health is a **rolling aggregate**, not a new entity lifecycle. Materialized views or snapshot tables would add ops burden without MVP need. If query cost becomes an issue, add **indexes only** (see §8), not snapshot tables.

### 3.4 Lookback window

All rates and counts use a single lookback window (default **24 hours**):

```text
ALPSTEIN_AI_ADAPTER_MONITOR_WINDOW_HOURS=24
```

Window is **closed interval** `[now - window, now]` in UTC. No per-tenant tuning in MVP.

---

## 4. Health calculation strategy (E3.3a)

### 4.1 Derived rates

Computed only when `recent_messages >= MIN_SAMPLE` (default **5**):

```text
delivery_attempted = delivery_success_count + delivery_failure_count
delivery_failure_rate = delivery_failure_count / delivery_attempted   (if attempted > 0)
```

`pending` deliveries are **excluded** from success rate (they are not success or failure—they indicate reporting lag).

### 4.2 Status definitions (E3.3c) — deterministic precedence

Evaluate in order; **first match wins**:

| Status | Conditions (all tenant+business scoped, per adapter) |
|--------|-----------------------------------------------------|
| **inactive** | `recent_messages == 0` in window |
| **degraded** | `dead_letter_count > 0` in window **OR** `delivery_failure_rate >= DEGRADED_RATE` (with min sample) **OR** `delivery_pending_count >= PENDING_STALE_MIN` AND `delivery_success_count == 0` |
| **warning** | Not inactive/degraded AND (`retry_count >= RETRY_WARNING` **OR** `delivery_failure_rate >= WARNING_RATE` **OR** `delivery_pending_count >= PENDING_WARNING`) |
| **healthy** | Default when not inactive, degraded, or warning |

Default thresholds (env-overridable, platform constants):

| Variable | Default | Meaning |
|----------|---------|---------|
| `ADAPTER_MONITOR_WINDOW_HOURS` | `24` | Lookback |
| `ADAPTER_MONITOR_MIN_SAMPLE` | `5` | Min traces before rate rules |
| `ADAPTER_MONITOR_DEGRADED_FAILURE_RATE` | `0.50` | 50% delivery failures |
| `ADAPTER_MONITOR_WARNING_FAILURE_RATE` | `0.25` | 25% delivery failures |
| `ADAPTER_MONITOR_RETRY_WARNING` | `10` | Retry attempts in window |
| `ADAPTER_MONITOR_PENDING_WARNING` | `5` | Many pending, some success |
| `ADAPTER_MONITOR_PENDING_STALE_MIN` | `3` | Pending with zero delivered → degraded |

**No AI scoring.** Pure integer/float comparisons.

### 4.3 Status metadata (API)

Include non-secret `status_reasons: string[]` e.g. `["dead_letter_present", "high_failure_rate"]` for ops clarity—stable machine-readable codes only.

---

## 5. API design (E3.3b)

Auth: same as other observability routes — `X-Alpstein-Webhook-Token` + required `tenant_id`, `business_id` query params.

### 5.1 `GET /api/v1/observability/adapters`

**Purpose:** List adapter health for a business.

**Query:**

```text
tenant_id (required)
business_id (required)
window_hours (optional, capped 1–168, default from env)
```

**Response:**

```json
{
  "success": true,
  "data": {
    "window_hours": 24,
    "items": [
      {
        "adapter": "telegram",
        "status": "healthy",
        "status_reasons": [],
        "recent_messages": 42,
        "delivery_success_count": 40,
        "delivery_failure_count": 1,
        "delivery_pending_count": 1,
        "retry_count": 2,
        "dead_letter_count": 0,
        "delivery_failure_rate": 0.024,
        "last_activity_at": "2026-05-28T14:00:00Z"
      },
      {
        "adapter": "website_chat",
        "status": "warning",
        "status_reasons": ["elevated_pending_deliveries"],
        "recent_messages": 10,
        "delivery_success_count": 8,
        "delivery_failure_count": 0,
        "delivery_pending_count": 2,
        "retry_count": 0,
        "dead_letter_count": 0,
        "delivery_failure_rate": null,
        "last_activity_at": "2026-05-28T13:55:00Z"
      }
    ]
  }
}
```

`delivery_failure_rate` is `null` when sample too low (same as `MIN_SAMPLE` rule).

### 5.2 `GET /api/v1/observability/adapters/{adapter}`

**Purpose:** Detail for one adapter (same metrics + `evaluated_at` timestamp).

**Path:** `adapter` ∈ `telegram` | `website_chat` (else `404`).

**Response:** Single `data` object (same fields as list item) plus optional breakdown:

```json
{
  "breakdown": {
    "delivery_by_status": {
      "pending": 1,
      "delivered": 40,
      "failed": 1,
      "dead_letter": 0,
      "retrying": 0,
      "skipped": 0
    }
  }
}
```

No prompts, raw payloads, secrets, or customer PII.

### 5.3 Error envelope

- Invalid UUID / missing params → `VALIDATION_ERROR` (400)
- Unknown adapter → `NOT_FOUND` (404)
- Standard `{ success: false, error: { code, message } }`

---

## 6. Transaction boundaries

- **Read-only:** one `AsyncSession` per request; multiple aggregate queries (or one SQL with subqueries per channel).
- **No writes** to business tables.
- **Consistency:** point-in-time snapshot; counts may drift slightly between queries—acceptable for ops MVP.
- **Isolation:** aggregates only; no cross-tenant joins.

Suggested query plan (implementation detail):

1. Aggregate `message_traces` by `channel` (filtered).
2. Aggregate `delivery_events` by `channel` + `status` (filtered).
3. Aggregate `retry_attempts` with joins for channel attribution (filtered).
4. Aggregate `dead_letter_events` with joins (filtered).
5. Merge in Python per adapter key; compute status.

---

## 7. Observability ownership

| Layer | Role |
|-------|------|
| **n8n** | Transport; continues PATCH delivery outcomes; no adapter API calls required |
| **Backend `AdapterMonitoringService`** | Derives health; owns thresholds |
| **API routes** | Thin; delegate to service |
| **Existing list APIs** | Unchanged; adapters API is additive ops surface |

---

## 8. Performance and optional indexes (implementation note)

Existing indexes likely sufficient for MVP demo volume:

- `delivery_events`: `(business_id, channel, status)`
- `message_traces`: `(business_id, …)`, `status`

**Optional additive migration (only if profiling requires):**

```text
message_traces (business_id, channel, created_at)
```

Defer unless slow; document in implementation PR if added as `0017_*`.

---

## 9. Implementation slices (after approval)

### E3.3a — Adapter health model

- `app/services/adapter_monitoring_service.py`
- `app/services/adapter_health_policy.py` (thresholds + status evaluation)
- Unit tests for status precedence with fixture counts

### E3.3b — API

- `app/schemas/adapter_health.py` + mapper
- Routes on `observability` router
- API tests (tenant isolation, 404 unknown adapter)
- Update `specs/api/api-endpoints.md`

### E3.3c — Degradation detection

- Wire policy into service (same PR as 3b)
- Tests: deterministic cases for healthy/warning/degraded/inactive
- Update `scripts/verify/e2_observability_verification.py` route list

---

## 10. Required tests (acceptance)

1. List adapters returns `telegram` + `website_chat` for scoped tenant/business.
2. Cross-business request does not include other business rows.
3. Retry/dead-letter counts match seeded fixtures.
4. Status rules: inactive (no traces), degraded (DL present), warning (high pending), healthy baseline.
5. E3.1 / E3.2 / E2.7 suites remain green.
6. No forbidden fields in JSON responses.

---

## 11. Risks and rollback

| Risk | Mitigation |
|------|------------|
| Heavy aggregates on large DB | Window cap 168h; optional index; limit to 2 adapters |
| Misleading healthy with stuck pending | `pending` stale rules → warning/degraded |
| Inbound retries skew channel metrics | Document joins; delivery-weighted ops interpretation |
| Threshold tuning wrong for prod | Env vars; document defaults in ops audit |

**Rollback:** Remove routes + service; no migration required if no index shipped.

---

## 12. Rollout (operator)

1. Deploy backend (no migration if indexes deferred).
2. `GET /api/v1/observability/adapters?tenant_id=…&business_id=…` with webhook token.
3. Compare with existing `/deliveries`, `/dead-letter`, `/retries` drill-down.

---

## 13. Approval checklist

- [x] No new tables for MVP agreed
- [x] Adapter set (`telegram`, `website_chat`) agreed
- [x] Status rules and thresholds acceptable
- [x] API shape acceptable for future dashboard (not in scope)
- [x] n8n unchanged

**Implemented:** see [`e3-3-adapter-monitoring.md`](e3-3-adapter-monitoring.md).
