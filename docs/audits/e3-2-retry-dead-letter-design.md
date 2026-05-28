# E3.2 — Retry / dead-letter behavior (design)

**Branch:** `stabilization/runtime-baseline`  
**Phase:** E3 — Multi-Channel Operational Hardening  
**Status:** **Implemented** — see [`e3-2-retry-dead-letter.md`](e3-2-retry-dead-letter.md)  
**Prerequisite:** E3.1 complete (`inbound_processing_locks`, `replay_events`, terminal delivery PATCH)

---

## 1. Executive summary

E3.2 adds **deterministic retry accounting** and **dead-letter persistence** for two backend-owned domains:

| Domain | Who retries in MVP | E3.2 role |
|--------|-------------------|-----------|
| **Outbound delivery** | n8n transport (Telegram Send, Website Respond) may re-attempt; backend records outcomes via PATCH | Formal retry counter, max limit, `dead_letter` terminal state, audit rows |
| **Inbound processing** | n8n/provider webhook redelivery (same idempotency key) | Count provider retries via lock `replay_count`; dead-letter when exhausted; **no** in-process OpenAI retry worker |

**Explicit non-goals:** Kafka/RabbitMQ/Redis/Celery, background workers, automatic OpenAI re-call inside one webhook request, n8n → PostgreSQL, frontend dashboards, CRM.

**Golden rule preserved:** E3.1 replay protection remains authoritative for concurrent/duplicate ingress; E3.2 does not weaken idempotency or terminal `delivered` semantics.

---

## 2. Threat map

| # | Threat | Current gap | E3.2 mitigation |
|---|--------|-------------|-----------------|
| 1 | Transient OpenAI timeout/error | Single gateway call; fallback text; trace may `completed` with `ai_failed` | **Document** as non-retryable in MVP; optional `retry_attempts` row `scope=inbound_ai` with `attempt=1` only; dead-letter only if future worker added |
| 2 | Transient HTTP (n8n → backend) | n8n error branch; provider may redeliver webhook | E3.1 lock + `replay_events`; E3.2 inbound DL when `inbound_processing_locks.replay_count` ≥ max |
| 3 | Telegram delivery failure | PATCH `failed`; `retry_count` increments only if n8n sends `retrying` | Enforce max on `increment_retry`; terminal `dead_letter` + `dead_letter_events` |
| 4 | Website delivery failure | Same as Telegram | Same |
| 5 | Replay vs retry confusion | `replay_events` for duplicate/illegal PATCH | Separate `retry_attempts` for failure/retry lifecycle; cross-link IDs in metadata |
| 6 | Duplicate dead-letter rows | None today | Unique partial index on `(business_id, scope_type, scope_id)` where `resolved_at IS NULL` |
| 7 | Dead-letter table growth | N/A | Append-only; ops retention policy documented; no auto-purge in MVP |
| 8 | Unbounded n8n PATCH `retrying` | Counter exists; no cap | Backend rejects transition to `retrying` when `retry_count >= max`; no-op + `retry_exhausted` replay event |
| 9 | `delivered` corrupted by retry storm | E3.1b terminal guard | Unchanged; illegal transitions still no-op |

---

## 3. Retry strategy

### 3.1 Principles

1. **Backend owns state; n8n owns transport.** Retries are initiated by n8n (re-send message, re-call webhook) or provider redelivery—not by a new backend worker.
2. **Count attempts in PostgreSQL** on each legitimate retry signal (PATCH `retrying`, lock replay increment).
3. **Fail closed at max:** further retry transitions become no-op; record moves to dead-letter.
4. **Distinguish transient vs terminal** via `error_type` classification (configurable allowlist), not automatic AI re-invocation in MVP.

### 3.2 Error classification (MVP)

| Class | Examples | Backend behavior |
|-------|----------|------------------|
| **Transient (delivery)** | `telegram_rate_limit`, `telegram_timeout`, `website_chat_delivery_failed` (5xx) | Allow `failed` → `retrying` if under max |
| **Terminal (delivery)** | `chat_not_found`, `invalid_chat_id`, `blocked` | Recommend n8n skip retry; backend allows one `failed` PATCH then DL on next `retrying` attempt or immediate DL if `error_type` in terminal set |
| **Transient (inbound)** | n8n timeout calling backend | Provider redelivery; lock `replay_count++` |
| **Terminal (inbound)** | `BUSINESS_NOT_FOUND`, validation errors | No DL loop; fail fast on first request |
| **AI provider** | OpenAI timeout | Fallback reply; **no** retry loop in E3.2 MVP |

