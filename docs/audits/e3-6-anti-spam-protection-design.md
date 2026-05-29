# E3.6 — Anti-spam protection (design)

**Branch:** `stabilization/runtime-baseline`  
**Phase:** E3 — Multi-Channel Operational Hardening  
**Status:** **Design only — awaiting approval before implementation**  
**Prerequisites:** E3.1 replay protection, E3.5 rate limiting (accepted), E3.4 ingress isolation

---

## 1. Executive summary

E3.6 adds **backend-owned, deterministic anti-spam protection** for MVP adapters **`telegram`** and **`website_chat`**. It complements E3.5 (infrastructure volume caps) with **explainable behavioral rules**: repeated payloads, conversation flooding patterns, retry/replay abuse signals, and adapter-scoped containment.

| Slice | Deliverable |
|-------|-------------|
| E3.6a | Spam detection model — deterministic indicators, env-configurable thresholds, no scoring |
| E3.6b | Containment — reversible actions (`allow`, `mark_suspicious`, `throttle`, `temporary_block`, `ignore`); no permanent bans |
| E3.6c | Observability — decision audit + active containment list APIs; optional adapter metric extension |

**Storage decision:** **Three additive PostgreSQL tables** (see §5). Existing observability tables are sufficient for **read-only signals** (retry ratios) but **not** for atomic pre-orchestration counters or **reversible active containment state**.

**Rollout:** Feature flag `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED` default **`false`** (same pattern as E3.4/E3.5).

**Non-goals:** AI/ML moderation, external anti-spam APIs, content classification, permanent auto-ban, tenant-wide blocking, queues/workers, Redis, dashboards, n8n workflow changes, storing message text in spam audit rows.

---

## 2. Problem statement vs E3.5

| Concern | E3.5 rate limiting | E3.6 anti-spam |
|---------|-------------------|----------------|
| Protects | Infrastructure capacity | Abuse patterns & user-visible spam |
| Mechanism | Fixed-window request counts | Deterministic rules (payload repeat, burst shape, retry ratios) |
| Duplicate idempotent retries | Exempt from counters | Exempt from spam increment (same as E3.5) |
| Typical false positive | Legitimate burst traffic | Repeated “hello?” messages, widget double-submit |
| Primary operator question | “Are we over capacity?” | “Why was this conversation throttled?” |

E3.5 and E3.6 stack: volume cap first (cheap), behavioral evaluation second (more context).

---

## 3. Threat map

| # | Threat | Current gap | E3.6 mitigation |
|---|--------|-------------|-----------------|
| 1 | Repeated message spam (same text) | Idempotency stops duplicate **AI**; new keys still flood | `payload_repeat` indicator + conversation-scoped containment |
| 2 | Payload replay abuse (hash-stable spam) | No content-pattern counter | Normalized text hash bucket per conversation/window |
| 3 | Conversation flooding (many distinct messages) | E3.5 conversation **volume** cap only | `conversation_burst` + softer `mark_suspicious` before hard reject |
| 4 | Adapter flooding (many conversations) | E3.5 adapter volume cap | Adapter-scoped indicators + optional `temporary_block` per adapter |
| 5 | Retry / replay abuse | E3.1/E3.2 handle correctness, not spam classification | Derived `retry_abuse` signal from `replay_events` + lock `replay_count` |
| 6 | False positives (legitimate rapid questions) | N/A | `mark_suspicious` path, high thresholds, env tuning, short TTL blocks |
| 7 | Tenant isolation breach | N/A | All rows/queries filter `tenant_id`; business-scoped where applicable |
| 8 | Business isolation breach | N/A | Containment keys include `business_id`; no cross-business scope |

---

## 4. Spam detection model (E3.6a)

### 4.1 Design principles

| Principle | MVP rule |
|-----------|----------|
| Deterministic | Same inputs → same rule outcome |
| Explainable | Every decision cites `rule_id`, threshold, observed count |
| Observable | Append-only decision audit; no hidden score |
| Reversible | All blocks/throttles expire; manual release API deferred (ops uses TTL) |
| No AI/ML | Hash + count + ratio only |
| No PII in audit | Store `payload_hash` (SHA-256 hex), never `message.text` |

