# E3.5 — Rate limiting (design)

**Branch:** `stabilization/runtime-baseline`  
**Phase:** E3 — Multi-Channel Operational Hardening  
**Status:** **Design only — awaiting approval before implementation**  
**Prerequisites:** E3.1 replay protection, E3.4 ingress failure isolation

---

## 1. Executive summary

E3.5 adds **backend-owned, deterministic ingress rate limiting** for MVP adapters **`telegram`** and **`website_chat`**, scoped at **tenant**, **business**, **adapter**, and **conversation** levels. Enforcement is synchronous (accept or reject)—no Redis, queues, workers, or delayed processing.

| Slice | Deliverable |
|-------|-------------|
| E3.5a | Rate limiting model — scopes, windows, limits, burst semantics |
| E3.5b | Enforcement — pre-orchestration checks + atomic counters; `429 RATE_LIMIT_EXCEEDED` |
| E3.5c | Observability — violation audit + list API; optional adapter metric extension |

**Storage decision:** **Two additive PostgreSQL tables** — justified because existing tables cannot enforce limits **before** accepting a new request atomically under burst load (see §3.3). No Redis.

**Rollout:** Feature flag `ALPSTEIN_AI_RATE_LIMIT_ENABLED` default **`false`** (same pattern as E3.4 ingress gate).

**Non-goals:** anti-spam/content moderation, n8n rate nodes, token-bucket smoothing, per-IP limits, billing quotas, auto-ban, delayed/queued requests.

---

## 2. Threat map

| # | Threat | Current gap | E3.5 mitigation |
|---|--------|-------------|-----------------|
| 1 | Telegram provider retry storm | E3.1 idempotency stops duplicate AI; no volume cap | Adapter + conversation limits; duplicates exempt from increment |
| 2 | Website retry storm | Same | Same |
| 3 | Traffic spike (one business) | Unbounded webhook accepts | Business + adapter scoped limits |
| 4 | Burst at window boundary | N/A | Fixed-window limits; document burst shape; env tunable |
| 5 | Cross-adapter impact | E3.4 isolates failure state | Adapter limits independent; business limit is intentional shared cap only |
| 6 | Shared backend exhaustion (DB/OpenAI) | Physical contention | Tenant/business caps reduce load; reject before AI orchestration |
| 7 | Misconfigured integration loop | Unbounded ingress | Conversation limit catches tight loops |
| 8 | Intentional abuse | No volume guard | Multi-scope limits before expensive path |
| 9 | Rate limit false positives on duplicates | N/A | Skip increment/count for idempotent duplicate responses |
| 10 | Cross-tenant leak | N/A | All buckets/violations filter `tenant_id` + `business_id` |

---

## 3. Rate limiting model (E3.5a)

### 3.1 What is rate-limited

**Ingress only:** `POST /api/v1/webhook/message` normalized requests that would proceed to **new** processing (not idempotent duplicate short-circuit).

**Not rate-limited in E3.5:**

- Observability GET routes (already token-gated)
- Delivery PATCH routes (separate transport feedback path; defer to follow-up if needed)
- Validation errors (`400`) — rejected before scope resolution where possible; do not increment counters on malformed payloads

### 3.2 Scope hierarchy

Evaluation order (first exceeded limit wins; all scopes checked deterministically):

| Priority | Scope | `scope_key` | Purpose |
|----------|-------|-------------|---------|
| 1 | **tenant** | `{tenant_id}` | Platform safety net per client |
| 2 | **business** | `{business_id}` | Protect one business from overload |
| 3 | **adapter** | `{business_id}:{channel}` | Isolate telegram vs website_chat volume |
| 4 | **conversation** | `{conversation_id}` | Stop tight loops / widget spam |

**Cross-adapter rule:** Adapter scope uses `channel` (`telegram` | `website_chat`). Exceeding telegram limit **must not** increment or block website_chat buckets.

**Business scope:** Shared across adapters by design (total ingress cap). Document for ops.

### 3.3 Why existing tables are insufficient

