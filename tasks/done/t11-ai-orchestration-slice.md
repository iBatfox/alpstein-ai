# T11 — AI orchestration slice (finalized plan)

**Status:** **done** (T11.1–T11.16 complete; 2026-05-24)

**Goal:** Replace T10 stub `reply_to_customer` with spec-aligned AI orchestration while staying MVP-safe.

**MVP success (achieved in code):** Inbound webhook returns real `reply_to_customer` from the AI stack; outgoing AI messages and `prompt_runs` are persisted; duplicate webhooks skip re-execution; failures use fallback policy. `lead_created` / `notify_owner` remain `false` until **T12**.

**Depends on:** T10 (webhook route and incoming message persistence).

---

## Spec alignment

- **In MVP:** yes — `specs/mvp/mvp-scope.md` (AI reply, PromptRun logging)
- **Primary specs:**
  - `specs/architecture/ai-configuration-architecture.md`
  - `specs/architecture/prompt-builder-rules.md`
  - `specs/flows/incoming-message-flow.md` (Steps 12–19, §10 Idempotency)
  - `specs/database/database-schema.md` (AI tables, `prompt_runs`)
  - `specs/api/webhooks.md`, `specs/api/api-endpoints.md` (response shape unchanged)
- **Out of scope:** n8n workflow implementation, lead creation, owner notifications, vector DB / embeddings / AI memory / multi-agent, **T10-F1** (production blocker, parallel track), `IntegrityError` race handling (T10-F3)

**Architecture note:** Services + `AsyncSession`, mandatory `tenant_id` / `business_id` filters. **No generic repository layer.** **No OpenAI HTTP outside Gateway.**

---

## T10 follow-ups (parallel track)

| ID | Task | Status | Notes |
|----|------|--------|--------|
| **T10-F1** | API token auth on `POST /api/v1/webhook/message` | **Open** | **Production blocker** before n8n/production |
| **T10-F2** | Fix stale project-status Database lines | Optional | Addressed in T11.16 sweep where applicable |
| **T10-F3** | `IntegrityError` on concurrent duplicate `external_message_id` | **Open** | Complements T5/T6 |

---

## T11 task breakdown

### Phase A — Data foundation

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| **T11.1** | Alembic AI tables + `prompt_runs` | **Done** | `0006`, model tests |
| **T11.2** | Tenant-scoped AI read services | **Done** | `test_ai_configuration_services.py` |
| **T11.3** | Dev AI configuration seed | **Done** | `test_dev_ai_configuration_seed.py` |

### Phase B — AI services (no webhook orchestration yet)

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| **T11.4** | AI Configuration Service | **Done** | `test_ai_configuration_service.py` |
| **T11.5** | Knowledge Retrieval Service | **Done** | `test_knowledge_retrieval_service.py` |
| **T11.6** | Conversation history DTOs + loader | **Done** | `test_message_conversation_context.py` |
| **T11.7** | Prompt Builder Service | **Done** | `test_prompt_builder_service.py`; section IDs `tenant_behavior`, `knowledge` |
| **T11.8** | AI Gateway Service (sole OpenAI HTTP) | **Done** | `test_ai_gateway_service.py` (mocked HTTP) |

### Phase C — Persistence helpers

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| **T11.9** | `save_outgoing_ai_message` | **Done** | `test_message_service.py` |
| **T11.10** | `PromptRunService.create_prompt_run` | **Done** | `test_prompt_run_service.py` |

### Phase D — Orchestration, fallback, webhook, tests, docs

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| **T11.11** | `AiReplyOrchestrationService` | **Done** | `test_ai_reply_orchestration_service.py` |
| **T11.12** | `AiReplyFallbackService` (tenant fallback → platform default) | **Done** | `test_ai_reply_fallback_service.py` |
| **T11.13** | `AiReplyOrchestrationCoordinator` (duplicate skip) | **Done** | `test_ai_reply_orchestration_coordinator.py` |
| **T11.14** | `WebhookMessageService` wire-up | **Done** | `test_webhook_message_ai_wiring.py` |
| **T11.15** | Integration/regression suite | **Done** | `test_t11_ai_webhook_integration.py` (9 tests) |
| **T11.16** | Project status/docs sweep | **Done** | `docs/project-status/*` |

**Explicitly not in T11:** vector path; lead/notify (**T12**); n8n workflows; prompt management UI; exposing system prompts in HTTP responses.

---

## Dependency graph

```text
T10 ─┬─► T11.1 → T11.2 → T11.3
     │                    ├─► T11.4 ─┐
     │                    ├─► T11.5 ─┼─► T11.7 → T11.8 ─┐
     │                    └─► T11.6 ─┘                  │
     ├─► T11.9 ─────────────────────────────────────────┼─► T11.11 → T11.12 → T11.13 → T11.14 → T11.15 → T11.16 ✓
     └─► T11.10 ────────────────────────────────────────┘

T10-F1 — production blocker (before n8n/production)
T12 — next feature slice (after T10-F1)
```

---

## Risks (mitigations in place)

| Risk | Mitigation |
|------|------------|
| Provider call outside Gateway | Only `ai_gateway/_openai.py` performs HTTP |
| Duplicate webhooks double-charge OpenAI | T11.13 + T11.14 duplicate path |
| `prompt_runs.final_prompt` leaks to customers | Redaction + truncation; not in webhook `data` |
| Missing `OPENAI_API_KEY` | Gateway error → T11.12 fallback → T11.14 reply |
| Webhook unauthenticated in prod | **T10-F1** before n8n |
| Tests call real OpenAI | Mocked in T11.8 / T11.15 |

---

## n8n / API contract

Response shape unchanged (`success`, `data.reply_to_customer`, `lead_created`, `notify_owner`, `conversation`, `message`). n8n receives **real AI or fallback text** (not the T10 stub). Backend must not be called in production until **T10-F1** auth is enabled.

---

## What’s next

1. **T10-F1** — webhook API token auth (production blocker)
2. **T12** — leads + owner notifications in webhook response
