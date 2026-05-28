# E3.1 — Retry and replay protection (design note)

**Branch:** `stabilization/runtime-baseline`  
**Slices:** E3.1a → E3.1b → E3.1c

## Threat map

| Threat | Mitigation slice |
|--------|------------------|
| Concurrent duplicate webhook (TOCTOU) | E3.1a — `inbound_processing_locks` + message unique constraint |
| In-flight retry marks trace `skipped_duplicate` while AI runs | E3.1a — trace guard on `processing`/`accepted` |
| Delivery PATCH `delivered` → `failed` | E3.1b — terminal transition validator |
| Ops cannot see replay storms | E3.1c — `replay_events` + read API |

## E3.1a — Chosen approach

**Option A (selected):** `inbound_processing_locks` with unique `(business_id, conversation_id, idempotency_key)`.

**Why not advisory locks only:** harder to test without Postgres; no `replay_count` / audit trail until E3.1c.

**Why not trace-only guard:** trace is created per `inbound_message_id`; concurrent race is before trace exists; lock scopes idempotency key before AI.

**Flow:**

1. `save_incoming_customer_message` (existing unique indexes).
2. If `is_duplicate` → duplicate path (trace guard only).
3. Else `acquire_processing_lock` → on conflict, treat as **in-flight replay** (duplicate response, no AI, no outbound).
4. On success path completion/failure → `release_lock(completed|failed)`.
5. `mark_skipped_duplicate` never downgrades `processing`/`accepted` traces.

**Transaction strategy:** `INSERT` lock row with nested transaction + `IntegrityError` → load existing lock; if `processing` and different `owner_correlation_id`, replay conflict. Same owner re-entrant allowed.

**No runtime redesign:** single backend process, no queues; additive table + service calls in existing `WebhookMessageService`.

## E3.1b — Delivery terminal states

Validator in `DeliveryVisibilityService`: `delivered` and `skipped` terminal; illegal transitions no-op (return current row) for n8n stability; record event in E3.1c.

## E3.1c — Replay observability

`replay_events` append-only audit; GET `/api/v1/observability/replays` with tenant/business filters.

## Risks

- Lock row must be released on exception (try/finally in webhook).
- Stale `processing` locks if worker crashes — `expires_at` column for future sweeper (MVP: document; optional TTL check on acquire).
- Website hash idempotency unchanged (documented tradeoff).