| Source | Can observe volume? | Can enforce pre-accept? | Burst-safe? |
|--------|---------------------|-------------------------|-------------|
| `message_traces` | After trace created | No — race under concurrent requests | No |
| `inbound_processing_locks` | Per idempotency key | No — created mid-flow | No |
| `replay_events` | Retries only | No | No |

Concurrent webhook requests can pass a `COUNT(*)` check before any row exists. **Atomic increment** requires a dedicated counter row per window bucket.

### 3.4 Window model — fixed window (MVP)

**Algorithm:** Fixed window bucket keyed by `window_start = floor(now / window_seconds) * window_seconds`.

| Property | MVP choice |
|----------|------------|
| Window size | Default **60 seconds** per scope (env-overridable per scope) |
| Burst handling | Allow up to `limit` requests per window; no sub-second smoothing |
| Reset | Automatic on next window bucket |
| Clock | UTC |

**Not in MVP:** sliding window, token bucket, leaky bucket, request delay/retry queue.

### 3.5 Default limits (env-overridable)

All limits are **requests per window** for **non-duplicate** ingress only.

| Scope | Env prefix example | Default | Window (s) |
|-------|-------------------|---------|------------|
| tenant | `RATE_LIMIT_TENANT_LIMIT` | 1000 | 60 |
| business | `RATE_LIMIT_BUSINESS_LIMIT` | 300 | 60 |
| adapter (telegram) | `RATE_LIMIT_ADAPTER_TELEGRAM_LIMIT` | 120 | 60 |
| adapter (website_chat) | `RATE_LIMIT_ADAPTER_WEBSITE_CHAT_LIMIT` | 120 | 60 |
| conversation | `RATE_LIMIT_CONVERSATION_LIMIT` | 30 | 60 |

Separate env keys for window seconds per scope optional; MVP may use one `RATE_LIMIT_WINDOW_SECONDS=60` for all.

### 3.6 Duplicate / idempotency interaction

**Rule:** Idempotent duplicate inbound (E3.1/E2.3 — same idempotency key / external message already processed) **does not increment** counters and **does not** emit a violation.

Rate limiting applies to requests that would create new processing work (including first-seen idempotency keys).

---

## 4. Enforcement strategy (E3.5b)

### 4.1 Placement in webhook flow

Align with [incoming-message-flow.md](../../specs/flows/incoming-message-flow.md) and E3.4 gate ordering:

```text
1. Validate normalized payload (400 on failure — no counter)
2. Resolve business → tenant_id
3. [E3.5] Check/increment tenant + business + adapter buckets
4. Resolve flow, customer, conversation
5. Idempotency / duplicate detection
   → if duplicate: return success WITHOUT further increment (adapter/business/tenant already incremented? — see §4.3)
6. [E3.5] Check/increment conversation bucket
7. [E3.4 optional] Ingress containment gate
8. Orchestration (AI, delivery, leads)
```

**§4.3 refinement (recommended):** Perform **cheap pre-check** (read counts) at step 3 without increment. After duplicate detection at step 5, **increment all scopes once** for non-duplicate new work only. Conversation increment requires `conversation_id` from step 4.

Revised order:

```text
1. Validate
2. Resolve business/tenant
3. Resolve flow, customer, conversation (needed for conversation scope + duplicate key)
4. Duplicate check (read-only)
5. If duplicate → return (no rate increment)
6. Rate limit: atomic check-and-increment all scopes
7. If exceeded → record violation, return 429
8. E3.4 optional gate
9. Orchestration
```

Moving conversation resolution before rate limit adds DB reads on rejected traffic — acceptable MVP tradeoff for correct conversation scope. Tenant/business/adapter pre-reject can optionally use lightweight path before full conversation resolve (phase 2 optimization); **MVP uses single check after duplicate detection**.

### 4.2 Enforcement outcomes

| Outcome | HTTP | `error.code` | Processing |
|---------|------|--------------|------------|
| Accepted | 200/201 envelope | — | Counters incremented; orchestration runs |
| Rate limited | **429** | `RATE_LIMIT_EXCEEDED` | No orchestration; violation row persisted |
| Duplicate | 200 success | — | No increment (E3.1 behavior preserved) |
| Validation | 400 | `VALIDATION_ERROR` | No increment |