### 4.2 Evaluation scope hierarchy

Containment applies at the **most specific** scope that triggered the rule (same specificity order as E3.5 violations):

```text
conversation > adapter > business > tenant
```

**Hard rule:** No automatic **tenant-wide** block. Tenant scope may only emit `mark_suspicious` (audit-only) in MVP.

### 4.3 Deterministic indicators (rules)

Each rule has: `rule_id`, `scope`, `window_seconds`, `threshold`, `action` (default containment if triggered).

| rule_id | Signal | Scope | Window (default) | Threshold (default) | Default action | Notes |
|---------|--------|-------|------------------|---------------------|----------------|-------|
| `payload_repeat_conversation` | Same normalized payload hash repeated | `conversation` | 300s | 5 | `throttle` | Hash from E2.3 normalization (`" ".join(text.split())` then SHA-256) |
| `conversation_burst` | Distinct **non-duplicate** ingress messages | `conversation` | 60s | 15 | `mark_suspicious` | Softer than E3.5 conversation limit (30/60s); fires earlier for ops visibility |
| `adapter_conversation_fanout` | Distinct conversations with ingress | `adapter` | 300s | 50 | `mark_suspicious` | Many chats opened quickly — possible bot |
| `retry_abuse_conversation` | `replay_events` + lock conflicts in window | `conversation` | 600s | 10 | `throttle` | Derived read; no new counter required |
| `inflight_replay_storm` | `replay_ignored` events | `adapter` | 300s | 20 | `temporary_block` | Short TTL block on adapter only |

**Env prefix:** `SPAM_RULE_<RULE_ID>_…` or grouped `SPAM_<RULE>_THRESHOLD`, `SPAM_<RULE>_WINDOW_SECONDS`, `SPAM_<RULE>_ACTION`.

**Disabled rules:** action `ignore` or threshold `0` disables rule.

### 4.4 Payload hash (safe fingerprint)

```python
normalized_text = " ".join(message_text.split())
payload_hash = sha256(normalized_text.encode("utf-8")).hexdigest()
```

- Used for **`payload_repeat`** bucket key: `{conversation_id}:{payload_hash}`.
- Stored in audit as full hash or `hash_prefix` (first 12 hex chars) — **never** store raw text.
- Identical normalization as idempotency fallback path (without business/flow/timestamp in hash — intentional: spam cares about content repetition).

### 4.5 What is evaluated

**Ingress only:** `POST /api/v1/webhook/message` for **`telegram`** and **`website_chat`**, on **non-duplicate** path (after E3.1 duplicate short-circuit).

**Not evaluated:**

- Idempotent duplicate returns (no increment, no new decision beyond `allow`)
- Validation errors (`400`) before business resolution
- Observability GET/PATCH routes
- `test` channel (unless explicitly enabled later)

### 4.6 Why existing tables are insufficient (detection)

| Source | Observe pattern? | Atomic pre-orchestration? | Reversible active block? |
|--------|------------------|---------------------------|-------------------------|
| `message_traces` | After trace exists | No — race under concurrency | No |
| `messages` | Has text (PII) | No — post-persist | No |
| `replay_events` | Retry/replay audit | Read-only OK for ratios | No |
| `rate_limit_buckets` | Volume only | Yes | No |
| `rate_limit_violations` | Volume audit | N/A | No |

**Conclusion:** Need dedicated **indicator buckets** (like E3.5) for payload/burst counters; need **containment state** table for active TTL blocks.

---

## 5. Schema requirements (E3.6a / storage strategy)

### 5.1 Recommended tables (additive)

#### Table 1: `spam_indicator_buckets` (atomic counters)

Purpose: burst-safe counters for content/pattern signals.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | required |
| `business_id` | UUID FK | required |
| `rule_id` | VARCHAR(64) | e.g. `payload_repeat_conversation` |
| `scope_type` | VARCHAR(32) | `conversation` \| `adapter` \| `business` |
| `scope_key` | VARCHAR(255) | e.g. `{conversation_id}:{payload_hash}` |
| `channel` | VARCHAR(50) NULL | adapter rules |
| `window_start` | TIMESTAMP | UTC fixed window |
| `window_seconds` | INT | |
| `signal_count` | INT | monotonic within window |
| `created_at` / `updated_at` | TIMESTAMP | |

