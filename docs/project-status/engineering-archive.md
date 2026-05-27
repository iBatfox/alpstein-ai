**Doc status:** archived  
**Tier:** project-status/historical (pending move)  
**Canonical anchor:** [`architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md) for runtime; this file for chronology

# Alpstein AI — Engineering Archive

**Document type:** internal engineering history (not marketing)  
**As-of:** 2026-05-27 (archivist patch)  
**Audience:** onboarding, architecture review, founder reference, historical reconstruction  
**Rule:** status labels are explicit — **implemented**, **partial**, **deferred**, **experimental**, **planned**. Planned work is not described as shipped.

**Primary evidence:** `docs/project-status/completed.md`, `tasks/done/*`, `specs/`, Alembic revisions, ops runbooks, architecture decision records.

---

## Chronology (high level)

| Period | Focus | Outcome |
|--------|--------|---------|
| Pre-2026-05-24 | Specs + agent governance | Specification layer largely complete before production code velocity |
| 2026-05-24 | Backend foundation T2–T10 | PostgreSQL core entities, webhook orchestration (stub reply), normalized contract |
| 2026-05-24 | T11 AI orchestration | Full backend AI stack: config → prompt → gateway → PromptRun → webhook wire-up |
| 2026-05-24 | T10-F1, T12 | Webhook token auth; leads + owner notification policy in backend |
| 2026-05-24–25 | T13 n8n | Docker runtime, HTTPS, test webhook → backend, owner Telegram branch (Gate 2) |
| 2026-05-25 | T14 Telegram ingress | Customer bot path, normalize mapping, live pipeline exec evidence |
| 2026-05-25 | T14-OC | `operator_business_context` spec + backend + n8n Set node |
| 2026-05-25 | Greeting, Langfuse, ATTR-2, demo separation | Backend greeting policy; dev tracing; attribution schema; Alpstein vs barbershop demo split |
| 2026-05-25–27 | CIP-B intent + contact ownership | Intent slices in §2 for `alpstein_ai_demo_001`; hardcoded contacts removed from backend prompts |
| Ongoing | Hardening + ATTR persistence | HF-1 history safety, CIP-C/D, T14.5–T14.6, ATTR-3+, T13.6 retries, WhatsApp |

---

## 1. Project vision evolution

### Initial intent (spec phase — **implemented** as documentation)

- **Product:** multi-tenant AI assistant for Swiss SMBs — ingest messages (WhatsApp, Telegram, website chat in scope), AI reply, conversation storage, lead capture, owner notification.
- **MVP goal** (`specs/mvp/mvp-scope.md`): prove message → AI reply → stored conversation → lead → owner notify without overbuilding SaaS, billing, or vector DB.
- **Commercial framing** (`specs/project/vision.md`, business goals): local outreach, demo-first sales, “never miss a customer message” — informs demo data and tone, not runtime architecture.

### Engineering vision (stable since 2026-05-24 decisions)

Documented in `docs/project-status/decisions.md`:

| Decision | Status |
|----------|--------|
| Spec-driven development (specs win over code) | **Implemented** (process) |
| Multi-tenant from day one (`tenant_id`, `business_id`) | **Implemented** |
| Backend-centric AI (no prompt assembly in n8n) | **Implemented** |
| Shared PostgreSQL MVP | **Implemented** |
| Platform safety over tenant config | **Implemented** (Prompt Builder ordering + metadata scrub) |
| Normalized webhook only (providers normalized in n8n) | **Implemented** |

### Vision drift handled in engineering (not product pivot)

- **Demo vs product assistant:** early reuse of `demo_barbershop_001` for Alpstein AI Telegram tests caused **business context contamination** — resolved by separate `alpstein_ai_demo_001` business + profiles (**implemented** data separation; see §11).
- **Operator-editable context in n8n:** added without moving OpenAI to n8n — `operator_business_context` as additive reference data (**implemented** T14-OC); DB profiles remain canonical.

---

## 2. Infrastructure / runtime

### Domain and edge (**implemented**)

- Public site: `https://alpstein-ai.ch` (referenced in project status).
- n8n admin/UI: `https://n8n.alpstein-ai.ch` via nginx reverse proxy → `127.0.0.1:15679` (`docs/ops/n8n-https-reverse-proxy.md`).

### n8n runtime (**implemented**)

| Component | Detail |
|-----------|--------|
| Compose | `n8n/docker-compose.yml`, project `alpstein-n8n`, container `alpstein_n8n` |
| Bind | `127.0.0.1:15679` |
| Volume | `alpstein_n8n_data` |
| Docs | `docs/ops/n8n-runtime-start.md`, `n8n-env-credential-checklist.md` |

### Backend runtime (**partial** — dev/proof path documented; full production compose not unified in archive evidence)

- Gate 1 / Telegram paths documented with `BACKEND_BASE_URL=http://172.20.0.1:8010`, backend on `0.0.0.0:8010`, UFW allowing Docker bridge → host (`docs/ops/n8n-workflow1-test-webhook.md`).
- Webhook auth: `X-Alpstein-Webhook-Token` ↔ `N8N_BACKEND_API_TOKEN` (**implemented** T10-F1).

### Deferred / backlog (historical checklist: `docs/project-status/historical/backlog.md`)

- Single Docker Compose “full stack” (Postgres + API + n8n + nginx) as one artifact — **planned / partial** (n8n compose exists; full stack checklist still open in backlog).

### HubSpot / legacy n8n

- Explicit rule: do not modify `/hubspot_clone` n8n (port `15678`) — Alpstein n8n is isolated (**architecture guard**).

---

## 3. Database evolution

### Migrations (**implemented** — Alembic `0001`–`0007`, all `Create Date: 2026-05-24` unless noted)

| Rev | Tables / change |
|-----|-----------------|
| `0001` | `tenants`, `businesses` |
| `0002` | `customers` |
| `0003` | `conversations` |
| `0004` | `messages` |
| `0005` | Partial unique index `(business_id, external_message_id)` WHERE NOT NULL — idempotency |
| `0006` | `tenant_business_profiles`, `tenant_ai_profiles`, `tenant_knowledge_sources`, `tenant_channel_settings`, `prompt_templates`, `prompt_runs` |
| `0007` | `leads` |

### Access pattern (**implemented**)

- No repository layer — services use `AsyncSession` directly (**intentional MVP**; repositories **deferred** per `current-state.md`).

### Demo / seed data (**implemented** + later content refactors)

- `scripts/seed_dev_ai_configuration.py` — deterministic demo tenant, `demo_barbershop_001`, platform templates, profiles, knowledge (**T11.3**).
- Later: **`alpstein_ai_demo_001`** business row + isolated profiles/knowledge (**implemented** — demo separation task).
- Content-only refactor of Alpstein `tenant_business_profiles` to reduce marketing noise (**implemented** — no schema change).

### Not in database (MVP boundaries)

- n8n does **not** write PostgreSQL (**implemented** rule).
- `operator_business_context` **not persisted** on webhook (**implemented** T14-OC-2) — transport-only per request.
- Attribution fields validated (ATTR-2) but **not persisted** yet (**planned** ATTR-3).

### Recovery ops (**implemented** documentation)

- `docs/ops/database-recovery.md` — Alembic replay + seed after volume loss.

---

## 4. AI architecture evolution

### Phase A — Stub webhook (T10, **implemented** 2026-05-24)

- `WebhookMessageService`: resolve business → customer → conversation → save message → static `reply_to_customer`.
- No provider HTTP, no PromptRun.

### Phase B — Full orchestration stack (T11, **implemented** 2026-05-24)

Canonical chain (`AiReplyOrchestrationService`):

```text
AiConfigurationService
  → KnowledgeRetrievalService
  → MessageService.load_recent_conversation_history
  → PromptBuilderService
  → AiGatewayService (OpenAI HTTP only in ai_gateway/_openai.py)
  → PromptRunService
```

Supporting:

- `AiReplyFallbackService` — tenant fallback → platform default; `should_handoff`.
- `AiReplyOrchestrationCoordinator` — **skips** full AI path on duplicate incoming message.
- `WebhookMessageService` wire-up (T11.14) — real replies, outgoing AI message rows.

### Phase C — Post-T11 additions (**implemented** 2026-05-25)

| Addition | Role |
|----------|------|
| `GreetingPolicyService` | History-derived greeting mode → appended to `task_instructions` |
| `operator_business_context` | Webhook overlay in section 3 (after DB profile) |
| `LangfuseTracingService` | Dev/internal traces around orchestration + generation |

### Phase D — Not implemented

| Item | Status |
|------|--------|
| Vector / embedding retrieval | **Out of MVP scope** |
| AI writing leads or messages directly | **Forbidden** — backend services only |
| Provider abstraction beyond OpenAI gateway | **Deferred** |
| Attribution in Prompt Builder (`channel_source_context`) | **Planned** ATTR-4 |

### Configuration sources (precedence)

1. **Platform** — `prompt_templates.system_prompt` + task registry (immutable by tenant metadata keys).
2. **PostgreSQL** — `tenant_business_profiles`, `tenant_ai_profiles`, `tenant_channel_settings`, `tenant_knowledge_sources`.
3. **Webhook overlay** — `operator_business_context` (additive, not stored).
4. **Ephemeral** — knowledge retrieval ranking, conversation history, current message.

---

## 5. PromptBuilder evolution

### T11.7 baseline (**implemented**)

- Eight canonical sections per `specs/architecture/prompt-builder-rules.md`.
- Section IDs: `platform_system`, `task_instructions`, `tenant_business_context`, `tenant_behavior`, `channel_rules`, `knowledge`, `conversation_history`, `current_customer_message`.
- `PROMPT_ASSEMBLY_MAX_CHARS = 24_000`; variable-section truncation order documented in code (`VARIABLE_SECTION_TRIM_ORDER`).
- Explicit rejection of `raw_payload` as prompt input (**spec + code**).

### T11.7 naming sync (**implemented**)

- Legacy names `tenant_ai_behavior` / `knowledge_snippets` retired in favor of `tenant_behavior` / `knowledge`.

### T14-OC overlay (**implemented**)

- `OPERATOR BUSINESS NOTES` sub-block inside section 3 after `TenantBusinessProfile` text (`OPERATOR_BUSINESS_NOTES_LABEL` in `prompt_builder_service.py`).
- Spec §4.5 in `prompt-builder-rules.md`.

### Greeting instructions (**implemented**)

- `build_greeting_instruction_block(greeting_policy)` merged into **section 2** (`task_instructions`), not tenant reference sections — preserves platform authority (`docs/architecture/greeting-orchestration-mvp.md`).

### Planned

- `channel_source_context` section from webhook `source` + `attribution` (**planned** ATTR-4, spec stub in prompt-builder-rules §4 table).

### Design artifact

- `docs/architecture/deprecated/t11-prompt-builder-design.md` — draft pointer to canonical spec (superseded by `prompt-builder-rules.md` for implementation).

---

## 6. Telegram / n8n ingress evolution

### T13 — Test path (**implemented**)

| ID | Deliverable |
|----|-------------|
| T13.0 | Docker n8n runtime |
| T13.1 | Env/credential checklist |
| T13.2 | Workflow 1 skeleton — test webhook, normalize |
| T13.3 | POST Backend + token header |
| T13.4 | Shape customer reply (thin response for test webhook) |
| T13.5 | Owner notify branch — IF `notify_owner` → Telegram (`AlpsteinAIbot`, `TELEGRAM_CHAT_ID`) |
| Gate 1 | HTTPS test webhook → backend 200 + `reply_to_customer` |
| Gate 2 | Urgent notify delivered (exec **50**); duplicate suppress (**51**); normal no notify (**52**) |

Export: `n8n/workflows/t13_workflow1_test_webhook_skeleton.json`  
Ops: `docs/ops/n8n-workflow1-test-webhook.md`

### T14 — Telegram customer ingress (**implemented** core; **partial** production hardening)

| ID | Status |
|----|--------|
| T14.1 | Normalize mapping doc — `docs/ops/telegram-customer-ingress.md` |
| T14.2 | Dual-bot credential separation — customer `alpsteinai_0001bot` vs owner `AlpsteinAIbot` |
| T14.3 | Workflow `alpstein-incoming-message-telegram` skeleton |
| T14.4 | Pipeline verification exec **55–57** |
| T14.5 | Owner-notify + duplicate regression on Telegram path — **planned** |
| T14.6 | Scrubbed export + ops final — **planned** |

### Credential model (**implemented** as architecture)

- `docs/architecture/telegram-channel-credentials.md` — client token in n8n credentials only; backend stores `credential_ref` metadata only; owner bot separate.

### Contract notes (**implemented** decisions)

- `external_conversation_id` **not** on webhook body for MVP routing — conversation reuse via customer + `channel`; `telegram_chat_id` kept on n8n item for Send only.
- `external_message_id` = ``tg:{chat_id}:{message_id}`` for dedup.
- Private text-only MVP; drop bots, non-private chats, non-text.

### WhatsApp

- **Deferred** (T13-W* / MVP scope) — test + Telegram proved first.

### n8n retries / error taxonomy

- **Deferred** T13.6 — no structured retry layer documented.

---

## 7. Greeting orchestration

**Status:** **implemented** (backend); verified via n8n POST path after Alpstein AI switch.

| Mode | Trigger |
|------|---------|
| `first_contact` | No prior `ai` messages in loaded history |
| `follow_up` | Prior `ai` messages exist |
| `soft_return` | Prior `ai` + gap ≥ 24h since last prior message |

- Language: heuristics on `message.text` → `raw_payload` `language_code` → English default; RU/DE/EN/etc. supported in detection (`customer_language_detection.py`).
- Instructions live in **`task_instructions`** (platform layer), not operator/tenant reference blocks.
- **Limitation (documented):** does not purge polluted `messages` history — new customer/conversation required to escape old greeting loops (`greeting-orchestration-mvp.md`).

**Verification:** T14 Alpstein AI greeting switch — exec **89–91** (RU first/follow-up, DE first) — `tasks/done/T14-switch-alpstein-ai-greeting-n8n.md`.

---

## 8. `operator_business_context` evolution

| Stage | Status |
|-------|--------|
| Planning | `docs/architecture/operator-business-context-n8n.md` — rejected `raw_payload` as AI path |
| **T14-OC-1** | Spec in `webhooks.md` §7, `prompt-builder-rules.md` §4.5 — **implemented** |
| **T14-OC-2** | Pydantic field (max 8192, whitespace normalize); wire webhook → orchestration → Prompt Builder; excluded from API response; lead signals use `message.text` only — **implemented** (`test_operator_business_context.py`) |
| **T14-OC-3** | n8n Set node “Add Business Context” — **implemented** (exec **68–71** on earlier barbershop context; later switched to Alpstein copy) |

### Responsibility split (engineering decision)

| Layer | Responsibility |
|-------|----------------|
| `tenant_business_profiles` (DB) | Stable business identity / capabilities |
| `operator_business_context` (n8n → webhook) | Runtime operator notes, office rules, demo tweaks |
| Platform + task + greeting | Behavior authority |

### Investigation outcome (**implemented** analysis, **partial** fix)

- Task `T14-Investigate-why operator_business_context.md`: technical path worked (field reached Prompt Builder) but **DB `tenant_ai_profiles` / behavior** and **conversation history** still dominated (German-only onboarding loops, repetitive name asks).
- Fix path: config/content + demo separation + greeting orchestration — **not** moving prompts to n8n.

---

## 9. Langfuse / observability

**Status:** **implemented**, **experimental / dev-only**.

- `LangfuseTracingService` wraps `AiReplyOrchestrationService.generate_reply`.
- Enable: `LANGFUSE_*` keys + `LANGFUSE_TRACING_ENABLED` or auto in dev environments (`docs/architecture/langfuse-tracing.md`).
- Observations: span `ai_reply_orchestration` (greeting mode, language, operator context, assembled prompt metadata); generation `openai_chat_completion`.
- Session id = `conversation_id`.
- **Not** production-mandatory; secrets never traced.
- Used to diagnose **prompt noise** and **duplicated context** (Bitrix/HubSpot lists in `tenant_business_context`).

**Missing for production ops:** centralized log/metrics stack, alert on AI failure rate, trace retention policy — **planned**.

---

## 10. Multi-channel attribution architecture

**Status:** **partial** — contract + validation only.

| ID | Status |
|----|--------|
| ATTR design | `specs/architecture/channel-source-attribution.md` — **implemented** (spec) |
| **ATTR-2** | Pydantic: `source`, `attribution`, `message.client`, prefixed `message.external_conversation_id` — **implemented** (`webhook_attribution.py`, tests) |
| **ATTR-3** | Persist to `conversations` / `messages.metadata` — **planned** |
| **ATTR-4** | Prompt Builder `channel_source_context` — **planned** |
| **ATTR-5** | Lead snapshot on create — **planned** |
| **ATTR-6** | n8n adapter docs (WhatsApp, website) — **planned** |

**Principles:** `channel` remains Alpstein routing key; attribution never in `message.text`; no secrets in attribution objects.

Telegram MVP adapter: **does not** send attribution block yet — payloads remain valid without it.

---

## 11. Major architecture pivots

| Pivot | From → To | When |
|-------|-----------|------|
| AI in backend only | n8n/OpenAI considered → Gateway-only in Python | 2026-05-24 decision |
| Real AI on webhook | Stub reply → T11 orchestration | 2026-05-24 |
| Webhook security | Open route → T10-F1 token | 2026-05-24 |
| Leads in backend | n8n CRM writes rejected → `LeadService` + policy | 2026-05-24 T12 |
| Owner vs customer Telegram | Single bot risk → dual-bot credential model | 2026-05-25 T14.2 |
| Demo business isolation | `demo_barbershop_001` reused for Alpstein tests → `alpstein_ai_demo_001` | 2026-05-25 |
| Operator context transport | `raw_payload` / ignored extras → explicit `operator_business_context` | 2026-05-25 T14-OC |
| Greeting control | Implicit model behavior → `GreetingPolicyService` in task layer | 2026-05-25 |

**Non-pivot (explicitly rejected):** prompt assembly in n8n; n8n→PostgreSQL; tenant override of platform system prompt.

---

## 12. Current system state

### Works end-to-end (**implemented**)

```text
[Test webhook OR Telegram Trigger]
  → n8n normalize (+ optional operator context)
  → POST /api/v1/webhook/message (token auth)
  → WebhookMessageService
       → persist customer message (idempotent)
       → AI orchestration (non-duplicate) OR skip AI (duplicate)
       → lead create/update + notification policy
  → JSON response (reply, flags, optional lead/notification)
  → n8n shape reply → Telegram Send (customer bot)
  → optional owner Telegram (Alpstein bot)
```

### Backend (**implemented**)

- FastAPI, async SQLAlchemy, migrations through `0007`.
- **308** pytest test functions in `backend/tests/` as-of 2026-05-27 (includes greeting, Langfuse, attribution, operator context, conversation intent).
- Services pattern without repositories.

### n8n (**implemented** workflows; **partial** ops maturity)

- Test workflow + Telegram ingress workflow in repo (`active: false` in export; runtime ids documented in ops).
- HTTPS, env-driven backend URL, no secrets in git exports (scrub discipline — T14.6 **planned** formal gate).

### Partial

| Area | Gap |
|------|-----|
| `current-state.md` | Regenerated 2026-05-27 — verify quarterly or after major slices |
| Telegram T14.5–T14.6 | Regression + export gate not closed |
| Attribution | Schema only; no persistence |
| Production compose | Not single documented stack |
| Concurrent duplicate race | T10-F3 `IntegrityError` handling **optional / deferred** |
| WhatsApp ingress | **Deferred** |

### Intentionally deferred

- T13.6 structured retries and error taxonomy.
- T13.7 full cross-channel E2E checklist.
- ATTR-3–ATTR-7 attribution pipeline.
- Dashboard, billing, vector DB, queues, microservices (MVP scope exclusions).
- DB-backed operator context UI (n8n Set node is MVP stand-in).

### Experimental

- Langfuse tracing (dev/internal).

---

## 13. Current prompt hierarchy

**Authority order (high → low):**

1. **`platform_system`** — `prompt_templates.system_prompt` (platform-owned).
2. **`task_instructions`** — `reply_to_customer` task + **greeting block** (history-derived).
3. **`tenant_business_context`** — DB `tenant_business_profiles` + **`OPERATOR BUSINESS NOTES`** (webhook, if present).
4. **`tenant_behavior`** — `tenant_ai_profiles` (tone, language, ask_for_name, handoff, fallback text reference).
5. **`channel_rules`** — `tenant_channel_settings` for current `channel`.
6. **`knowledge`** — retrieved snippets from `tenant_knowledge_sources`.
7. **`conversation_history`** — last N messages (`customer` / `ai` / `owner`).
8. **`current_customer_message`** — always last; same text may exist in history but section 8 is mandatory.

**Truncation:** variable sections trimmed in order `channel_rules` → `tenant_behavior` → `tenant_business_context` → `knowledge` → `conversation_history` when over budget.

**Explicitly excluded from assembly:** `raw_payload`, webhook envelope, provider IDs (except via safe future attribution block).

---

## 14. Current Telegram runtime flow

**Workflow name:** `alpstein-incoming-message-telegram`  
**Repo:** `n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json`  
**Runtime id (last documented):** `2lMuaSWD1XFOXLEK` (deactivated post-test)

```text
Telegram Trigger          [@alpsteinai_0001bot — client credential]
  → Normalize               [channel=telegram, business_id=alpstein_ai_demo_001,
                             external_message_id=tg:{chat}:{msg}, phone=null]
  → Add Business Context    [operator_business_context — Alpstein AI copy]
  → POST Backend            [X-Alpstein-Webhook-Token]
       ├─ success → Shape Telegram Customer Reply → Telegram Send (telegram_chat_id)
       ├─ success → IF notify_owner → Shape Owner Notification → Telegram Owner Notify
       │              [@AlpsteinAIbot + TELEGRAM_CHAT_ID]
       └─ error   → Format Telegram Backend Error → Telegram Send (safe generic text)
```

**Parallel fan-out:** customer Send and owner notify are siblings after POST Backend (not sequential).

**Env:** `BACKEND_BASE_URL`, `N8N_BACKEND_API_TOKEN`, `TELEGRAM_CHAT_ID` (owner only).

---

## 15. Testing / review discipline

### Implemented discipline

- **Slice-based tasks** — one concern per agent session (T2–T14-OC).
- **Spec-first** — AGENTS.md + `specs/` before code.
- **Focused pytest** per service; integration suite `test_t11_ai_webhook_integration.py`.
- **Webhook contract tests** — schemas, auth, response shape, lead wiring, HTTP regression (T12.7).
- **No commit without human review** — project rule.
- **Post-task docs** — `completed.md`, ops runbooks, task files in `tasks/done/`.
- **n8n verification** — execution IDs recorded (Gate 1/2, T14.4, T14-OC-3, greeting **89–91**).

### Review conclusions (engineering)

| Review | Conclusion |
|--------|------------|
| T11 orchestration plan | OpenAI only in Gateway; coordinator skips AI on duplicate; T10-F1 blocker for production n8n |
| T14.1 contract | No `external_conversation_id` on body; retain `telegram_chat_id` in n8n only |
| T14-OC investigation | Operator context reaches Prompt Builder but DB AI profile + history can override perceived behavior |
| Tenant business context refactor | Marketing-style DB profile caused hallucination pressure; shorten to grounded facts |
| Demo separation | Shared `business_id` caused domain contamination — separate `alpstein_ai_demo_001` |
| Telegram credentials | Never mix owner and customer bot credentials |

### Gaps (**planned**)

- Formal T14.5 regression sign-off on Telegram path.
- ATTR integration tests after persistence.
- Load / concurrency testing for idempotency race (T10-F3).

---

## 16. Major mistakes / discoveries

### Discovered problems (with mitigations)

| Problem | Discovery | Mitigation status |
|---------|-----------|-------------------|
| **History pollution** | Old `ai` messages with repetitive German onboarding looped in `conversation_history` | Greeting policy reduces re-intro; **does not delete history** — new conversation/customer required (**partial**) |
| **Hallucination pressure** | Long CRM/platform lists in `tenant_business_context` (Bitrix24, HubSpot, Salesforce) | DB content refactor for `alpstein_ai_demo_001` (**implemented** content); Langfuse used to verify |
| **Prompt noise** | Duplicated meaning between DB profile and `operator_business_context` | Split responsibilities: DB = stable facts, operator = runtime rules (**implemented** policy); still requires discipline |
| **Business context contamination** | `demo_barbershop_001` used for Alpstein Telegram tests | Separate business + profiles (**implemented**); n8n switched `business_id` (**implemented**) |
| **Operator context “ignored”** | Field worked technically; behavior unchanged | Traced to `tenant_ai_profiles` (language, ask_for_name) + history — investigation doc; greeting + profile cleanup (**partial**) |
| **Misleading `raw_payload` path** | Extra top-level fields silently dropped; `raw_payload` stored but not used for AI | T14-OC explicit field + spec forbids raw_payload as primary business path (**implemented**) |
| **n8n silent drops** | Non-text / non-private Telegram updates | By design — workflow stops with no item (**documented**) |
| **Synthetic chat Send failures** | `chat not found` on injected tests | Expected — real DM to `@alpsteinai_0001bot` for Send verification (**known**) |

### Process mistakes (retrospective)

- Reusing one demo `business_id` for multiple personas before data model separation.
- Treating `operator_business_context` as sufficient without aligning `tenant_ai_profiles` and clearing toxic history.
- `docs/project-status/current-state.md` not updated after T13/T14 — risks false onboarding picture (**technical debt: docs**).

---

## 17. Current roadmap

### P0 — Close Telegram + ops (**planned**)

| ID | Task | Status |
|----|------|--------|
| **T14.5** | Owner-notify + duplicate regression on Telegram ingress | **Planned** (unblocked after greeting switch) |
| **T14.6** | Scrubbed workflow export + ops sign-off | **Planned** |

### P1 — Attribution persistence (**planned**)

| ID | Task |
|----|------|
| **ATTR-3** | Persist attribution subset to conversation/message metadata |
| **ATTR-4** | Prompt Builder safe attribution block |
| **ATTR-5** | Lead snapshot |
| **ATTR-6** | Adapter mapping docs (WhatsApp, website) |

### P1 — Stability (**planned / optional**)

| ID | Task |
|----|------|
| **T10-F3** | `IntegrityError` race on concurrent duplicate `external_message_id` |
| **T13.6** | n8n retry/error taxonomy |

### P2 — Channels & product (**deferred**)

- WhatsApp ingress (T13-W*).
- T13.7 full E2E checklist.
- DB-backed operator context (replace n8n Set node).
- Structured `operator_business_context` JSON renderer.
- Production Langfuse / metrics.
- Dashboard, billing, vector search — **out of MVP scope**.

### Recommended next engineering task

**T14.5** — Prove Telegram path preserves T13.5 owner-notify and duplicate semantics before T14.6 export freeze.

---

## Appendix A — Task index (implemented unless noted)

| Slice | IDs |
|-------|-----|
| Persistence | T2–T8.1, T6 idempotency index |
| Webhook | T9 schemas, T10 route + orchestration, T10-F1 auth |
| AI | T11.1–T11.16 |
| Leads / notify | T12.1–T12.7 |
| n8n | T13.0–T13.5, Gate 1–2 |
| Telegram | T14.1–T14.4 **done**; T14.5–T14.6 **planned** |
| Operator context | T14-OC-1–OC-3 **done** |
| Attribution | ATTR-2 **done**; ATTR-3+ **planned** |
| Greeting | Backend MVP **done**; n8n switch **done** |
| Demo data | Separation + tenant_business_context refactor **done** |

## Appendix B — Key file map

| Concern | Path |
|---------|------|
| Webhook schema | `backend/app/schemas/webhook.py`, `webhook_attribution.py` |
| Webhook orchestration | `backend/app/services/webhook_message_service.py` |
| AI orchestration | `backend/app/services/ai_reply_orchestration_service.py` |
| Prompt assembly | `backend/app/services/prompt_builder_service.py` |
| Greeting | `backend/app/services/greeting_policy_service.py` |
| Langfuse | `backend/app/services/langfuse_tracing_service.py` |
| Canonical specs | `specs/architecture/prompt-builder-rules.md`, `specs/api/webhooks.md` |
| Ops | `docs/ops/n8n-workflow-telegram-customer-ingress.md` |
| Status | `docs/project-status/completed.md`, `next-steps.md` |

## Appendix C — Technical debt & architectural risks

| Item | Severity | Notes |
|------|----------|-------|
| Stale `current-state.md` | Medium | Misstates n8n/AI integration status |
| History not auto-healed | Medium | Bad loops persist until new conversation |
| Operator + DB context overlap | Low–Medium | Requires operational discipline |
| Attribution not persisted | Medium | Analytics/CRM incomplete |
| Single-host backend URL in n8n | Medium | Docker bridge IP documented — fragile if network changes |
| No webhook retry idempotency at n8n | Medium | T13.6 deferred |
| Langfuse in dev only | Low | Limited production observability |
| Tenant prompt injection via profiles | Ongoing | Mitigated by ordering; not eliminated |
| Concurrent duplicate insert race | Low | T10-F3 optional |

---

*This archive should be updated when T14.5/T14.6 close or ATTR-3 ships. Do not mark items complete here without matching `completed.md` or merged task evidence.*
