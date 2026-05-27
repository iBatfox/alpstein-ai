# Phase D4.4 — Production safety audit (observability)

**Date:** 2026-05-27  
**Branch:** `stabilization/runtime-baseline` (`13eb37b` metadata JSON-safe, `5a45478` D2)  
**Phase:** D4.4 — Production safety audit (verification / code review only)  
**Contracts:** [`specs/architecture/observability-metadata.md`](../../specs/architecture/observability-metadata.md) §3.4, §16  
**Prior audits:** D3 harness, D4.1 (host stale), D4.2 compose E2E, D4.3 DB replay

---

## Verdict

| Result | **PASS WITH NOTES** |
|--------|---------------------|
| **Summary** | **Observability envelope paths** (`prompt_runs.metadata`, Langfuse **flat metadata**, structured webhook logs) are **production-safe by design** and match D1/D2 §16. **Residual risks** are explicit and mostly **opt-in** (production Langfuse enablement) or **outside the metadata envelope** (`final_prompt` column, Langfuse generation I/O, `messages.raw_payload`). No D1/D2 contract contradiction found in code. |

---

## Audit scope

| Area | In scope | Method |
|------|----------|--------|
| `prompt_runs.metadata` | yes | Code + D4.3 DB sample + `prompt_run_service.py` |
| Langfuse flat metadata | yes | `observability.py`, tests, D4.1/D4.3 notes |
| Langfuse span/generation **input/output** | yes (residual) | `langfuse_tracing_service.py` |
| Structured logs | yes | `webhook.py`, `observability_context.py`, compose log sample |
| `final_prompt` / `result` / `error` columns | yes (related persistence) | `prompt_run_service.py` |
| Operator context isolation | yes | envelope + webhook response + PromptBuilder path |
| Environment gating | yes | `config.py`, `_langfuse_allows_sensitive_text_metadata` |
| Replay SQL safety | yes | D4.3 snippets + guidance |
| Failure-path DB rows | skip | No `error IS NOT NULL` rows; unit tests only |
| n8n / CRM / metrics / K8s | no | Out of phase |

---

## Files reviewed

| File | Focus |
|------|--------|
| `specs/architecture/observability-metadata.md` | §3.4 exclusions, §16 defaults |
| `backend/app/services/prompt_run_service.py` | Redaction, `json_safe_metadata`, `final_prompt` |
| `backend/app/schemas/observability.py` | Envelope, Langfuse gating, metadata cap |
| `backend/app/services/langfuse_tracing_service.py` | Trace shape, generation I/O |
| `backend/app/core/config.py` | `langfuse_tracing_active` |
| `backend/app/core/observability_context.py` | Log filter |
| `backend/app/api/routes/webhook.py` | Request logging |
| `backend/app/schemas/webhook_response.py` | Forbidden response fields |
| `backend/tests/test_observability.py` | Production metadata policy tests |
| `backend/tests/test_langfuse_tracing_service.py` | Production trace metadata test |
| `backend/tests/test_prompt_run_service.py` | Secret redaction on prompt/result/error |
| `docs/audits/d3-runtime-trace-validation-2026-05-27.md` | Harness |
| `docs/audits/d4-1-live-trace-validation-2026-05-27.md` | Stale ingress risk |
| `docs/audits/d4-3-db-replay-verification-2026-05-27.md` | Compose metadata evidence |

---

## Runtime reviewed

| Runtime | Used for D4.4 |
|---------|----------------|
| **Code review** | Primary evidence |
| **Compose** `alpstein_backend` | Log sample (`docker logs`, last 30m) — no `sk-`/`Bearer` pattern hits |
| **D4.3 DB row** | `ce6de969-…` metadata (development compose) — scalar lineage, no forbidden keys |
| **Host `:8010` uvicorn** | **Not re-audited live** — D4.1 showed pre-D2 behavior; treat as **ops hazard** |
| **Production/staging deploy** | Not accessed |

---

## 1. `prompt_runs.metadata` safety

### Design (code)