**No delayed acceptance** — reject only (no queues).

**Response metadata (safe):**

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Ingress rate limit exceeded",
    "metadata": {
      "scope_type": "conversation",
      "scope_key": "…",
      "adapter": "telegram",
      "retry_after_seconds": 42,
      "window_seconds": 60,
      "limit": 30,
      "current_count": 30
    }
  }
}
```

No message text, tokens, or PII in metadata.

### 4.3 Atomic check-and-increment

Single DB transaction in `RateLimitService`:

1. For each applicable scope, `SELECT … FOR UPDATE` bucket row (or insert with count=0).
2. If any `count >= limit` → rollback, write violation event(s), return exceeded.
3. Else increment all buckets, commit, proceed.

**Service:** `RateLimitService` in `backend/app/services/`.

**Integration:** `WebhookMessageService.process_incoming_message` after duplicate detection; route maps exception to 429.

### 4.4 Relationship to E3.4

| Mechanism | Trigger | Code | Purpose |
|-----------|---------|------|---------|
| E3.4 ingress gate | Inbound DL + contained | 503 `ADAPTER_INGRESS_CONTAINED` | Failure containment |
| E3.5 rate limit | Volume threshold | 429 `RATE_LIMIT_EXCEEDED` | Abuse/spike protection |

Both can be disabled independently via env flags.

---

## 5. Storage design (additive schema)

### 5.1 Table: `rate_limit_buckets`

Purpose: atomic counters per scope/window.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | required |
| `business_id` | UUID FK | required (tenant scope still stores business_id for query uniformity OR nullable for tenant-only — **prefer always set to resolving business for tenant scope key uses tenant_id only in scope_key**) |
| `scope_type` | VARCHAR | `tenant` \| `business` \| `adapter` \| `conversation` |
| `scope_key` | VARCHAR | deterministic string |
| `channel` | VARCHAR NULL | set for adapter scope |
| `window_start` | TIMESTAMPTZ | bucket start |
| `window_seconds` | INT | window size used |
| `request_count` | INT | monotonic within window |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

**Unique:** `(tenant_id, business_id, scope_type, scope_key, window_start)`

**Indexes:** `(tenant_id, business_id, scope_type, window_start)`, `(business_id, scope_type, scope_key, window_start)`

**Retention:** Optional cleanup job deferred; old buckets harmless at low volume. Document manual/scheduled purge as ops follow-up.

### 5.2 Table: `rate_limit_violations`

Purpose: append-only observability audit (E3.5c).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id`, `business_id` | UUID FK | |
| `scope_type`, `scope_key` | VARCHAR | exceeded scope |
| `channel` | VARCHAR NULL | adapter context |
| `conversation_id` | UUID NULL | when applicable |
| `limit_value` | INT | configured limit |
| `window_seconds` | INT | |
| `window_start` | TIMESTAMPTZ | |
| `observed_count` | INT | count at rejection |
| `correlation_id` | TEXT NULL | from observability context |
| `metadata` | JSONB NULL | safe only |
| `created_at` | TIMESTAMPTZ | |

**Indexes:** `(tenant_id, business_id, created_at)`, `(business_id, channel, created_at)`, `(scope_type, created_at)`

Migration: **`0017_rate_limit_buckets`**, **`0018_rate_limit_violations`** (one logical concern per revision preferred: can combine if team approves single migration).

---

## 6. Observability (E3.5c)

### 6.1 List violations API

**`GET /api/v1/observability/rate-limits`**

Auth: webhook token (same as other observability routes).

Query: `tenant_id`, `business_id` required; optional `channel`, `scope_type`, `conversation_id`, `limit`, `offset`.

