# CIP-C Phase D — D1 Observability metadata (complete)

**Status:** **approved** — §16 defaults locked; **D2 implemented** (pending review)  
**Date:** 2026-05-25 · defaults finalized 2026-05-27  
**Branch:** `stabilization/runtime-baseline`

**Canonical contract:** [`specs/architecture/observability-metadata.md`](../../specs/architecture/observability-metadata.md)

## Deliverables (D1)

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | Metadata contract | `specs/architecture/observability-metadata.md` |
| 2–11 | Required/optional fields, naming, lifecycle, correlation, session, workflow, channel, prompt lineage, replay | §3–§11 |
| 12 | Langfuse mapping proposal | §12 |
| 13 | D2 file list | §14 |
| 14 | Risks / approved defaults | §16 |
| — | Review checklist | §17 |

## Current runtime baseline (audit summary)

| Mechanism | State |
|-----------|--------|
| `prompt_runs` | Persists execution; `final_prompt` redacted; **`metadata` JSONB underused** |
| `messages.ai_metadata` | `prompt_run_id`, `model`, `provider`, `used_fallback` |
| Langfuse | D2 — flat envelope metadata; `session_id=conversation_id`; `correlation_id` + CIP intent keys wired |
| Webhook | D2 — `X-Correlation-Id` / body / server UUID; `X-N8n-Execution-Id` at ingress |
| Channel attribution | Spec only (ATTR); not in traces yet |

## Approved defaults (§16 summary)

| Topic | Default |
|-------|---------|
| Correlation id | Header `X-Correlation-Id` > body `correlation_id` > server UUID v4 |
| Operator context in traces | Boolean always; text preview non-production only |
| `prompt_runs.metadata` | Scalar envelope subset, max 4096 bytes |
| Demo tag | `alpstein_ai_demo_001` only for that `business_external_id` |
| n8n execution | Header `X-N8n-Execution-Id` in D2; optional webhook field in D3 |
| Production Langfuse | Unchanged — off unless explicit enable + keys |

## Next step

**D2** — `ObservabilityContext` + propagation + Langfuse metadata + `prompt_runs.metadata`. **Implemented** (see `tasks/done/T-d2-langfuse-runtime-metadata-wiring.md`).

## Suggested commit

See §18 in canonical spec.
