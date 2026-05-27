# Phase D4.3 — DB replay verification report

**Date:** 2026-05-27  
**Branch:** `stabilization/runtime-baseline` (includes `13eb37b` JSON-safe `prompt_runs.metadata`, D2 `5a45478`)  
**Phase:** D4.3 — DB replay verification (operational only)  
**Contracts:** [`observability-metadata.md`](../../specs/architecture/observability-metadata.md) §16, D2, U1 fix `json_safe_metadata`  
**Prior:** [`d4-1-live-trace-validation-2026-05-27.md`](d4-1-live-trace-validation-2026-05-27.md) (host `:8010` stale), D4.2 compose E2E

---

## Verdict

| Result | **PASS WITH NOTES** |
|--------|---------------------|
| **Summary** | On **compose backend** (`alpstein_backend`), `prompt_runs.metadata` persists as **JSON-safe scalar lineage**; full replay from `correlation_id` works; duplicate/retry behavior matches D1 semantics. **Failure-path webhook verification skipped** (no safe live trigger; no `error` rows in DB). **Host `:8010` process not used** (still pre-D2 per D4.1). |

---

## Execution environment

| Item | Value |
|------|--------|
| Ingress used | **Docker compose** `alpstein_backend` → `http://127.0.0.1:8000` **inside container** (`docker exec … httpx`) |
| Postgres | `alpstein_postgres` / DB `alpstein_ai` |
| Readiness | `200` inside container (`/api/v1/health/ready`, `db: reachable`) |
| Image / commit context | Branch at `b554908`; U1 fix `13eb37b` `json_safe_metadata` in `prompt_run_service.py` |
| Business | `demo_barbershop_001` (seeded) |
| Environment | `development` |
| **Not used** | Host uvicorn `:8010` (PID from 2026-05-26 — D4.1 stale; would not meet D4.3 criteria) |

---

## Commands used

```bash
# Health (inside compose backend)
docker exec alpstein_backend python -c \
  "import httpx; r=httpx.get('http://127.0.0.1:8000/api/v1/health/ready',timeout=5); print(r.status_code, r.text[:120])"

# Webhooks (token from container env — not logged)
docker exec alpstein_backend python -c '<httpx POST script>'   # see payloads below

# DB queries
docker exec alpstein_postgres psql -U alpstein -d alpstein_ai -c '...'

# Metadata JSON type check (host pipes psql → python3)
docker exec alpstein_postgres psql -U alpstein -d alpstein_ai -t -A \
  -c "SELECT metadata::text FROM prompt_runs WHERE id = '...';" | python3 -c '...'
```

---

## Webhook payloads used

### 1) Success (primary replay anchor)

| Field | Value |
|-------|--------|
| `X-Correlation-Id` | `b618921d-1925-4e00-997e-c0c4ef63ca32` |
| `X-N8n-Execution-Id` | `n8n-d43-success` |
| `external_message_id` | `d43-success-1779923283` |
| `customer.phone` | `+4179d43001` |
| `channel` | `test` |
| `message.text` | `D4.3 DB replay success` |

**Response:** HTTP `200`, `is_duplicate: false`

| Entity | ID |
|--------|-----|
| `conversation_id` | `e9774264-2167-4c9b-8496-8ae4b0a5b090` |
| inbound `message_id` | `e2d534b8-b211-43c2-a178-a0305e25ec27` |
| `prompt_run_id` | `ce6de969-3e01-4b52-aacd-3676d1959df0` |
| outbound `message_id` | `f0161a3a-b2c3-4066-864c-261c5b5a1835` |

### 2) Duplicate (same `external_message_id`)

