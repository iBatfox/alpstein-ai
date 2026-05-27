**Doc status:** archived  
**Tier:** project-status/historical (pending move)  
**Note:** T11 slice complete — see [`completed.md`](../completed.md)

# T11 — AI orchestration plan (canonical reference)

**Canonical task breakdown:** [`tasks/done/t11-ai-orchestration-slice.md`](../../../tasks/done/t11-ai-orchestration-slice.md)

**Status:** **Done** (T11.1–T11.16, 2026-05-24).

**Completed in code:** migrations + models; config/knowledge/history/prompt builder/gateway services; PromptRun + outgoing message persistence; orchestration + fallback + duplicate guard; webhook wire-up; integration regression suite (`test_t11_ai_webhook_integration.py`); status docs sweep (T11.16).

**T10-F1 (done):** API token auth on `POST /api/v1/webhook/message` (`X-Alpstein-Webhook-Token` / `N8N_BACKEND_API_TOKEN`).

**Next feature slice:** **T12** — lead creation and `lead_created` / `notify_owner` in webhook response.

## Architecture constraints

- **OpenAI HTTP only in AI Gateway Service** (`app/services/ai_gateway/_openai.py`)
- Prompt Builder and AI Gateway remain separated
- PromptRuns are execution logs, not AI memory
- AI orchestration stays backend-owned; **n8n does not write to PostgreSQL** in MVP
- Provider-neutral assembly uses section IDs `tenant_behavior`, `knowledge` (not legacy `tenant_ai_behavior` / `knowledge_snippets`)