| Control | Implementation |
|---------|----------------|
| No full prompt in metadata | `ObservabilityContext._scalar_dict()` **excludes** `operator_business_context_preview`; no `assembled_prompt` field on envelope |
| JSON-safe types | `json_safe_metadata()` — UUID/datetime → string |
| Secret patterns in string values | `_redact_metadata()` → `_redact_secrets()` (`sk-…`, `Bearer …`, `api_key=`, `OPENAI_API_KEY=`) |
| Size cap | `_fit_prompt_run_metadata()` — 4096 bytes, drops optional keys |

### Checklist (envelope metadata)

| Risk | Status | Notes |
|------|--------|-------|
| OPENAI_API_KEY | **PASS** | Not in envelope; redaction if embedded in strings |
| Webhook / auth tokens | **PASS** | Not in envelope |
| Raw secrets in metadata | **PASS** | Patterns + D4.3 `sk_pattern` false |
| Full operator business context | **PASS** | Preview excluded from `_scalar_dict` |
| `assembled_prompt` text | **PASS** | Not in metadata path |
| Stack traces in metadata | **PASS** | `error_code` scalar only; traces not stored in metadata |
| Raw provider payload dumps | **PASS** | Not in envelope |
| Raw UUID objects in JSONB | **PASS** | U1 `json_safe_metadata` |

### D4.3 operational sample (compose, development)

Observed keys: `correlation_id`, `conversation_id`, `assembled_section_ids`, `n8n_execution_id`, `template_key`, etc. — **no** `assembled_prompt`, `operator_business_context`, `final_prompt`.

### Related column: `prompt_runs.final_prompt` (not metadata)

| Classification | **IMPORTANT** |
|----------------|---------------|
| Behavior | Full assembled prompt stored (secret-redacted, max 16k chars) per T11.10 |
| Production impact | DB readers see tenant context, history, customer turn content — **by design**, not observability-metadata |
| Ops guidance | Replay SQL on `metadata` does **not** dump `final_prompt`; restrict DB role access |

---

## 2. Langfuse metadata safety

### Flat metadata (`to_langfuse_metadata`)

| Environment | `operator_business_context` text | `assembled_prompt` text |
|-------------|----------------------------------|-------------------------|
| `development` / `dev` / `local` / `test` + tracing on | Allowed (truncated) | Allowed (truncated 24k) |
| `production` / `staging` + tracing on | **Omitted** | **Omitted** |
| Tracing off | N/A (no export) | N/A |

Gate: `_langfuse_allows_sensitive_text_metadata()` requires **both** `langfuse_tracing_active()` **and** dev environment set.

**Tests:** `test_production_langfuse_metadata_excludes_sensitive_text_previews`, `test_trace_ai_reply_production_metadata_excludes_sensitive_text`.

### Scalar lineage in production metadata (when tracing explicitly on)

Preserved: `correlation_id`, `conversation_id`, `channel`, `greeting_mode`, CIP intent keys, `operator_business_context_present`, `n8n_execution_id`, etc.

### Residual: Langfuse observation I/O (outside flat metadata)

| Classification | **IMPORTANT** |
|----------------|---------------|
| Finding | `openai_chat_completion` generation records **`input.messages`** = full OpenAI request (all prompt sections). **`output`** = model text or error dict. |
| Contract | D1 §16.2 governs **metadata** keys; generation I/O predates D4 gating |
| When it matters | Only if `LANGFUSE_TRACING_ENABLED=true` in production/staging **with keys set** |
| Default production | Tracing **off** (`environment=production`, flag false) → **no Langfuse export** |
| Recommendation | Do not enable production Langfuse without acceptance of generation I/O exposure; or future hardening task (out of D4.4) |

### Span `input` (Langfuse)

`customer_message` truncated to **500** chars — aligns with D1 §3.4 preview limit pattern.

---

## 3. Structured log safety

### Webhook ingress (`webhook.py`)

```text
logger.info("webhook message received", extra={
  "correlation_id", "business_external_id", "channel"
})
```

| Check | Status |
|-------|--------|
| Auth header / token logged | **PASS** — not logged |
| Full JSON body logged | **PASS** — not logged |
| `message.text` logged | **PASS** — not logged |
| `correlation_id` present | **PASS** |

### Global filter (`CorrelationIdLogFilter`)

Attaches `correlation_id` to log records during webhook handling; does not add payloads.

### Langfuse errors (`langfuse_tracing_service.py`)

