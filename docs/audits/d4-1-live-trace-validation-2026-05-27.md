# Phase D4.1 — Live trace validation report

**Date:** 2026-05-27  
**Branch:** `stabilization/runtime-baseline` (HEAD `5a45478` — D2 merged)  
**Phase:** D4.1 — Live trace validation (operational only)  
**Contracts:** [`specs/architecture/observability-metadata.md`](../../specs/architecture/observability-metadata.md) §16, D2 wiring  
**Prior harness:** [`d3-runtime-trace-validation-2026-05-27.md`](d3-runtime-trace-validation-2026-05-27.md)

---

## Verdict

| Result | **BLOCKED** |
|--------|-------------|
| **Reason** | Live ingress responds, Langfuse receives a trace, but **runtime behavior does not match D1/D2** on the active process. Evidence points to a **stale long-running uvicorn** started **before** D2 landed. |

**Do not redesign semantics.** Re-run D4.1 after **restarting** the backend process from current `stabilization/runtime-baseline` (see § Operational remediation).

---

## Execution environment

| Item | Value |
|------|--------|
| Host | Gate / dev server (Linux) |
| Active backend | Host uvicorn `127.0.0.1:8010` (not portable compose) |
| Process | `uvicorn app.main:app --host 0.0.0.0 --port 8010` |
| CWD | `/opt/alpstein-ai/backend` |
| Process start | **2026-05-26 00:10:26** (local time) |
| D2 commit time | **2026-05-27 23:46:06** (`5a45478`) |
| `observability.py` mtime | **2026-05-27 23:41** |
| Environment | `ALPSTEIN_AI_ENVIRONMENT=development` (from process env) |
| Langfuse | Cloud (`LANGFUSE_BASE_URL` configured; keys present — values not recorded) |
| Postgres | Via `ALPSTEIN_AI_DATABASE_URL` (app DB reachable; queries succeeded) |
| Portable compose | Postgres container **exited**; `alpstein_backend` **Created** not running |
| Port 8000 | Unrelated app (health 404) |

**Conclusion:** Validation exercised **legacy Contabo-style host backend**, not a freshly deployed D2 image/process.

---

## Commands used

```bash
# Health
curl -s http://127.0.0.1:8010/api/v1/health
curl -s http://127.0.0.1:8010/api/v1/health/ready   # → 404 (endpoint absent on this process)

# Live webhook (token from .env — not reproduced here)
CORR=$(uuidgen)
EXT="d4-1-live-$(date +%s)"
curl -s -X POST "http://127.0.0.1:8010/api/v1/webhook/message" \
  -H "Content-Type: application/json" \
  -H "X-Alpstein-Webhook-Token: <from N8N_BACKEND_API_TOKEN>" \
  -H "X-Correlation-Id: ${CORR}" \
  -H "X-N8n-Execution-Id: d4-1-exec-test" \
  -d @- <<EOF
{
  "business_id": "demo_barbershop_001",
  "channel": "test",
  "customer": { "phone": "+4179000d411" },
  "message": {
    "text": "D4.1 live trace validation ping",
    "external_message_id": "${EXT}"
  }
}
EOF

# Invalid correlation control
curl -s -w "\nHTTP:%{http_code}" -X POST "http://127.0.0.1:8010/api/v1/webhook/message" \
  -H "X-Alpstein-Webhook-Token: <token>" \
  -H "X-Correlation-Id: not-valid" \
  -d '{"business_id":"demo_barbershop_001","channel":"test","customer":{"phone":"+4179000d412"},"message":{"text":"bad corr","external_message_id":"d4-1-bad-corr"}}'

# DB evidence (backend venv)
cd /opt/alpstein-ai/backend && .venv/bin/python -c '... query prompt_runs / messages ...'

# Langfuse public API (Basic auth pk:sk — not logged)
curl -s -u "<LANGFUSE_PUBLIC_KEY>:<LANGFUSE_SECRET_KEY>" \
  "https://cloud.langfuse.com/api/public/traces?sessionId=<conversation_uuid>&limit=5"
curl -s -u "..." "https://cloud.langfuse.com/api/public/traces/<trace_id>"
curl -s -u "..." "https://cloud.langfuse.com/api/public/observations?traceId=<trace_id>&limit=10"
```

---

## Webhook payload used (successful run)