Terminal delivery `error_type` list: env `ALPSTEIN_DELIVERY_TERMINAL_ERROR_TYPES` (comma-separated) with safe defaults in code.

### 3.3 Configuration (env)

| Variable | Default | Scope |
|----------|---------|--------|
| `ALPSTEIN_DELIVERY_MAX_RETRIES` | `3` | Outbound delivery PATCH `retrying` cycles |
| `ALPSTEIN_INBOUND_PROVIDER_RETRY_MAX` | `5` | `inbound_processing_locks.replay_count` before inbound DL |
| `ALPSTEIN_DELIVERY_TERMINAL_ERROR_TYPES` | `chat_not_found,invalid_chat_id` | Skip retry encouragement |

No per-tenant tuning in MVP (platform constants only).

---

## 4. Dead-letter strategy

### 4.1 When dead-letter is created

| Trigger | `event_type` | Primary key scope |
|---------|--------------|-------------------|
| Delivery `retry_count >= max` after `failed` or blocked `retrying` | `delivery_exhausted` | `delivery_id` |
| Terminal `error_type` on first `failed` PATCH (optional strict mode) | `delivery_terminal_failure` | `delivery_id` |
| Inbound lock `replay_count >= max` on replay conflict | `inbound_exhausted` | `inbound_message_id` or lock scope |
| Manual ops (future) | `manual` | — |

**One active dead-letter row per scope:** `UNIQUE (business_id, scope_type, scope_id)` where `resolved_at IS NULL`. Re-exhaustion updates `retry_count` / `last_seen_at` on existing row (idempotent), does not insert duplicate.

### 4.2 What is stored

- **References only:** UUIDs (`tenant_id`, `business_id`, `flow_id`, `conversation_id`, `trace_id`, `delivery_id`, `inbound_message_id`, `outbound_message_id`).
- **Safe text:** `failure_reason` (truncated), `error_type`, `last_error_message` (max 500 chars).
- **Counters:** `retry_count` at exhaustion.
- **No:** raw provider payloads, tokens, API keys, full customer message bodies.

### 4.3 What is not lost

- Original `messages`, `message_traces`, `delivery_events` rows remain unchanged (except delivery `status` → `dead_letter`).
- `retry_attempts` append log retains history.
- `replay_events` (E3.1) retains duplicate/replay audit.

### 4.4 Resolution (MVP)

- `resolved_at` / `resolved_by` columns **nullable**, unused by automation.
- No PATCH “resolve dead-letter” API in E3.2 MVP (read-only ops visibility). Defer to E3.3+ if needed.

---

## 5. Retry state machines

### 5.1 Outbound delivery (`delivery_events.status`)

**Existing (E3.1b):** `pending`, `delivered`, `failed`, `skipped`, `retrying`.

**E3.2 addition:** `dead_letter` (terminal).

```text
pending ──► delivered (terminal)
         ├─► skipped (terminal)
         ├─► failed ──► retrying ──► delivered
         │              │    ▲
         │              └────┘ (retry_count < max)
         │              └──► failed ──► dead_letter (terminal, retry_count >= max)
         └─► retrying (from pending, rare)

dead_letter: terminal (no transition out except idempotent dead_letter → dead_letter)

delivered / skipped: unchanged (E3.1b terminal guard)
```

**PATCH behavior (extends E3.1b):**

| Request | Current | Allowed when |
|---------|---------|--------------|
| `retrying` | `failed`, `pending` | `retry_count < max` and not terminal error_type |
| `failed` | `pending`, `retrying` | always (increments context) |
| `delivered` | `pending`, `retrying` | always if allowed by E3.1b |
| `retrying` | `failed` | blocked → no-op + `retry_exhausted` replay_event + DL row if at cap |
| any | `dead_letter` | idempotent no-op only |

On each allowed `retrying` transition: `increment_retry`, append `retry_attempts` row, set `last_retry_at`.

### 5.2 Inbound processing (`message_traces.status`)

**No new trace status required for MVP** if we treat provider redelivery as replay (E3.1).

Optional **additive** trace status `dead_letter` (only set when inbound exhausted)—alternative: keep trace `failed` / `processing` and rely on `dead_letter_events` + lock state.

**Recommended MVP:** Do **not** add `message_traces.dead_letter`; use `dead_letter_events.event_type=inbound_exhausted` + lock `status=failed` to avoid trace enum churn.

```text
accepted → processing → completed
                      → failed (unhandled exception)
skipped_duplicate (dedup)
(replay) processing preserved — E3.1

Provider retry (same idempotency_key):
  lock.replay_count++
  if replay_count >= max → dead_letter_events + replay_events.retry_exhausted
  response: is_duplicate=true (no AI)
```