`logger.exception(..., extra={"correlation_id": ...})` — may emit **stack traces to application logs** (stderr/compose logs), not to `prompt_runs.metadata`.

| Classification | **OPTIONAL** |
|----------------|--------------|
| Risk | Log aggregators may capture exception stacks; typically no API keys unless embedded in exception message |
| Mitigation | Log retention policy; avoid enabling debug logging of HTTP clients |

### Compose log sample (30m)

`docker logs alpstein_backend` — grep for `sk-`, `Bearer`, `api_key`, `token`, `password`: **no matches**.

**Gap:** Production access/uvicorn access logs (if any) not reviewed — depends on reverse proxy config.

---

## 4. Environment gating

### Tracing enablement (`langfuse_tracing_active`)

| Condition | Tracing |
|-----------|---------|
| Missing Langfuse keys | **Off** |
| `LANGFUSE_TRACING_ENABLED=true` | **On** (any environment) |
| Else `environment` in `{development, dev, local, test}` | **On** if keys set |
| `production` / `staging` without flag | **Off** |

Matches §16.6 — **explainable and documented**.

### Sensitive text in Langfuse metadata

Requires dev environment **even if** tracing enabled — `staging` does not receive `assembled_prompt` / operator text in metadata.

### Default settings footgun

`Settings.environment` defaults to **`production`** in code if unset — safe default for tracing (off).

---

## 5. Operator context isolation

| Path | Operator text exposed? |
|------|------------------------|
| Webhook HTTP response | **No** — `FORBIDDEN_WEBHOOK_RESPONSE_FIELDS` includes `operator_business_context` |
| `prompt_runs.metadata` | **No** — preview excluded |
| Langfuse metadata (production) | **No** — boolean `operator_business_context_present` only |
| Langfuse metadata (dev) | Truncated preview (≤4000 chars) |
| `prompt_runs.final_prompt` | **Yes** — if operator overlay merged into assembled prompt (PromptBuilder) |
| Langfuse generation `input` (dev / prod tracing on) | **Yes** — via prompt sections |
| Customer `messages.message_text` | Stores customer text (MVP data model) |

---

## 6. Webhook payload persistence safety

| Store | Content | Observability audit |
|-------|---------|---------------------|
| `messages.message_text` | Customer message | Expected PII; not part of observability envelope |
| `messages.raw_payload` | Optional provider blob from n8n | **IMPORTANT** — can contain provider tokens if n8n forwards them; §3.4 excludes from traces; **not redacted in column** |
| `messages.ai_metadata` | `prompt_run_id`, model, provider | Scalar; no secrets |
| Webhook response | Business summaries only | Forbidden list enforced |

---

## 7. Replay / query operational safety

D4.3 SQL targets `prompt_runs.metadata` and relational joins — **appropriate** for incident replay without pulling `final_prompt` by default.

| Classification | **IMPORTANT** |
|----------------|---------------|
| Ops risk | `SELECT metadata` / `SELECT final_prompt` / `SELECT raw_payload` have different sensitivity |
| Recommendation | Document in runbook: use metadata-first replay; restrict roles on `prompt_runs.final_prompt` and `messages.raw_payload` |

Suggested safe operator query (metadata keys only):

```sql
SELECT id, created_at,
       metadata->>'correlation_id' AS correlation_id,
       metadata->>'conversation_id' AS conversation_id,
       metadata->>'channel' AS channel,
       metadata->>'n8n_execution_id' AS n8n_execution_id
FROM prompt_runs
WHERE metadata->>'correlation_id' = '<uuid>';
```

Avoid pasting full `metadata` or `final_prompt` into tickets without redaction review.

---

## 8. Failure-path persistence

| Status | **SKIP** (live DB) |
|--------|---------------------|
| Reason | `SELECT … WHERE error IS NOT NULL` returned 0 rows on compose DB (same as D4.3) |
| Code expectation | `error` passed through `_redact_secrets()`; no stack requirement in spec (`error_code` in metadata) |
| Tests | `test_create_prompt_run_failure`, `test_create_prompt_run_redacts_secrets_in_result_and_error` |

---

## Contract alignment (D1 / D2)

