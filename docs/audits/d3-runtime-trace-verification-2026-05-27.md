# Phase D3 — Runtime trace verification report

**Date:** 2026-05-27  
**Branch:** `stabilization/runtime-baseline`  
**Scope:** CIP-C observability runtime verification only (no new features)  
**Canonical contract:** [`specs/architecture/observability-metadata.md`](../../specs/architecture/observability-metadata.md) §16  
**Verifier:** alpstein-reviewer (automated harness + targeted pytest)

---

## Executive summary

| Verdict | **APPROVED WITH NOTES** |
|---------|-------------------------|
| **Confidence** | High for **in-process / ASGI runtime** behavior; **not** for live Langfuse SaaS export or full Docker compose E2E on this host |

D2 observability wiring behaves correctly under runtime-style execution (FastAPI ASGI, `ObservabilityContext`, mocked Langfuse client). **13/13** harness checks passed; **2** skipped (readiness without DB, live Langfuse cloud). Targeted pytest: **20 passed**.

**D3 is not BLOCKED** for engineering acceptance of CIP-C wiring, but **operator sign-off** still requires one dev-environment webhook + Langfuse UI check when keys are configured.

---

## Commands used

```bash
# 1) Backend venv + dependencies
cd /opt/alpstein-ai/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest pytest-anyio httpx

# 2) D3 harness (ASGI + mock Langfuse + log filter)
.venv/bin/python ../scripts/verify/d3_runtime_trace_verification.py

# 3) Targeted pytest (observability + route + orchestration metadata)
.venv/bin/python -m pytest \
  tests/test_observability.py \
  tests/test_langfuse_tracing_service.py \
  tests/test_webhook_message_route.py::test_webhook_message_passes_correlation_id_to_service \
  tests/test_webhook_message_route.py::test_webhook_message_invalid_correlation_id_returns_validation_error \
  tests/test_ai_reply_orchestration_service.py::test_generate_reply_gateway_success_creates_successful_prompt_run \
  -q --tb=short

# 4) Optional compose (attempted on gate host — partial)
export POSTGRES_PASSWORD='<set in .env>'
docker-compose -p alpstein-ai -f docker-compose.yml -f docker-compose.dev.yml up -d postgres
docker-compose -p alpstein-ai build backend
# backend up failed: 127.0.0.1:8000 already in use (foreign uvicorn)
```

**Harness script (repeatable):** [`scripts/verify/d3_runtime_trace_verification.py`](../../scripts/verify/d3_runtime_trace_verification.py)

---

## Verification checklist

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Backend starts cleanly | **PASS** (import + ASGI) / **SKIP** (compose) | `app.main` import; liveness 200 in harness; compose backend blocked by host `:8000` conflict |
| 2 | Webhook accepts valid `X-Correlation-Id` | **PASS** | D3-02; pytest route test |
| 3 | Generates `correlation_id` when missing | **PASS** | D3-03 |
| 4 | Invalid `X-Correlation-Id` → `VALIDATION_ERROR` | **PASS** | D3-04; HTTP 400, service not called |
| 5 | `X-N8n-Execution-Id` captured | **PASS** | D3-05 → `ObservabilityContext.n8n_execution_id` |
| 6a | `correlation_id` in logs | **PASS** | D3-06a `CorrelationIdLogFilter` |
| 6b | `correlation_id` in `ObservabilityContext` | **PASS** | D3-02/03 webhook kwargs |
| 6c | `correlation_id` in Langfuse span metadata | **PASS** | D3-06b mock span metadata |
| 6d | `correlation_id` in `prompt_runs.metadata` | **PASS** (builder) | D3-06c; pytest orchestration `create_prompt_run` kwargs |
| 6e | DB row `prompt_runs.metadata` after real insert | **NOT RUN** | No live Postgres webhook E2E in this session |
| 7 | `conversation_id` = Langfuse `session_id` | **PASS** | D3-07 `propagate_attributes(session_id=...)` |
| 8 | `prompt_run_id` in trace metadata post-create | **PASS** | D3-08 `update_trace_metadata` on span |
| 9 | CIP intent fields in Langfuse metadata | **PASS** | D3-06b `conversation_intent`, `intent_matched_rule`, `intent_used_previous_message` |
| 10a | Production: no `assembled_prompt` in metadata | **PASS** | D3-10; pytest production tests |
| 10b | Production: no `operator_business_context` text | **PASS** | D3-10 |
| 10c | Production: scalar lineage remains | **PASS** | `correlation_id`, `operator_business_context_present` |
| 11 | Error-path traceability | **PASS** | D3-11 invalid correlation; D3-04 HTTP path |
| 12 | Duplicate/retry lineage | **PASS** (semantic) | D3-12 new correlation per attempt + `is_duplicate` |
| — | Live Langfuse cloud trace | **SKIP** | D3-09-live — mock client only; keys present in `.env` but no export verified |