**Unique:** `(tenant_id, business_id, rule_id, scope_type, scope_key, window_start)`

#### Table 2: `spam_containments` (active reversible enforcement)

Purpose: active `throttle` / `temporary_block` until expiry or release.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | |
| `business_id` | UUID FK | |
| `rule_id` | VARCHAR(64) | triggering rule |
| `scope_type` | VARCHAR(32) | |
| `scope_key` | VARCHAR(255) | |
| `channel` | VARCHAR(50) NULL | |
| `conversation_id` | UUID NULL | when scope is conversation |
| `action` | VARCHAR(32) | `throttle` \| `temporary_block` |
| `expires_at` | TIMESTAMP | required — no permanent rows |
| `released_at` | TIMESTAMP NULL | set when expired or manually cleared |
| `correlation_id` | TEXT NULL | |
| `metadata` | JSONB NULL | safe: counts, thresholds, hash_prefix only |
| `created_at` | TIMESTAMP | |

**Partial unique (active):** `(tenant_id, business_id, scope_type, scope_key, rule_id) WHERE released_at IS NULL` — one active containment per scope/rule.

**No `spam_events` table:** append-only detections are merged into `spam_decisions` (below) to avoid duplicate audit streams.

#### Table 3: `spam_decisions` (append-only observability audit)

Purpose: answer “why blocked/throttled?” — includes `allow` and `mark_suspicious` for completeness.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | |
| `business_id` | UUID FK | |
| `rule_id` | VARCHAR(64) | |
| `scope_type` | VARCHAR(32) | |
| `scope_key` | VARCHAR(255) | |
| `channel` | VARCHAR(50) NULL | |
| `conversation_id` | UUID NULL | |
| `decision` | VARCHAR(32) | `allow` \| `mark_suspicious` \| `throttle` \| `temporary_block` \| `ignore` |
| `outcome` | VARCHAR(32) | `passed` \| `applied` \| `already_contained` \| `skipped_duplicate` |
| `observed_count` | INT NULL | |
| `threshold` | INT NULL | |
| `window_seconds` | INT NULL | |
| `containment_id` | UUID NULL FK → `spam_containments.id` | |
| `correlation_id` | TEXT NULL | |
| `metadata` | JSONB NULL | safe only |
| `created_at` | TIMESTAMP | |

**Indexes:** `(tenant_id, business_id, created_at)`, `(business_id, channel, created_at)`, `(conversation_id, created_at)`, `(rule_id, created_at)`

**Migrations (proposed):** `0019_spam_indicator_buckets`, `0020_spam_containments`, `0021_spam_decisions` (one logical concern per revision).

### 5.2 Derived signals (no new storage)

| Rule | Source |
|------|--------|
| `retry_abuse_conversation` | COUNT `replay_events` for `conversation_id` in window |
| `inflight_replay_storm` | COUNT `replay_events` where `event_type=replay_ignored`, join trace → channel |

These are **eventually consistent** under concurrency — acceptable for `mark_suspicious` / adapter block with conservative thresholds. Not used for payload-repeat atomic paths.

---

## 6. Containment strategy (E3.6b)

### 6.1 Actions

| Action | Runtime effect | Persisted? | Reversible? |
|--------|----------------|------------|-------------|
| `allow` | Proceed to orchestration | Decision row only | N/A |
| `mark_suspicious` | Proceed; flag in audit | Decision row | N/A |
| `ignore` | Rule disabled / skipped | Optional skip row | N/A |
| `throttle` | Reject ingress with **429** `SPAM_THROTTLED` | Active containment + decision | TTL expiry |
| `temporary_block` | Reject ingress with **403** `SPAM_CONTAINED` | Active containment + decision | TTL expiry |

**No delay queue, no retry queue, no async worker** — reject-only (same posture as E3.5).