Response:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "scope_type": "conversation",
        "scope_key": "…",
        "channel": "telegram",
        "conversation_id": "uuid",
        "limit_value": 30,
        "window_seconds": 60,
        "observed_count": 31,
        "created_at": "…"
      }
    ],
    "limit": 20,
    "offset": 0
  }
}
```

### 6.2 Adapter monitoring extension (optional in E3.5c)

Extend **`GET /api/v1/observability/adapters`** items with:

```text
rate_limit_violation_count  (violations in lookback window, by channel)
```

Derived from `rate_limit_violations` — no new logic duplication.

### 6.3 Operator signals

Operators can answer:

- Which adapter hit limits? → filter `channel`
- Which business? → `business_id` query param
- Spike vs sustained? → violation time series in window
- Cross-adapter? → compare telegram vs website_chat violation counts (should be independent at adapter scope)

---

## 7. Scope hierarchy summary

```text
Request
  └─ tenant bucket     (widest)
       └─ business bucket
            └─ adapter bucket (telegram | website_chat)
                 └─ conversation bucket (narrowest)
```

**First exceeded scope** determines violation record and error metadata (most specific wins for messaging: conversation > adapter > business > tenant).

---

## 8. Transaction boundaries

- Rate check + increment: **same transaction** as violation insert on failure (read-only check then rollback) OR separate read-only check then increment in orchestration transaction before AI — **recommended:** dedicated short transaction for rate limit before main webhook transaction commits orchestration.
- Violation row: persisted even if main webhook rolls back (separate commit) so ops visibility survives failures — **acceptable** for audit.

---

## 9. Implementation slices (after approval)

### E3.5a — Model + migration

- Alembic `0017`/`0018`, models, `RateLimitPolicy` (limits from env)
- Unit tests for window bucket key + hierarchy

### E3.5b — Enforcement

- `RateLimitService.check_and_increment(...)`
- Wire into `WebhookMessageService` post-duplicate
- `429` in webhook route; feature flag default off
- Tests: duplicate exempt, adapter isolation, 429 metadata

### E3.5c — Observability

- `RateLimitViolationService.list`
- `GET /observability/rate-limits`
- Optional adapter API field
- Update `specs/api/api-endpoints.md`, E2 verifier route list

---

## 10. Required tests (acceptance)

1. Under limit → request accepted; counters increment.
2. Over conversation limit → 429; no AI/orchestration side effects.
3. Telegram over limit does not block website_chat (adapter scope isolation).
4. Duplicate inbound does not increment or violate.
5. Flag off → legacy behavior unchanged.
6. Violation list API tenant-scoped.
7. E3.1 / E3.2 / E3.3 / E3.4 / E2.7 regression green.

---

## 11. Risks and rollback

| Risk | Mitigation |
|------|------------|
| False positives on legitimate bursts | Defaults conservative; env tuning; duplicate exempt |
| DB write amplification (4 buckets/request) | Short transaction; indexed UPSERT; limits enabled gradually |
| Conversation resolve before limit adds latency | Accept for MVP; document optimization path |
| Multi-worker correctness | PostgreSQL row locks — not in-memory |
| Business limit affects both adapters | Document as intentional total cap |

**Rollback:**

1. Set `ALPSTEIN_AI_RATE_LIMIT_ENABLED=false`.
2. Remove webhook integration (code rollback).
3. Tables can remain empty (no runtime dependency when disabled).

---

## 12. Rollout (operator)

1. Deploy migrations + backend with flag **off**.
2. **Gate:** complete E3.5d PostgreSQL concurrency validation ([`T-e3.5d-postgres-concurrency-validation.md`](../../tasks/todo/T-e3.5d-postgres-concurrency-validation.md)) — **`ALPSTEIN_AI_RATE_LIMIT_ENABLED` must remain `false` until this passes**.
3. Staging: enable flag with low limits; verify 429 + observability.
4. Production: enable per environment after staging review.
5. Monitor `GET /observability/rate-limits` and adapter violation counts.

---

## 13. Approval checklist

- [ ] Two-table PostgreSQL approach approved (vs derived-only)
- [ ] Fixed 60s window + default limits acceptable
- [ ] Enforcement after duplicate detection order acceptable
- [ ] Reject-only (429) — no delay/queue
- [ ] `GET /observability/rate-limits` API acceptable
- [ ] Feature flag default **off** acceptable
- [ ] Business-level shared cap across adapters understood
- [ ] n8n unchanged (backend returns 429; n8n should backoff — document only)

**After approval:** implement E3.5a → E3.5b → E3.5c; reviewer pass; stop for human review (no commit unless asked).
