**Doc status:** runtime-derived (supplement)  
**Tier:** architecture/runtime (pending move)  
**Canonical source:** `docs/architecture/canonical-runtime-architecture.md` §11 (observability runtime truth)  
**Keep as:** implementation detail / enablement notes; may lag behind canonical map until CIP-C closes

# Langfuse tracing (backend MVP)

**Status:** Implemented — dev/internal only.

## Enable

Set in `.env` (never commit values):

```env
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_TRACING_ENABLED=true
ALPSTEIN_AI_ENVIRONMENT=development
```

Tracing auto-enables in `development` / `dev` / `local` / `test` when both keys are set. Production requires explicit `LANGFUSE_TRACING_ENABLED=true`.

## Trace shape

| Observation | Type | Content |
|-------------|------|---------|
| `ai_reply_orchestration` | span | business/conversation/channel, greeting mode, language, operator context, assembled prompt |
| `openai_chat_completion` | generation | OpenAI messages input, model output, token usage, latency |

## Tags

- `greeting_orchestration` (always)
- `telegram` (when `channel=telegram`)
- `alpstein_ai_demo_001` (when `business_id=demo_barbershop_001`)

Session id = `conversation_id` UUID.

## Integration point

`AiReplyOrchestrationService.generate_reply` wraps `AiGatewayService.complete`.

## Security

Secrets (OpenAI key, Langfuse secret, tokens) are never written to trace metadata.