| Field | Value |
|-------|--------|
| `business_id` | `demo_barbershop_001` |
| `channel` | `test` |
| `customer.phone` | `+4179000d411` |
| `message.text` | `D4.1 live trace validation ping` |
| `message.external_message_id` | `d4-1-live-1779920407` |
| `X-Correlation-Id` | `90807d6c-cdc9-4ff2-bafc-b4955f072104` |
| `X-N8n-Execution-Id` | `d4-1-exec-test` |

**HTTP response:** `200` — `success: true`, AI reply returned, lead + notify flags set.

| Entity | ID |
|--------|-----|
| `conversation.id` | `dd784365-3a15-4fd4-9fe9-1a6aad846cd5` |
| `message.id` (inbound) | `f4fdafb5-9ac0-4d31-8c35-742e86a146fa` |
| `lead.id` | `c944604e-3578-486c-aed0-ba2a89318792` |
| Outbound `messages.id` | `7fd4efcb-…` (from DB query) |
| `prompt_runs.id` | `d466e06f-55c3-48fb-a03a-b7282e0ba13f` |

Webhook JSON **does not** expose observability envelope (expected per D1).

---

## Trace IDs captured (Langfuse)

| Artifact | ID |
|----------|-----|
| **Trace** | `9d1037bbe099030e22a02a7cc7a0efec` |
| **Span** `ai_reply_orchestration` | `384a7d34a629ec34` |
| **Generation** `openai_chat_completion` | `ed13982ec76218ca` |
| **Langfuse `sessionId`** | `dd784365-3a15-4fd4-9fe9-1a6aad846cd5` (= `conversation_id`) |

**Screenshots:** Not captured (no browser session in verifier environment). Use trace ID above in Langfuse UI → Traces.

---

## Validation checklist

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Real webhook through active ingress | **PASS** | HTTP 200 on `:8010`, AI + DB writes |
| 2 | Langfuse trace creation | **PASS** | Trace `9d1037bbe099030e22a02a7cc7a0efec` |
| 3 | `correlation_id` continuity | **FAIL** | Sent `90807d6c-…`; **absent** from Langfuse metadata and `prompt_runs.metadata` |
| 4 | `session_id` lineage | **PASS** | `sessionId` = `dd784365-3a15-4fd4-9fe9-1a6aad846cd5` |
| 5 | `prompt_run_id` linkage | **PARTIAL** | In `messages.ai_metadata` on **outbound** row only; **not** in Langfuse span/generation metadata |
| 6 | Metadata propagation correctness | **FAIL** | `prompt_runs.metadata` is **`null`**; Langfuse missing D2 fields (`correlation_id`, `n8n_execution_id`, `obs_schema_version`, CIP intent keys) |
| 7 | Production-safe metadata policy | **N/A** (dev env) | Dev trace includes **`assembled_prompt`** (len 3654) — allowed in development per §16.2 |
| 8 | No sensitive payload leakage | **PASS** (webhook) | Response has no operator context / envelope |
| 9 | No operator/internal context leakage in trace metadata | **PASS** | No `operator_business_context` key on trace |
| 10 | Trace replayability | **PARTIAL** | Replay by `conversation_id` / `prompt_run_id` / Langfuse trace ID; **not** by `correlation_id` (missing) |
| 11 | Capture trace IDs | **PASS** | § Trace IDs |
| 12 | Screenshots | **SKIP** | Not available in environment |
| — | Invalid `X-Correlation-Id` → `VALIDATION_ERROR` | **FAIL** | `not-valid` returned **HTTP 200** (D2 §16.1 violation — strong stale-process signal) |

---

## Contract inconsistencies (D1/D2 vs live runtime)

**STOP — documented before any semantic redesign.**

| Contract (D1/D2) | Live observation | Severity |
|--------------------|------------------|----------|
| §16.1 valid `X-Correlation-Id` propagated to metadata + logs | Header accepted but **not stored** in Langfuse/DB metadata | **Critical** |
| §16.1 invalid UUID → `VALIDATION_ERROR` | **`not-valid` → 200** | **Critical** |
| §16.3 `prompt_runs.metadata` scalar envelope | Column **`null`** for run `d466e06f-…` | **Critical** |
| §16.5 `X-N8n-Execution-Id` in envelope | **Not** in Langfuse trace metadata | **Important** |
| D2 post-create `prompt_run_id` on span metadata | **Not** on observations | **Important** |
| CIP intent keys in Langfuse (demo business) | **Absent** (`demo_barbershop_001` — intent may be off by design; still no `correlation_id`) | **Important** |
| §16.2 dev-only `assembled_prompt` in metadata | Present (dev) — **consistent** with pre-D2-style tracing | OK for dev |
| Process must run D2 code | Uvicorn started **2026-05-26**; D2 committed **2026-05-27** | **Root cause hypothesis** |