---

## Harness output (summary)

```json
{
  "summary": { "passed": 13, "failed": 0, "skipped": 2, "total": 15 }
}
```

Readiness without database: **SKIP** (`liveness=200`, `readiness=503` in ASGI harness).

---

## Screenshots / trace IDs

| Item | Value |
|------|--------|
| Langfuse UI trace | **Not captured** — mock Langfuse only |
| Sample `correlation_id` (harness) | e.g. `3a3ddfe9-fa71-4d0c-af63-ef0f94939ca8` (ephemeral per run) |
| Sample `session_id` | `conversation_id` UUID passed to `propagate_attributes` |

---

## Gaps found

| Gap | Severity | Notes |
|-----|----------|-------|
| No live Langfuse export verified | **Important** | Mock proves metadata shape; SaaS UI confirmation still operator task |
| No DB readback of `prompt_runs.metadata` JSONB | **Important** | `create_prompt_run(metadata=...)` verified in unit tests; column not read after INSERT on live DB |
| Docker compose full stack not completed on gate host | **Important** | `127.0.0.1:8000` in use by unrelated uvicorn; `docker-compose up backend` also hit `ContainerConfig` KeyError |
| Generation observation still sends full OpenAI `messages` in **input** when tracing on | **Suggestion** | Flat metadata policy passes; generation I/O is pre-existing (D2 scope) |
| Invalid body `correlation_id` → FastAPI **422** vs header **400** | **Suggestion** | Documented in D1/D2 review; not re-tested here |

---

## Recommended follow-up tasks

| ID | Task | Owner |
|----|------|--------|
| **D3-OPS-1** | Dev/staging: one real `POST /api/v1/webhook/message` with `X-Correlation-Id` + Langfuse keys; confirm trace in UI filtered by `correlation_id` | Operator |
| **D3-OPS-2** | SQL spot-check: `SELECT metadata->>'correlation_id' FROM prompt_runs ORDER BY created_at DESC LIMIT 5;` after webhook | Operator |
| **D3** (planned) | n8n pass `X-Correlation-Id` / `X-N8n-Execution-Id` on workflows | n8n-integration-engineer |
| **D4** | ATTR-3 persistence (`messages.metadata`) | backend-engineer |
| **D3-HARDEN** | Optional: redact generation `input` when `environment=production` and tracing enabled | backend-engineer (if prod tracing used) |

---

## Phase D3 verdict

| Decision | **APPROVED WITH NOTES** |
|----------|-------------------------|
| **Blockers** | None for code-level CIP-C runtime wiring |
| **Conditions** | Complete D3-OPS-1/2 before calling observability “production-operational”; do not treat Langfuse as ops-ready without UI smoke |

---

## Related

- D2 task: [`tasks/done/T-d2-langfuse-runtime-metadata-wiring.md`](../../tasks/done/T-d2-langfuse-runtime-metadata-wiring.md)
- D1 contract: [`specs/architecture/observability-metadata.md`](../../specs/architecture/observability-metadata.md)
- Supplement: [`docs/architecture/langfuse-tracing.md`](../architecture/langfuse-tracing.md)