### 5.3 Unified retry attempt log (`retry_attempts` — E3.2a)

Append-only audit (separate from `replay_events`):

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id`, `business_id` | UUID NOT NULL | FK |
| `scope_type` | TEXT | `delivery`, `inbound` |
| `scope_id` | UUID | `delivery_id` or `inbound_processing_lock.id` |
| `trace_id` | UUID NULL | |
| `conversation_id` | UUID NULL | |
| `attempt_number` | INT | 1-based |
| `status` | TEXT | `retrying`, `failed`, `exhausted` |
| `error_type` | TEXT NULL | |
| `error_message` | TEXT NULL | truncated |
| `correlation_id` | TEXT NULL | |
| `metadata` | JSONB NULL | sanitized |
| `created_at` | TIMESTAMPTZ | |

Indexes: `(business_id, scope_type, scope_id, created_at)`, `(business_id, conversation_id, created_at)`, `(trace_id)`.

---

## 6. Dead-letter persistence (E3.2b)

### Table: `dead_letter_events`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id`, `business_id` | UUID NOT NULL | |
| `flow_id` | UUID NULL | |
| `conversation_id` | UUID NULL | |
| `trace_id` | UUID NULL | |
| `delivery_id` | UUID NULL | |
| `inbound_message_id` | UUID NULL | |
| `outbound_message_id` | UUID NULL | |
| `scope_type` | TEXT NOT NULL | `delivery`, `inbound` |
| `scope_id` | UUID NOT NULL | |
| `event_type` | TEXT NOT NULL | see §4.1 |
| `failure_reason` | TEXT NOT NULL | human-safe summary |
| `error_type` | TEXT NULL | |
| `retry_count` | INT NOT NULL | at time of DL |
| `correlation_id` | TEXT NULL | |
| `metadata` | JSONB NULL | sanitized |
| `resolved_at` | TIMESTAMPTZ NULL | future ops |
| `created_at` | TIMESTAMPTZ NOT NULL | |
| `last_seen_at` | TIMESTAMPTZ NOT NULL | updated on idempotent re-hit |

**Unique:** `(business_id, scope_type, scope_id)` WHERE `resolved_at IS NULL` (partial unique index).

**Migration:** `0015_retry_attempts.py`, `0016_dead_letter_events.py` (or single `0015` if team prefers one revision—implementation should use **two logical revisions** per migration-engineer rule).

**Delivery row update:** set `delivery_events.status = dead_letter` when delivery exhausted (alongside DL insert).

---

## 7. Transaction boundaries

| Operation | Unit of work | Ordering |
|-----------|--------------|----------|
| PATCH delivery status | Single DB transaction | 1) load event (tenant+business); 2) validate transition; 3) update event / increment retry; 4) insert `retry_attempts`; 5) if exhausted → insert/update `dead_letter_events` + `replay_events.retry_exhausted`; 6) commit |
| Inbound lock replay | Same session as webhook | 1) increment lock replay_count; 2) if ≥ max → DL upsert + replay event; 3) return duplicate response **without** AI |
| Webhook success path | Existing | Lock release `completed` unchanged |
| Illegal PATCH (E3.1) | Same transaction | DL not created; `illegal_transition` replay only |

**Isolation:** rely on PostgreSQL row lock via `SELECT` on `delivery_events` by PK within transaction (SQLAlchemy session flush order). No distributed locks.

**Idempotency:** Duplicate PATCH `retrying` at cap → no counter increment; single DL row via upsert.

---

## 8. Observability model (E3.2c)

### 8.1 APIs (webhook token, same as E2.5/E3.1)

#### `GET /api/v1/observability/retries`

- **Required:** `tenant_id`, `business_id`
- **Optional:** `trace_id`, `delivery_id`, `conversation_id`, `scope_type`, `status`, `limit`, `offset`
- **Response:** `success`, `data.items[]` from `retry_attempts` (no secrets)

#### `GET /api/v1/observability/dead-letter`

- **Required:** `tenant_id`, `business_id`
- **Optional:** `trace_id`, `delivery_id`, `conversation_id`, `inbound_message_id`, `event_type`, `scope_type`, `limit`, `offset`
- **Response:** `success`, `data.items[]` from `dead_letter_events`

### 8.2 Relationship to existing APIs

| API | Purpose |
|-----|---------|
| `GET /observability/traces` | Trace lifecycle |
| `GET /observability/deliveries` | Delivery current state |
| `GET /observability/replays` | Duplicate/replay/illegal PATCH (E3.1) |
| `GET /observability/retries` | **E3.2** attempt history |
| `GET /observability/dead-letter` | **E3.2** exhausted failures |