**Not claimed:** D2 code is wrong — **in-process D3 harness passed** on current tree. Failure mode is **deployment drift** (long-lived process).

---

## Database evidence

```text
prompt_runs.id     = d466e06f-55c3-48fb-a03a-b7282e0ba13f
prompt_runs.metadata = null

messages (inbound)  f4fdafb5-…  ai_metadata = null
messages (outbound) 7fd4efcb-…  ai_metadata = {
  "model": "gpt-4o-mini-2024-07-18",
  "provider": "openai",
  "prompt_run_id": "d466e06f-55c3-48fb-a03a-b7282e0ba13f"
}
```

---

## Langfuse trace metadata (root trace, abbreviated)

| Key | Present | Notes |
|-----|---------|-------|
| `conversation_id` | yes | Matches webhook |
| `business_id` | yes | `demo_barbershop_001` |
| `channel` | yes | `test` |
| `greeting_mode` | yes | `first_contact` |
| `assembled_prompt` | yes | ~3654 chars (dev) |
| `correlation_id` | **no** | D2 expected |
| `n8n_execution_id` | **no** | D2 expected |
| `prompt_run_id` | **no** | D2 expected on span after create |
| `conversation_intent` | **no** | Expected only for Alpstein demo business |

---

## Discovered risks

| Risk | Impact |
|------|--------|
| Stale host uvicorn after D2 merge | Operators believe CIP-C is live; contracts not enforced |
| `prompt_runs.metadata` always null on live path | Ops replay chain broken at DB layer |
| Invalid correlation not rejected | Bad n8n headers can pollute sessions undetected |
| Langfuse generation **input** still holds full OpenAI messages | Out of D4.1 flat-metadata check; still a dev-data exposure surface |
| D4.1 run on `demo_barbershop_001` | CIP intent metadata not expected unless switched to `alpstein_ai_demo_001` |

---

## Unresolved issues

1. **Restart required** — D4.1 must be repeated after backend reload from `5a45478+`.
2. **Readiness 404** — Live process lacks `/api/v1/health/ready` (pre-B2.4 or old build); separate from CIP-C but blocks compose-style gates.
3. **Second validation business** — Re-test with `alpstein_ai_demo_001` for CIP intent fields once D2 process is active.
4. **Screenshots** — Operator to attach Langfuse UI for trace `9d1037bbe099030e22a02a7cc7a0efec` when re-running.

---

## Operational remediation (before re-test)

```bash
# 1) Stop stale uvicorn on 8010 (operator confirms PID)
kill <pid>   # was 445006 at validation time

# 2) Start from current tree
cd /opt/alpstein-ai/backend
source .venv/bin/activate
# ensure .env / env vars loaded (DATABASE_URL, tokens, Langfuse keys)
uvicorn app.main:app --host 0.0.0.0 --port 8010

# 3) Re-run D4.1 webhook + DB + Langfuse API checks from this doc
# 4) Expect: invalid correlation → 400 VALIDATION_ERROR
#           prompt_runs.metadata JSON with correlation_id
#           Langfuse metadata.correlation_id matches header
```

Portable compose path remains optional; not used for this run.

---

## Recommended follow-up tasks

| ID | Task |
|----|------|
| **D4.1-R1** | Restart host backend; repeat live validation checklist |
| **D4.1-R2** | Add deploy checklist: “restart required after D2” in ops runbook |
| **D4.1-R3** | Second webhook on `alpstein_ai_demo_001` for CIP intent metadata |
| **D4.1-R4** | Operator Langfuse screenshot attached to audit appendix |
| **D3-OPS** | n8n headers (`X-Correlation-Id`, `X-N8n-Execution-Id`) — unchanged |

---

## Phase D4.1 approval gate

| Gate | Status |
|------|--------|
| D4.1 live trace validation | **BLOCKED** |
| Proceed to D3 n8n headers / ATTR | **Only after D4.1-R1 passes** |

---

## Related

- [`d3-runtime-trace-validation-2026-05-27.md`](d3-runtime-trace-validation-2026-05-27.md)
- [`tasks/done/T-d2-langfuse-runtime-metadata-wiring.md`](../../tasks/done/T-d2-langfuse-runtime-metadata-wiring.md)