**Duplicate idempotent inbound:** return existing success path; **no** spam increment, **no** new containment.

### 6.2 Placement in webhook flow

Align with E3.5 ordering:

```text
1. Validate normalized payload
2. Resolve business → tenant, flow, customer, conversation
3. Persist incoming message + message trace
4. If duplicate → return success (no spam evaluation)
5. E3.5 rate limit check/increment → 429 RATE_LIMIT_EXCEEDED
6. E3.6 spam evaluation:
   a. Check active spam_containments for scope chain (conversation → adapter → business)
   b. If active block/throttle → record decision, reject
   c. Else evaluate rules; increment indicator buckets where needed
   d. If rule triggers → apply containment (TTL), record decision, reject or mark_suspicious
7. E3.4 optional ingress containment gate → 503
8. AI orchestration
```

**Rationale:** Spam evaluation after duplicate detection and rate limit avoids double-counting retries; rate limit remains the first cheap gate.

### 6.3 TTL defaults (env-overridable)

| Action | Default TTL |
|--------|-------------|
| `throttle` | 300s (5 min) |
| `temporary_block` | 900s (15 min) |

Re-release: set `released_at = now()` when `expires_at` passed (lazy on read) or background cleanup deferred.

### 6.4 Cross-adapter isolation

- Adapter-scoped containment uses `scope_key = {business_id}:{channel}` — same pattern as E3.5 adapter scope.
- Blocking `telegram` **must not** block `website_chat`.
- Business-scoped `mark_suspicious` does not block adapters unless explicit business rule added (none in MVP defaults).

### 6.5 Error responses (safe metadata)

**429 SPAM_THROTTLED:**

```json
{
  "success": false,
  "error": {
    "code": "SPAM_THROTTLED",
    "message": "Ingress temporarily throttled due to spam protection",
    "metadata": {
      "rule_id": "payload_repeat_conversation",
      "scope_type": "conversation",
      "scope_key": "...",
      "adapter": "telegram",
      "retry_after_seconds": 240,
      "observed_count": 5,
      "threshold": 5
    }
  }
}
```

**403 SPAM_CONTAINED:** same shape with `temporary_block` semantics.

No message text, tokens, secrets, or PII in metadata.

### 6.6 Transaction boundaries

- Indicator increment + containment insert: same transaction as webhook processing **or** short dedicated transaction (mirror E3.5).
- **Decision audit:** persist in **isolated commit** (like `rate_limit_violations`) so ops visibility survives webhook rollback on reject.
- Active containment row must commit when block applied even if main webhook rolls back.

---

## 7. Observability strategy (E3.6c)

### 7.1 List APIs (webhook token auth)

**`GET /api/v1/observability/spam-decisions`**

Query: `tenant_id`, `business_id` required; optional `channel`, `rule_id`, `conversation_id`, `decision`, `limit`, `offset`.

Response: paginated `items` with rule, scope, decision, outcome, counts, `created_at` — no message content.

**`GET /api/v1/observability/spam-containments`**

Query: `tenant_id`, `business_id` required; optional `channel`, `scope_type`, `active_only=true` (default).

Response: active and recently expired containments with `expires_at`, `action`, `rule_id`.

### 7.2 Adapter monitoring extension (optional E3.6c)

Extend **`GET /api/v1/observability/adapters`** items with:

```text
spam_decision_count      -- decisions with decision != allow in window
spam_containment_count   -- active containments for channel
```

Derived from `spam_decisions` / `spam_containments` — no duplicate logic.

### 7.3 Operator questions answered

| Question | Source |
|----------|--------|
| Why blocked? | Latest `spam_decisions` row: `rule_id`, `observed_count`, `threshold` |
| Why throttled vs blocked? | `decision` = `throttle` vs `temporary_block` |
| Which adapter? | `channel` filter |
| Which conversation? | `conversation_id` filter |
| Which rule? | `rule_id` filter |
| Still active? | `spam_containments` with `released_at IS NULL` and `expires_at > now` |

---

## 8. Configuration