| Contract rule | Code / evidence | Conflict? |
|---------------|-----------------|-----------|
| §3.4 exclusions in metadata/logs | Enforced for metadata path | **No** |
| §16.2 prod: no operator/prompt text in Langfuse **metadata** | Gated | **No** |
| §16.3 scalar metadata only | `_scalar_dict` + cap | **No** |
| §16.6 prod tracing off by default | `langfuse_tracing_active` | **No** |
| Generation I/O in Langfuse | Full messages when tracing on | **Gap** vs strict “no prompt leakage” interpretation — **not** a metadata-key violation |

**STOP condition:** No spec redesign required; document generation I/O as residual operational risk.

---

## Findings classification

### CRITICAL

| ID | Finding | Risk |
|----|---------|------|
| — | *None in compose/D2 code paths for observability metadata* | — |
| **OPS-C1** | **Dual ingress**: host `:8010` may run **pre-D2** binary (D4.1) while compose has correct behavior | Operators think CIP-C is live globally; metadata null / no validation on wrong port |

### IMPORTANT

| ID | Finding | Risk |
|----|---------|------|
| **I1** | Langfuse **generation input/output** contains full prompt + reply when tracing enabled in production | Explicit opt-in via `LANGFUSE_TRACING_ENABLED` |
| **I2** | `prompt_runs.final_prompt` stores full assembled prompt (redacted, 16k) | DB access = high sensitivity |
| **I3** | `messages.raw_payload` may hold provider secrets | n8n normalization responsibility |
| **I4** | Failure-path persistence not live-verified | Rely on unit tests |
| **I5** | `staging` + `LANGFUSE_TRACING_ENABLED=true` → tracing on, metadata text suppressed but generation I/O still full | Rare config mistake |

### OPTIONAL

| ID | Finding | Risk |
|----|---------|------|
| **O1** | `logger.exception` on Langfuse failures may log stacks | Low secret risk |
| **O2** | `attribution_summary` in metadata may include UTM strings | Low |
| **O3** | Access/proxy logs not audited | Environment-dependent |
| **O4** | No automated scan that production metadata never contains `assembled_prompt` key in CI against live DB | Process gap |

---

## Pass / fail checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Metadata production-safe (no secrets, no full prompt/operator text) | **PASS** |
| 2 | Langfuse flat metadata respects §16.2 | **PASS** (code + tests) |
| 3 | Logs useful without leaking secrets (app code) | **PASS** |
| 4 | Environment gating explainable | **PASS** |
| 5 | Replay useful without mandatory secret dump | **PASS** (metadata-first) |
| 6 | No obvious metadata secret leakage path | **PASS** |
| 7 | Residual risks documented | **PASS** |
| 8 | Production Langfuse off by default | **PASS** |
| 9 | Full production safety including DB columns + generation I/O | **PASS WITH NOTES** |
| 10 | Wrong ingress / stale process | **FAIL** (operational — OPS-C1) |

---

## Operational recommendations

| Priority | Action |
|----------|--------|
| P0 | **Single ingress policy**: compose or restarted host binary at `5a45478+`; retire/stop stale `:8010` process |
| P1 | **Production Langfuse**: keep `LANGFUSE_TRACING_ENABLED` unset/false unless leadership accepts generation I/O exposure |
| P1 | **DB RBAC**: limit `SELECT final_prompt`, `raw_payload` to break-glass roles |
| P2 | Runbook: metadata-first replay (D4.3 SQL); warn on `final_prompt` |
| P2 | Optional disposable failure drill for `error` column redaction |
| P3 | Proxy/access log review for header leakage |
| P3 | Future task (out of scope): redact or omit generation `input` when `environment=production` |

---

## Unresolved concerns

1. No live **production** environment audit (only code + development compose evidence).
2. Failure-path DB rows not observed.
3. Langfuse generation I/O policy not in D1 §16 — organizational acceptance required if prod tracing is ever enabled.
4. `raw_payload` hygiene depends on n8n normalization (not D4.4 scope).

---

## Related

- [`d4-3-db-replay-verification-2026-05-27.md`](d4-3-db-replay-verification-2026-05-27.md)
- [`d4-1-live-trace-validation-2026-05-27.md`](d4-1-live-trace-validation-2026-05-27.md)
- [`docs/architecture/langfuse-tracing.md`](../architecture/langfuse-tracing.md)

---

**Report status:** Draft for human review — **not committed** per phase instructions.
