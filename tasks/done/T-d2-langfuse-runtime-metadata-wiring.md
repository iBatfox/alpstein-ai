# T-d2 — Langfuse runtime metadata wiring (Phase D / D2)

**Status:** done (pending human review)  
**Date:** 2026-05-27  
**Branch:** `stabilization/runtime-baseline`  
**Canonical:** `specs/architecture/observability-metadata.md` (§16 locked defaults)

## Goal

Deterministic observability wiring: `ObservabilityContext`, `correlation_id` propagation, Langfuse metadata alignment, `prompt_runs.metadata` scalar subset, structured logging.

## Delivered

- `ObservabilityContext` + ingress helpers (`resolve_correlation_id`, `observability_context_from_webhook`)
- ContextVar + `CorrelationIdLogFilter` for structured logs
- Webhook route: `X-Correlation-Id` > body `correlation_id` > generate; `X-N8n-Execution-Id`
- Propagation: webhook → message service → AI coordinator → orchestration → Langfuse + `prompt_runs.metadata`
- Langfuse: flat metadata from envelope; demo tag `alpstein_ai_demo_001` only; CIP intent keys
- Tests: `test_observability.py`, updated langfuse/orchestration/webhook route tests

## Out of scope (unchanged)

- n8n workflows (D3), ATTR-3, dashboards, metrics stack

## Review fix (§16.2)

- `assembled_prompt` Langfuse metadata uses the same dev/test guard as `operator_business_context` (production + explicit tracing: boolean/lineage only, no text previews).

## Verification

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest pytest-anyio
.venv/bin/python -m pytest tests/test_observability.py tests/test_langfuse_tracing_service.py \
  tests/test_ai_reply_orchestration_service.py tests/test_webhook_message_route.py -q
```
