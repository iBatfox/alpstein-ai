# Message trace lifecycle (E2.4 — implemented)

**Status:** implemented in backend (`message_traces` table, Alembic `0011`)  
**Spec reference:** [`specs/observability/message-trace-lifecycle.md`](../../specs/observability/message-trace-lifecycle.md)

---

## Purpose

One durable PostgreSQL row per **inbound customer turn** (keyed by `inbound_message_id`). Traces describe what happened; they do not control orchestration.

Langfuse and `prompt_runs` remain optional/supplementary. Internal traces work when Langfuse is disabled.

---

## Schema (summary)

| Column | Role |
|--------|------|
| `id` | Trace PK (`message_trace_id` in APIs/docs) |
| `tenant_id`, `business_id`, `flow_id`, `conversation_id` | Scope |
| `inbound_message_id` | **UNIQUE** — one trace per inbound message |
| `outbound_message_id` | AI/outbound message when saved |
| `channel`, `status` | Channel + lifecycle status |
| `external_trace_id` | Correlation / external observability id (e.g. `correlation_id`) |
| `langfuse_trace_id` | Optional Langfuse trace id when tracing is active |
| `flow_key`, `external_conversation_id`, `external_message_id`, `idempotency_key` | Ingress context |
| `error_type`, `error_message` | Failure metadata (truncated) |
| `metadata` | JSONB: `correlation_id`, `n8n_execution_id`, `prompt_run_id`, … |

---

## Status values

| Status | Meaning |
|--------|---------|
| `accepted` | Trace row created for new inbound |
| `processing` | Lead/AI path started |
| `completed` | Processing finished (outbound linked when applicable) |
| `skipped_duplicate` | Inbound dedup retry (E2.3); no second AI/lead |
| `failed` | Unhandled exception during processing |

**E3.1a:** Active traces in `accepted` / `processing` / `completed` are **not** downgraded to `skipped_duplicate` on duplicate or in-flight replay.

---

## Webhook flow

```text
save inbound message
  → record_inbound_turn (create or skip_duplicate)
  → if duplicate: return (no mark_processing / AI); replay_events.duplicate_retry
  → acquire inbound_processing_lock (E3.1a)
  → if lock conflict: in-flight replay (is_duplicate, no AI); replay_events.replay_ignored
  → if lock replay_count >= max: dead_letter_events.inbound_exhausted (E3.2)
  → mark_processing
  → lead + AI
  → release lock (completed|failed)
  → mark_completed (outbound + observability ids)
  → on exception: mark_failed (re-raise)
```

---

## Ops queries

```sql
SELECT * FROM message_traces
WHERE inbound_message_id = '…';

SELECT * FROM message_traces
WHERE business_id = '…' AND status = 'failed'
ORDER BY created_at DESC
LIMIT 20;
```

---

## Read APIs (E2.5)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/observability/traces/{trace_id}` | Single trace by id |
| `GET /api/v1/observability/traces?inbound_message_id=` | Lookup by inbound message |
| `GET /api/v1/observability/traces?external_message_id=` | Lookup by channel external id |
| `GET /api/v1/observability/conversations/{id}/traces` | List traces for conversation |

Auth: `X-Alpstein-Webhook-Token` (same as webhook). Required query: `tenant_id`, `business_id`.

Webhook `data.trace`: `{ trace_id, correlation_id, processing_status }` when trace row exists.

---

## Delivery visibility (E2.6)

**Table:** `delivery_events` (Alembic `0012`) — one row per `outbound_message_id` (unique).

| Status | Meaning |
|--------|---------|
| `pending` | Outbound AI message persisted; channel send not yet confirmed |
| `delivered` | n8n reported successful provider delivery |
| `failed` | n8n reported send failure (safe `error_type` / `error_message`) |
| `skipped` | No channel send expected |
| `retrying` | Retry in progress (optional; `retry_count` incremented) |

**Backend:** creates `pending` after outbound message save on non-duplicate webhook path. **n8n** performs Telegram / Website send and reports outcome via API (observability does not control delivery).

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/observability/deliveries/{delivery_id}` | Single delivery row |
| `GET /api/v1/observability/conversations/{id}/deliveries` | List deliveries for conversation |
| `PATCH /api/v1/observability/deliveries/{delivery_id}` | Report `delivered` / `failed` / `skipped` / `retrying` |

Auth: `X-Alpstein-Webhook-Token`. Required query: `tenant_id`, `business_id`.

Webhook `data.delivery` (when outbound saved): `{ delivery_id, delivery_status, outbound_message_id }`.

---

## E2.7 verification (continuity)

Automated checks: `backend/tests/test_e2_observability_continuity.py`, harness `scripts/verify/e2_observability_verification.py`.

Audit record: [`docs/audits/e2-observability-verification.md`](../audits/e2-observability-verification.md).

Verified in code:

- inbound → trace → outbound → `delivery_events.pending` share `outbound_message_id` and `trace_id`
- duplicate inbound: no new outbound/delivery; trace id returned for ops lookup
- observability GET APIs scoped by `tenant_id` + `business_id`
- Langfuse `langfuse_trace_id` optional on trace completion

---

## Out of scope (future)

- Latency columns (`backend_total_latency_ms`, …)
- Dedicated `correlation_id` column on `message_traces` (stored in `metadata` + `external_trace_id`)