| Env | Default | Purpose |
|-----|---------|---------|
| `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED` | `false` | Master switch |
| `SPAM_RULE_<ID>_ENABLED` | per rule | Enable/disable individual rules |
| `SPAM_RULE_<ID>_THRESHOLD` | see §4.3 | Trigger threshold |
| `SPAM_RULE_<ID>_WINDOW_SECONDS` | see §4.3 | Indicator window |
| `SPAM_RULE_<ID>_ACTION` | see §4.3 | Containment action |
| `SPAM_CONTAINMENT_THROTTLE_TTL_SECONDS` | `300` | Throttle TTL |
| `SPAM_CONTAINMENT_BLOCK_TTL_SECONDS` | `900` | Block TTL |

Depends on E3.5 remaining **off** until E3.5d Postgres concurrency test passes — E3.6 should not enable in production until **both** E3.5d and E3.6 staging validation pass.

---

## 9. Implementation slices (after approval)

| Slice | Work |
|-------|------|
| **E3.6a** | Models, migrations `0019`–`0021`, `SpamPolicy`, `SpamIndicatorService` (bucket math) |
| **E3.6b** | `SpamProtectionService`, webhook wiring post-E3.5, exceptions + 403/429 routes, feature flag |
| **E3.6c** | Observability routes, schemas, adapter metric extension, spec updates, E2 verifier route list |

**Services (proposed):**

- `SpamPolicy` — rule config from env
- `SpamProtectionService` — evaluate, increment, contain, audit
- Integration in `WebhookMessageService` only (orchestration layer)

---

## 10. Required validation (acceptance tests)

1. Repeated payload (same hash) triggers rule after threshold
2. Conversation burst triggers `mark_suspicious` without blocking (default config)
3. Adapter-scoped containment does not affect peer adapter
4. `temporary_block` expires after TTL; subsequent request allowed
5. Decision rows contain no message text / secrets
6. Tenant/business query isolation on list APIs
7. Duplicate inbound skips spam increment and containment
8. Regression: E3.1–E3.5 + E2 observability verifier green
9. **Follow-up (recommended):** Postgres concurrency test for `spam_indicator_buckets` (mirror E3.5d)

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| False positives on legitimate repeat questions | Default `mark_suspicious` before `throttle`; env tuning; short TTL |
| Overlap with E3.5 conversation limit | Different thresholds/windows; spam = behavioral, rate = capacity |
| DB write amplification | 1–2 bucket upserts per request; indexed; flag default off |
| Derived retry rules under-count races | Use for adapter block only with high thresholds |
| Storing payload hash | Still fingerprint — document; no reversible text in spam tables |
| Ops complexity (two flags: rate + spam) | Document evaluation order; separate observability endpoints |

---

## 12. Rollback plan

1. Set `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED=false`.
2. Deploy backend without webhook integration (code rollback).
3. Tables may remain; runtime inert when disabled.
4. Clear active containments: `UPDATE spam_containments SET released_at = now() WHERE released_at IS NULL` (ops runbook).

---

## 13. Approval checklist

- [ ] Three-table approach approved (`spam_indicator_buckets`, `spam_containments`, `spam_decisions`)
- [ ] No separate `spam_events` table (merged into decisions) acceptable
- [ ] Rule set + default thresholds acceptable
- [ ] Containment actions + TTL defaults acceptable
- [ ] No tenant-wide auto-block acceptable
- [ ] Placement after E3.5 rate limit acceptable
- [ ] `GET /observability/spam-decisions` + `/spam-containments` acceptable
- [ ] Feature flag default **off** acceptable
- [ ] Reject-only (no queues) acceptable

**After approval:** implement E3.6a → E3.6b → E3.6c; reviewer pass; stop for human review (no commit unless asked).

---

## 14. Related documents

- E3.5 rate limiting: [`e3-5-rate-limiting-design.md`](e3-5-rate-limiting-design.md)
- E3.5d Postgres concurrency gate: [`../../tasks/todo/T-e3.5d-postgres-concurrency-validation.md`](../../tasks/todo/T-e3.5d-postgres-concurrency-validation.md)
- Incoming flow: [`../../specs/flows/incoming-message-flow.md`](../../specs/flows/incoming-message-flow.md)