### 8.3 n8n impact (post-implementation, optional slice)

- **Not required for E3.2 backend merge** to pass tests.
- Follow-up doc: when transport fails with transient error, n8n may PATCH `retrying` before re-send; when backend returns DL, n8n should stop transport retry and surface ops alert (workflow branch reading `delivery_status=dead_letter` on subsequent webhook—**future**).

MVP backend must be correct **even if n8n never sends `retrying`** (counters stay 0; DL only on explicit exhaustion paths).

---

## 9. Implementation slices (after approval)

### E3.2a — Retry lifecycle

- Migration `retry_attempts`
- `RetryLifecycleService` (record attempt, list, enforce max)
- Extend `delivery_state_machine` + `DeliveryVisibilityService`
- Wire inbound lock exhaustion
- Env config
- Tests: counter increment, max enforced, idempotent retry

### E3.2b — Dead-letter persistence

- Migration `dead_letter_events` + `delivery_events.status` enum value `dead_letter`
- `DeadLetterService` (upsert, list)
- Wire from delivery PATCH and inbound replay
- Tests: DL created on exhaustion, unique scope, tenant isolation

### E3.2c — Retry observability

- Schemas + routes `GET /retries`, `GET /dead-letter`
- Update `specs/api/api-endpoints.md`
- Tests: API filters, forbidden fields, cross-business blocked
- Update `scripts/verify/e2_observability_verification.py` route list (optional)

---

## 10. Required tests (acceptance)

1. Delivery `retry_count` increments on allowed `retrying` PATCH.
2. PATCH `retrying` blocked when `retry_count >= ALPSTEIN_DELIVERY_MAX_RETRIES`.
3. Exhaustion creates `dead_letter_events` + `delivery_events.status=dead_letter` + `replay_events.retry_exhausted`.
4. Duplicate exhaustion does not create second DL row (upsert `last_seen_at`).
5. Dead-letter list API returns only matching `tenant_id` + `business_id`.
6. Retries API returns attempt history with correct filters.
7. E3.1 tests remain green (in-flight replay, terminal delivery, replay API).
8. E2 continuity harness passes (update head revision in verifier).

---

## 11. Operational risks

| Risk | Mitigation |
|------|------------|
| n8n never sends `retrying` | DL path dormant until workflow updated; document ops manual PATCH |
| DL table growth | Monitor row counts; future retention job out of scope |
| Stale `processing` locks (E3.1) | Separate from DL; optional TTL sweeper still deferred |
| Terminal error misclassified | Conservative default list; env override |
| OpenAI failures invisible in DL | Use traces + `prompt_runs.error`; document gap |

---

## 12. Rollback plan

1. Deploy previous backend image (no downgrade on prod with DL data unless empty).
2. Alembic: `downgrade` `0016` → `0015` → `0014` only if tables empty or staging.
3. n8n: no change required for rollback if workflows not updated.
4. Re-run Gate 1 + one Telegram/website smoke after rollback.

---

## 13. Spec / doc updates (with implementation)

- `specs/api/api-endpoints.md` — new GET endpoints
- `specs/database/database-schema.md` — new tables (database-architect)
- `docs/architecture/message-trace-lifecycle.md` — inbound exhaustion
- `docs/n8n/delivery-outcome-patching.md` — `retrying` / `dead_letter` PATCH examples
- `docs/audits/e3-2-retry-dead-letter.md` — implementation audit (post-merge)
- `docs/project-status/current-state.md` / `next-steps.md`

---

## 14. Design decisions log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Worker-based retry | **Rejected** | Violates runtime constraints |
| Separate `retry_attempts` vs overload `replay_events` | **Separate table** | Clear semantics: replay ≠ failure retry |
| Add `message_traces.dead_letter` | **Deferred** | DL table sufficient for MVP |
| In-process OpenAI retry | **Out of scope** | Single gateway call + fallback is current product behavior |
| `dead_letter` on `delivery_events` | **Yes** | Operators see terminal state in delivery list API |

---

## 15. Approval checklist

- [ ] Scope limited to backend additive schema + observability APIs
- [ ] No queue/worker/container additions
- [ ] E3.1 behavior preserved
- [ ] n8n transport retry contract understood (optional workflow follow-up)
- [ ] Migrations reversible
- [ ] Tenant isolation on all new queries

**After approval:** implement E3.2a → E3.2b → E3.2c sequentially; reviewer pass per slice.
