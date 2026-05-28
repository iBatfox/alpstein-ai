**Doc status:** runtime-derived  
**Tier:** project-status/current  
**Canonical anchor:** [`architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md)

# Alpstein AI — Current State

**As-of:** 2026-05-28 (OPS-H1 runtime surface documented)

## Project Phase

Specification-driven MVP with **backend AI orchestration complete**, **n8n test + Telegram ingress workflows implemented** (ops maturity partial), and **conversational behavior extensions** (greeting, intent for one demo business, operator context) shipped in backend.

**Phase D4 operational verification:** **complete** (D4.1–D4.4, U1, OPS-C1). Portable **Docker Compose** is the **operational source of truth** for backend verification; see [`d4-operational-wrap-up-2026-05-27.md`](../audits/d4-operational-wrap-up-2026-05-27.md).

**OPS-H1 (runtime surface):** **PASS WITH NOTES** — [`runtime-map.md`](../ops/runtime-map.md) · [`runtime-surface-hardening.md`](../ops/runtime-surface-hardening.md). Canonical ports: **15679** (n8n), **8000** (backend loopback), **15433** (postgres loopback). Legacy **8010** / **15432** not listening; `backend_postgres` container absent. **Action item:** `python3 -m http.server` on **`0.0.0.0:8088` / `8090`** — use `--bind 127.0.0.1` or stop when idle.

**RECOVERY-2 (compose recreate):** **PASS WITH NOTES** — [`recovery-compose-recreate-stabilization-2026-05-28.md`](../audits/recovery-compose-recreate-stabilization-2026-05-28.md). Root cause: **docker-compose v1.29 + Docker 29** → `ContainerConfig` on recreate. Fix: **`docker compose` v2** installed; full stack `up -d postgres backend n8n` verified; `--force-recreate` safe on v2. Canonical CLI documented in `postgres-compose.md` / `.env.example`. Legacy `docker-compose --force-recreate` **still broken** — do not use.

**RECOVERY-1 (runtime SoT):** **PASS WITH NOTES** — [`recovery-runtime-source-of-truth-2026-05-28.md`](../audits/recovery-runtime-source-of-truth-2026-05-28.md). Portable chain: `alpstein_postgres` → `alpstein_backend` → `alpstein_n8n_compose` @ **15679**; all compose-labeled under project `alpstein-ai`.

**Phase E0 (Telegram stability gate):** **PASS WITH WARNINGS** — [`e0-telegram-regression-2026-05-28.md`](../audits/e0-telegram-regression-2026-05-28.md) + [`e0-telegram-reference-channel-remediation-2026-05-28.md`](../audits/e0-telegram-reference-channel-remediation-2026-05-28.md). **Telegram reference channel: YES WITH WARNINGS** — portable `alpstein_n8n_compose` exec **222**, full n8n → `http://backend:8000` → AI path; synthetic Telegram Send (`chat not found`); Langfuse trace not on running compose backend yet.

**Primary open engineering:** E2.5+ (webhook response trace fields, n8n delivery logging); `messages.flow_id` denorm optional; Live Telegram DM confirmation post E1.9; Langfuse on compose backend; **CIP-D**, ATTR-3. **E2.4 (done):** `message_traces` persistence — inbound lifecycle + dedup-safe (Alembic `0011`). **E2.3 (done):** inbound message dedup — conversation-scoped `idempotency_key` + partial uniques (Alembic `0010`). **E2.2 (done):** conversation `flow_id` + flow-scoped lookup (Alembic `0009`). **E1.9 (done):** Production ingress on **`alpstein-customer-ingress`** (`aYrRmAGKhP4TJbG9`) — [`e1-9-unified-ingress-cutover-2026-05-28.md`](../audits/e1-9-unified-ingress-cutover-2026-05-28.md). Legacy workflows archived (`2lMuaSWD1XFOXLEK`, `hAJ3TFYn69in0vd5`). **E2.0 (done, design-only):** [`unified-conversation-observability.md`](../architecture/unified-conversation-observability.md) — **PASS WITH NOTES**.

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
- **Channel expansion ingress contract (E1.0)** — **implemented as design/spec only** in `docs/architecture/channel-ingress-contract.md`; no runtime integration started
- **Telegram + Website Chat mapping (E1.1)** — **implemented as design/spec only** in `docs/architecture/channel-mapping-telegram-website.md`; runtime unchanged
- **Normalized channel API alignment (E1.2)** — **implemented as spec only** in `specs/architecture/normalized-channel-contract.md`; `specs/api/webhooks.md` §7 aligned; runtime unchanged
- **Website Chat architecture (E1.3)** — **implemented as spec only** in `docs/architecture/website-chat-architecture.md`; widget/n8n/E2E phases E1.4–E1.6 bounded; runtime unchanged
- **Multi-channel identity strategy (E1.4)** — **implemented as spec only** in `docs/architecture/multi-channel-identity-strategy.md`; conservative non-merge rules locked; runtime unchanged
- **Channel capability matrix (E1.5)** — **implemented as spec only** in `docs/architecture/channel-capability-matrix.md`; Telegram vs Website operational differences and placeholder-channel boundaries documented; runtime unchanged
- **Website Chat MVP runtime (E1.6)** — minimal runtime slice implemented: widget assets + n8n workflow + ops runbook using existing backend orchestration path; no backend redesign
- **Unified conversation + observability (E2.0)** — **design-only** in [`unified-conversation-observability.md`](../architecture/unified-conversation-observability.md), [`unified-conversation-model.md`](../../specs/architecture/unified-conversation-model.md), [`message-trace-lifecycle.md`](../../specs/observability/message-trace-lifecycle.md), [`message-debugging-runbook.md`](../ops/message-debugging-runbook.md); golden rule **one flow = one bot behavior**; no runtime/migrations in E2.0
- **E1.6.2 + E1.6.3 live compose smoke/retest** — runtime blocker fixed (`Cannot find module 'crypto'` removed from Normalize node); see [`e1-6-2-website-chat-live-smoke-2026-05-28.md`](../audits/e1-6-2-website-chat-live-smoke-2026-05-28.md), [`T-e1.6.2-website-chat-live-smoke-verification.md`](../../tasks/done/T-e1.6.2-website-chat-live-smoke-verification.md), and [`T-e1.6.3-website-chat-runtime-stabilization.md`](../../tasks/done/T-e1.6.3-website-chat-runtime-stabilization.md)

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
- async SQLAlchemy + Alembic migrations `0001`–`0008` (`flows` in E2.1)
- models: tenants, businesses, customers, conversations, messages, leads, AI config tables, `prompt_runs`
- domain exceptions + tenant context validator
- `BusinessService`, `CustomerService`, `ConversationService`, `MessageService`, `LeadService`, `FlowService`
- `NotificationPolicyService`, `LeadSignalDetectionService`
- `POST /api/v1/webhook/message` — token auth (`T10-F1`); full T11–T12 orchestration in `WebhookMessageService`; optional `flow_key`; success `data.flow` (E2.1)
- message idempotency: partial unique index on `(business_id, external_message_id)`
- normalized webhook schemas + ATTR-2 attribution fields (`webhook_attribution.py`)
- `operator_business_context` on webhook → PromptBuilder overlay (`T14-OC-2`)
- AI stack: Configuration → Knowledge → PromptBuilder → Gateway → PromptRun → orchestration + fallback + duplicate guard
- **Greeting:** `GreetingPolicyService` + greeting blocks in §2 task_instructions
- **Intent (partial):** `ConversationIntentService` + intent slices for `alpstein_ai_demo_001` only; non-Alpstein tenants use core task + generic greeting only (P0 + P1; no legacy appendix)
- **History Safety (HF-1):** §7 preamble + non-authoritative `ai` labels in `PromptBuilderService` — **implemented**
- **Langfuse (dev):** `LangfuseTracingService` + `ObservabilityContext` (D2); flat metadata §16.2; intent keys wired in orchestration path — **implemented**; production off by default
- **Observability metadata (D4):** `prompt_runs.metadata` JSON-safe (`json_safe_metadata`); scalar lineage; production-safe envelope per D4.4
- pytest: **400** passed in `backend/tests/` (as-of 2026-05-28 E2.1)

### Missing / deferred

- T10-F3 — concurrent duplicate `external_message_id` `IntegrityError` race (optional)
- repositories layer (**deferred** MVP)
- ATTR-3+ attribution persistence

---

## Database

### Existing

- Alembic `0001`–`0008` (tenants → `prompt_runs`, `leads`, `flows`)
- SQLAlchemy models + async session
- dev seed: `demo_barbershop_001` + separate `alpstein_ai_demo_001` demo business

### Missing / deferred

- repositories (services use `AsyncSession` directly)
- attribution columns / persistence
- **`flows` table** — **E2.1 done**; default flow per business; webhook flow resolution
- **`message_traces` table** (E2.4 — designed in E2.0)
- **`messages.flow_id`** denorm (optional E2.4+; dedup uses `conversation_id` today)

---

## n8n

### Existing

- Docker runtime (`n8n/docker-compose.yml`), HTTPS at `n8n.alpstein-ai.ch`
- Workflow 1 test webhook: normalize → backend → customer reply → owner Telegram (T13.1–T13.5; Gate 1 + Gate 2 passed)
- Telegram customer ingress workflow (T14.1–T14.4, T14-OC-3, Alpstein AI greeting switch on `alpstein_ai_demo_001`)
- exports in `n8n/workflows/`; ops runbooks in `docs/ops/`
- n8n does **not** write PostgreSQL (MVP rule)

### Missing / partial

- **T14.5 / T-e0 remediation** — **done (WARN)** — exec **222**; reference channel **YES WITH WARNINGS**
- C1 runtime/export parity policy — [`n8n-runtime-export-parity.md`](../ops/n8n-runtime-export-parity.md) (E0 runtime categories §0)
- C2/T14.6 export scrub gate — [`scripts/n8n/export-scrub.sh`](../../scripts/n8n/export-scrub.sh) (G-EXP-2)
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
| Langfuse intent metadata at runtime | **implemented** (D2); live Alpstein demo smoke **open** (CIP-D) |
| AI Gateway (sole OpenAI HTTP) | **implemented** |

---

## Operational baseline (Phase D4)

| Item | Status |
|------|--------|
| Compose runtime SoT | **verified** (D4.2, D4.3) — `docker-compose -p alpstein-ai` |
| Migrate-before-serve | **verified** — `backend/docker-entrypoint.sh` |
| Correlation / replay lineage | **verified** on compose (D4.3) |
| Metadata JSON-safe persistence | **verified** (U1 + D4.3) |
| Production-safe metadata envelope | **verified** by code + sample (D4.4) |
| Single ingress policy | **implemented** (OPS-C1) — [`operational-ingress-policy.md`](../ops/operational-ingress-policy.md) |
| Failure-path live drill | **deferred** |
| Legacy host `:8010` | **compatibility only** — stale-process hazard if not stopped |

Wrap-up: [`d4-operational-wrap-up-2026-05-27.md`](../audits/d4-operational-wrap-up-2026-05-27.md).

---

## Infrastructure

- server, domain, HTTPS — **implemented**
- Domain: https://alpstein-ai.ch
- n8n admin: https://n8n.alpstein-ai.ch

### Deployment portability (B2)

| Phase | Status |
|-------|--------|
| B2.0 deployment contract | **done** — [`docs/deployment/deployment-contract.md`](../deployment/deployment-contract.md) |
| B2.1 env governance artifacts | **done** — `backend/.env.example`, `n8n/.env.example`, root `.env.example` index |
| B2.2 Postgres compose | **done** — [`postgres-compose.md`](../deployment/postgres-compose.md) |
| B2.3 Backend Dockerfile | **done** — [`backend-image.md`](../deployment/backend-image.md) |
| B2.4 Readiness health | **done** — `GET /api/v1/health/ready` |
| B2.5 Entrypoint migrate-then-serve | **done** — `backend/docker-entrypoint.sh` |
| B2.6 Compose backend service | **done** — `postgres` + `backend` in root compose |
| B2.7 n8n compose integration | **done** — `n8n` on `alpstein_internal`, `BACKEND_BASE_URL=http://backend:8000`; legacy `alpstein_n8n` unchanged |
| B2.8 Bootstrap profile | **done** — compose profile `bootstrap`; [`bootstrap-profile.md`](../deployment/bootstrap-profile.md) |
| B2.9 Clean-clone gate | **done** — [`clean-clone-gate-2026-05-27.md`](../audits/clean-clone-gate-2026-05-27.md) |

**Portable Postgres:** service `postgres`, DB `alpstein_ai`, volume `alpstein_postgres_data` — separate from legacy `backend_postgres` / `bitrix_app`.

**Legacy production:** host uvicorn `:8010`, n8n `BACKEND_BASE_URL=http://172.20.0.1:8010`, shared `backend_postgres` container — **documented compatibility**; not portable SoT. Do not use for D4/CIP validation without confirmed process revision.

---

## Current MVP Goal

**Target flow:** Customer message → normalized webhook → backend → AI reply → stored conversation → lead → owner notification.

**Implemented (backend + partial ops):** webhook + auth, AI reply, leads, notification flags, test webhook path, Telegram customer ingress with greeting/intent for Alpstein demo business.

**Not closed:** CIP-D smoke, T14.5 Telegram regression, ATTR persistence, E1.2 API/spec alignment, production hardening (T10-F3, T13.6).