| Field | Value |
|-------|--------|
| `X-Correlation-Id` | `47cdd557-7312-47f0-a95a-7c1a70bf5901` (new per HTTP attempt) |
| `external_message_id` | `d43-success-1779923283` (same as #1) |

**Response:** HTTP `200`, `is_duplicate: true`, **same** `message_id` `e2d534b8-…`

### 3) Retry (new `external_message_id`, same customer)

| Field | Value |
|-------|--------|
| `X-Correlation-Id` | `4ebfeab9-ce34-4470-bbb2-dba7bef6eb28` |
| `X-N8n-Execution-Id` | `n8n-d43-retry` |
| `external_message_id` | `d43-retry-1779923317` |

**Response:** HTTP `200`, `is_duplicate: false`, **same** `conversation_id`, **new** `message_id` `302de830-…`

### Control: invalid correlation

`X-Correlation-Id: not-a-uuid` → **HTTP 400** `VALIDATION_ERROR` (compose backend).

---

## Observed `prompt_runs` row (success)

| Column | Value |
|--------|--------|
| `id` | `ce6de969-3e01-4b52-aacd-3676d1959df0` |
| `tenant_id` | `11111111-1111-4111-8111-111111111111` |
| `business_id` | `22222222-2222-4222-8222-222222222222` |
| `conversation_id` | `e9774264-2167-4c9b-8496-8ae4b0a5b090` |
| `message_id` | `e2d534b8-b211-43c2-a178-a0305e25ec27` |
| `prompt_template_id` | `41a7dd32-7587-43f2-82e7-49135a965e0a` |
| `prompt_version` | `1` |
| `model` | `gpt-4o-mini-2024-07-18` |
| `provider` | `openai` |
| `input_tokens` | `638` |
| `output_tokens` | `66` |
| `latency_ms` | `3454` |
| `result` | present (success) |
| `error` | `null` |

---

## `prompt_runs.metadata` verification

**Storage:** JSONB `object`; **not null** after U1 fix.

**Sample keys (success run):**

| Key | Example value | Notes |
|-----|---------------|--------|
| `obs_schema_version` | `"1.0"` | string |
| `correlation_id` | `b618921d-1925-4e00-997e-c0c4ef63ca32` | **string** (not UUID object) |
| `conversation_id` | `e9774264-…` | string |
| `inbound_message_id` | `e2d534b8-…` | string |
| `n8n_execution_id` | `n8n-d43-success` | string |
| `business_external_id` | `demo_barbershop_001` | string |
| `template_key` | `customer_reply_v1` | string |
| `prompt_template_id` | `41a7dd32-…` | string |
| `prompt_version` | `1` | string |
| `assembled_section_ids` | JSON array of strings | section ids only |
| `is_duplicate` | `false` | boolean |
| `gateway_model` / `gateway_provider` / `ai_success` | present | scalars |

**Confirmed absent from metadata:**

- `assembled_prompt`, `operator_business_context`, `final_prompt`
- Secret patterns (`sk-…` scan negative)
- Raw UUID Python repr (`UUID(` negative)

**JSON scalar type audit:** all metadata values are JSON scalars/arrays/objects of scalars — **PASS**.

**Note:** `environment` and `prompt_run_id` are **not** duplicated inside metadata (D1 optional; row `id` is the prompt run PK). `request_id` / `trace_id` not in envelope — N/A.

---

## Replay reconstruction (from `correlation_id`)

**Anchor:** `b618921d-1925-4e00-997e-c0c4ef63ca32`

| Step | Entity | ID / detail |
|------|--------|-------------|
| prompt_run | `prompt_runs` | `ce6de969-3e01-4b52-aacd-3676d1959df0` |
| inbound message | `messages` | `e2d534b8-…` / `external_message_id` `d43-success-1779923283` |
| outbound AI | `messages` | `f0161a3a-…` / `ai_metadata.prompt_run_id` = `ce6de969-…` |
| conversation | `conversations` | `e9774264-…` / `open` |
| customer | `customers` | `6d9b9e22-…` / phone `+4179d43001` |

**Conclusion:** At least one successful webhook execution is **fully reconstructable from DB** using `metadata->>'correlation_id'`.

---

## Duplicate / retry verification

| Scenario | prompt_runs count | Messages (inbound) | Notes |
|----------|-------------------|--------------------|-------|
| After success + duplicate + retry | **2** on conversation | **2** inbound rows | Duplicate did **not** add prompt_run |
| Duplicate correlation `47cdd557-…` | **0** rows | — | No DB row for duplicate HTTP attempt |
| Retry correlation `4ebfeab9-…` | **1** row (`30c00a30-…`) | new inbound `302de830-…` | New lineage, same conversation |

| Check | Status |
|-------|--------|
| Duplicate detected | **PASS** (`is_duplicate: true`) |
| No second prompt_run on duplicate | **PASS** (count stays 2) |
| No second inbound message on duplicate | **PASS** (same `message_id`) |
| Retry creates new prompt_run + correlation | **PASS** |
| Same conversation/customer on retry | **PASS** |

Aligns with D1: new `correlation_id` per HTTP attempt; `is_duplicate` on metadata for first success only.

---

## Failure-path persistence

| Status | **SKIP** |
|--------|----------|
| Reason | No safe live webhook mechanism to force gateway failure without changing container `OPENAI_API_KEY` or orchestration code. Query `SELECT … FROM prompt_runs WHERE error IS NOT NULL` returned **0** rows. |
| Indirect confidence | Unit tests: `test_generate_reply_gateway_failure_creates_failure_prompt_run`, `test_create_prompt_run_failure` (not re-run in this audit). |
| Re-test option | Operator-only: temporary invalid key in **disposable** compose env, one webhook, restore key. |

---

## Operator SQL snippets

```sql
-- 1) Find prompt_run by correlation_id
SELECT id, message_id, conversation_id, model, provider, latency_ms,
       metadata
FROM prompt_runs
WHERE metadata->>'correlation_id' = '<correlation-uuid>';

-- 2) Conversation + customer for that run
SELECT c.id, c.status, cu.phone, cu.id AS customer_id
FROM prompt_runs pr
JOIN conversations c ON c.id = pr.conversation_id
JOIN customers cu ON cu.id = c.customer_id
WHERE pr.metadata->>'correlation_id' = '<correlation-uuid>';

-- 3) All messages for conversation (chronological)
SELECT direction, id, external_message_id, created_at,
       ai_metadata->>'prompt_run_id' AS prompt_run_id
FROM messages
WHERE conversation_id = '<conversation-uuid>'
ORDER BY created_at;

-- 4) Duplicate external_message_id probe
SELECT id, external_message_id, conversation_id, created_at
FROM messages
WHERE business_id = '<business-uuid>'
  AND external_message_id = '<external-id>'
ORDER BY created_at;

-- 5) Safe metadata inspection (keys only)
SELECT id,
       jsonb_object_keys(metadata) AS keys
FROM prompt_runs
WHERE metadata->>'correlation_id' = '<correlation-uuid>';

-- 6) List recent runs with metadata present
SELECT id, metadata->>'correlation_id' AS corr,
       metadata->>'n8n_execution_id' AS n8n_exec,
       created_at
FROM prompt_runs
WHERE metadata IS NOT NULL
ORDER BY created_at DESC
LIMIT 20;
```

Replace UUIDs from webhook response or prior query. Do not paste production tokens into tickets.

---

## Validation checklist

| # | Requirement | Status |
|---|-------------|--------|
| 1 | Real webhook execution | **PASS** (compose) |
| 2 | prompt_run columns populated | **PASS** |
| 3 | metadata JSON-safe, lineage fields | **PASS** |
| 4 | Replay from correlation_id | **PASS** |
| 5 | Duplicate: no extra PromptRun | **PASS** |
| 6 | Retry: new PromptRun + correlation | **PASS** |
| 7 | Failure path | **SKIP** (see above) |
| 8 | SQL examples provided | **PASS** |
| D1/D2 contract alignment (compose) | **PASS** |
| Host :8010 legacy ingress | **NOT VERIFIED** (known stale) |

---

## Unresolved risks

| Risk | Notes |
|------|--------|
| Ops hits host `:8010` instead of compose | Still serves **pre-D2** code (D4.1); metadata `null`, invalid correlation accepted |
| Failure path not live-proven | Rely on tests until controlled failure drill |
| `final_prompt` column | Separate from metadata; redaction policy applies to column, not audited byte-by-byte here |
| CIP intent keys | Not expected for `demo_barbershop_001`; use `alpstein_ai_demo_001` for intent metadata drill |

---

## Recommended next steps

| ID | Action |
|----|--------|
| **D4.3-R1** | Stop or restart host `:8010` uvicorn; route ops to compose or refreshed host process |
| **D4.3-R2** | Optional failure drill on disposable compose (`OPENAI_API_KEY` invalid → one webhook → restore) |
| **D4.3-R3** | Repeat metadata replay on `alpstein_ai_demo_001` for intent fields in metadata |
| **D3** | n8n `X-Correlation-Id` / `X-N8n-Execution-Id` headers |

---

## Contract conflicts

**None observed on compose backend** for D4.3 scope. D4.1 conflicts were **ingress-specific** (stale host), not contradictions in current code on the active compose deployment.

---

## Files created

| File | Purpose |
|------|---------|
| `docs/audits/d4-3-db-replay-verification-2026-05-27.md` | This report |

**Not committed** — awaiting human review per task instructions.

---

## Related

- [`d4-1-live-trace-validation-2026-05-27.md`](d4-1-live-trace-validation-2026-05-27.md)
- [`d3-runtime-trace-validation-2026-05-27.md`](d3-runtime-trace-validation-2026-05-27.md)
- Commit `13eb37b` — `fix(observability): serialize prompt run metadata for JSONB`
