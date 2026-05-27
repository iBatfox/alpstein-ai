**Doc status:** runtime-derived  
**Tier:** project-status/current  
**Canonical anchor:** [`architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md)

# Alpstein AI — Current State

**As-of:** 2026-05-27

## Project Phase

Specification-driven MVP with **backend AI orchestration complete**, **n8n test + Telegram ingress workflows implemented** (ops maturity partial), and **conversational behavior extensions** (greeting, intent for one demo business, operator context) shipped in backend.

**Primary open engineering:** CIP-C Langfuse intent metadata, T14.5–T14.6 Telegram regression/export gate, ATTR-3 attribution persistence.

---

## Specifications

### Existing

- system, backend, n8n, AI configuration, database architecture
- database schema, entities, API endpoints, webhooks
- incoming message, lead creation, notification flows
- MVP scope

### Spec-only / drift notes

- **Conversation Intent Policy** — behavior doc at `docs/architecture/conversation-intent-policy-mvp.md`; CIP-A/B **implemented** for `alpstein_ai_demo_001` only; CIP-C/D open
- **Attribution persistence (ATTR-3+)** — ATTR-2 schema **implemented**; persistence **planned**

---

## AI Engineering Governance

### Existing

- `AGENTS.md`, `CODEX.md`
- Cursor skills: backend-engineer, database-architect, migration-engineer, api-designer, ai-integration-engineer, n8n-integration-engineer, reviewer, task-planner, **project-archivist**
- Documentation index: [`docs/README.md`](../../docs/README.md); canonical runtime map: [`docs/architecture/canonical-runtime-architecture.md`](../../docs/architecture/canonical-runtime-architecture.md)

---

## Backend

### Existing

- `GET /api/v1/health`
- async SQLAlchemy + Alembic migrations `0001`–`0007`
- models: tenants, businesses, customers, conversations, messages, leads, AI config tables, `prompt_runs`
- domain exceptions + tenant context validator
- `BusinessService`, `CustomerService`, `ConversationService`, `MessageService`, `LeadService`
- `NotificationPolicyService`, `LeadSignalDetectionService`
- `POST /api/v1/webhook/message` — token auth (`T10-F1`); full T11–T12 orchestration in `WebhookMessageService`
- message idempotency: partial unique index on `(business_id, external_message_id)`
- normalized webhook schemas + ATTR-2 attribution fields (`webhook_attribution.py`)
- `operator_business_context` on webhook → PromptBuilder overlay (`T14-OC-2`)
- AI stack: Configuration → Knowledge → PromptBuilder → Gateway → PromptRun → orchestration + fallback + duplicate guard
- **Greeting:** `GreetingPolicyService` + greeting blocks in §2 task_instructions
- **Intent (partial):** `ConversationIntentService` + intent slices for `alpstein_ai_demo_001` only; non-Alpstein tenants use core task + generic greeting only (P0 + P1; no legacy appendix)
- **History Safety (HF-1):** §7 preamble + non-authoritative `ai` labels in `PromptBuilderService` — **implemented**
- **Langfuse (dev):** `LangfuseTracingService` on orchestration; greeting tags; intent metadata constants exist but **runtime export not wired (CIP-C)**
- pytest: **308** test functions in `backend/tests/` (as-of 2026-05-27; run `pytest` in venv to verify green)

### Missing / deferred

- T10-F3 — concurrent duplicate `external_message_id` `IntegrityError` race (optional)
- repositories layer (**deferred** MVP)
- ATTR-3+ attribution persistence

---

## Database

### Existing

- Alembic `0001`–`0007` (tenants → `prompt_runs`, `leads`)
- SQLAlchemy models + async session
- dev seed: `demo_barbershop_001` + separate `alpstein_ai_demo_001` demo business

### Missing / deferred

- repositories (services use `AsyncSession` directly)
- attribution columns / persistence

---

## n8n

### Existing

- Docker runtime (`n8n/docker-compose.yml`), HTTPS at `n8n.alpstein-ai.ch`
- Workflow 1 test webhook: normalize → backend → customer reply → owner Telegram (T13.1–T13.5; Gate 1 + Gate 2 passed)
- Telegram customer ingress workflow (T14.1–T14.4, T14-OC-3, Alpstein AI greeting switch on `alpstein_ai_demo_001`)
- exports in `n8n/workflows/`; ops runbooks in `docs/ops/`
- n8n does **not** write PostgreSQL (MVP rule)

### Missing / partial

- T14.5 owner-notify + duplicate regression on Telegram path
- T14.6 scrubbed export + repo source-of-truth gate
- T13.6 retries/errors, T13.7 full E2E (**deferred**)
- WhatsApp ingress (**deferred**)
- operator contact block in n8n `operator_business_context` (ops follow-up per pre-sales contact ownership)

---

## AI Layer (orchestration summary)

| Component | Status |
|-----------|--------|
| PromptBuilder 8-section assembly | **implemented** |
| Greeting orchestration | **implemented** |
| Intent policy (`alpstein_ai_demo_001`) | **partial** (one business) |
| Legacy pre-sales appendix | **removed** (P1); non-Alpstein uses core task + generic greeting only |
| Operator context overlay | **implemented** |
| History Safety (HF-1) | **implemented** |
| Langfuse intent metadata at runtime | **planned** (CIP-C) |
| AI Gateway (sole OpenAI HTTP) | **implemented** |

---

## Infrastructure

- server, domain, HTTPS — **implemented**
- Domain: https://alpstein-ai.ch
- n8n admin: https://n8n.alpstein-ai.ch

---

## Current MVP Goal

**Target flow:** Customer message → normalized webhook → backend → AI reply → stored conversation → lead → owner notification.

**Implemented (backend + partial ops):** webhook + auth, AI reply, leads, notification flags, test webhook path, Telegram customer ingress with greeting/intent for Alpstein demo business.

**Not closed:** CIP-C observability, T14.5–T14.6 Telegram gates, ATTR persistence, production hardening (T10-F3, T13.6).
