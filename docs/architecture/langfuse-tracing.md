**Doc status:** runtime-derived (supplement)  
**Tier:** architecture/runtime (pending move)  
**Canonical source:** `docs/architecture/canonical-runtime-architecture.md` §11 (observability runtime truth)  
**Metadata semantics:** [`specs/architecture/observability-metadata.md`](../../specs/architecture/observability-metadata.md) — D1 **approved** (§16 defaults locked); **D2 runtime wiring** in `ObservabilityContext` + `LangfuseTracingService.trace_ai_reply`  
**Keep as:** implementation detail / enablement notes

# Langfuse tracing (backend MVP)

**Status:** Implemented for all environments when credentials are configured.
**D4.4:** flat metadata production-safe; generation I/O exposure remains when
AI tracing is active — see
[`d4-operational-wrap-up-2026-05-27.md`](../audits/d4-operational-wrap-up-2026-05-27.md).

## Enable

Set in `.env` (never commit values):

```env
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_TRACING_ENABLED=true
ALPSTEIN_AI_ENVIRONMENT=development
```

Tracing activates whenever both keys are set. Environment and
`LANGFUSE_TRACING_ENABLED` do not disable tracing when credentials are present.

## Trace shape

| Observation | Type | Content |
|-------------|------|---------|
| `ai_reply_orchestration` | span | business/conversation/channel, greeting mode, language, operator context, assembled prompt |
| `openai_chat_completion` | generation | OpenAI messages input, model output, token usage, latency |

## Tags

- `greeting_orchestration` (always)
- `telegram` (when `channel=telegram`)
- `alpstein_ai_demo_001` — **approved (D1 §16.4):** only when `business_external_id=alpstein_ai_demo_001` (D2 removes incorrect tag on `demo_barbershop_001`)

Session id = `conversation_id` UUID (unchanged).

## D1 approved defaults (D2 wired)

| Topic | Approved behavior |
|-------|-------------------|
| `correlation_id` | Header `X-Correlation-Id` preferred over body; server UUID if absent |
| Operator context | `operator_business_context_present` always; truncated text **non-production only** (§16.2) |
| `assembled_prompt` | Truncated prompt body **non-production only** — same §16.2 guard as operator text |
| `prompt_runs.metadata` | Scalar envelope subset, max 4096 bytes; no full prompt duplicate |
| n8n execution | Header `X-N8n-Execution-Id` in D2 |
| CIP intent keys | Wire `conversation_intent`, `intent_matched_rule`, `intent_used_previous_message` in D2 |

Full contract: observability-metadata.md §16.

## Integration point

`WebhookMessageService.process_incoming_message` wraps the complete message
turn. `AiReplyOrchestrationService.generate_reply` adds the nested AI
generation span when the AI Gateway is used.

## Security

Secrets (OpenAI key, Langfuse secret, tokens) are never written to trace metadata.
