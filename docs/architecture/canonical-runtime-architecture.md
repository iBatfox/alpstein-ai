**Doc status:** canonical  
**Tier:** architecture/canonical (live path: `docs/architecture/`)  
**As-of:** 2026-05-27 — runtime truth only; not future architecture

# Alpstein AI — Canonical Runtime Architecture

## 1. Status

| Field | Value |
|-------|--------|
| **Document status** | Canonical runtime map (Phase 1 — canonicalization) |
| **As-of date** | 2026-05-27 (HF-1 patch) |
| **Scope** | Runtime truth only — not future architecture, not marketing |

**Evidence sources used (priority order applied):**

1. Backend: `backend/app/services/*`, `backend/app/api/routes/webhook.py`, `backend/app/models/*`
2. Migrations: `backend/alembic/versions/0001`–`0007`
3. Tests: `backend/tests/*` (308 `test_*` functions counted; green status not re-verified this sweep)
4. n8n exports: `n8n/workflows/t13_workflow1_test_webhook_skeleton.json`, `n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json`
5. Ops: `docs/ops/n8n-workflow1-test-webhook.md`, `docs/ops/n8n-workflow-telegram-customer-ingress.md`
6. Project status: `docs/project-status/current-state.md`, `completed.md`, `next-steps.md`, `engineering-audit-report.md`
7. Architecture behavior docs: `docs/architecture/*` (where runtime-aligned)
8. Specs: `specs/api/webhooks.md`, `specs/architecture/prompt-builder-rules.md` (contract reference; runtime wins on conflict)
9. Tasks: `tasks/done/*`, `tasks/todo/t14-telegram-customer-ingress.md`

**Explicit note:** This document describes **what runs today**. Planned systems (ATTR-3, CIP-C/D) are listed only as gaps or drift — not as implemented behavior unless marked implemented.

---

## 2. System purpose

Alpstein AI is a **backend-centered AI reply orchestration system** for multi-tenant SMB messaging:

- **Python FastAPI backend** owns validation, tenant/business resolution, conversation persistence, lead logic, AI orchestration, prompt assembly, and OpenAI calls.
- **n8n** is the ingress and automation layer: receives channel events, normalizes payloads, calls the backend, sends customer replies, and optionally notifies the business owner.
- **PromptBuilder** assembles an eight-section provider-neutral prompt per turn; conversational control (greeting, intent slices, pre-sales charter/appendix) lives in §2 `task_instructions`.
- **PostgreSQL** stores tenants, businesses, conversations, messages, leads, AI configuration, and `prompt_runs` audit rows.
- **Observability:** `PromptRun` DB trail (all environments when AI runs); **Langfuse** tracing (dev/internal only when keys + environment allow).
- **Telegram** is the only live customer ingress path documented with runtime evidence; test webhook path exists for Gate 1/2 verification.

Not in runtime scope: CRM admin panel, vector DB, billing, self-service onboarding UI, n8n→PostgreSQL writes.

---

## 3. Actual runtime request lifecycle

End-to-end path for a **non-duplicate** Telegram customer message (primary production-shaped path):

| Step | Action | Status |
|------|--------|--------|
| 1 | Customer sends text to Telegram customer bot (`alpsteinai_0001bot`) | **implemented** |
| 2 | n8n `Telegram Trigger` receives update; non-private/non-text/bot/edited updates dropped | **implemented** ([`t14_workflow_telegram_customer_ingress_skeleton.json`](../../n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json)) |
| 3 | `Normalize Telegram Incoming` builds normalized JSON: `channel=telegram`, `business_id=alpstein_ai_demo_001` (env override), `external_message_id=tg:{chat}:{msg}` | **implemented** |
| 4 | `Add Business Context` injects `operator_business_context` (transport-only, not persisted) | **implemented** |
| 5 | `POST Backend` → `POST /api/v1/webhook/message` with `X-Alpstein-Webhook-Token` | **implemented** ([`webhook.py`](../../backend/app/api/routes/webhook.py)) |
| 6 | Backend validates token (`require_webhook_token`) and Pydantic request (`NormalizedWebhookMessageRequest`) | **implemented** |
| 7 | `BusinessService.get_by_external_id` resolves tenant; customer + open conversation created/reused | **implemented** ([`webhook_message_service.py`](../../backend/app/services/webhook_message_service.py)) |
| 8 | `MessageService.save_incoming_customer_message` — idempotency via `(business_id, external_message_id)` lookup | **implemented**; concurrent race **partial** (T10-F3 not handled) |
| 9 | Duplicate path: skip lead/notify; coordinator skips AI; replay last AI reply or safe ack | **implemented** |
| 10 | Non-duplicate: `LeadSignalDetectionService` keywords; `LeadService` create/update; `NotificationPolicyService` | **implemented** |
| 11 | `AiReplyOrchestrationCoordinator` → `AiReplyOrchestrationService.generate_reply` | **implemented** |
| 12 | Load AI config, knowledge, history (10–20 msgs); `GreetingPolicyService.resolve`; `ConversationIntentService.resolve` if `alpstein_ai_demo_001` | **implemented** / **partial** (intent: one business only) |
| 13 | `PromptBuilderService.build_reply_to_customer` → `AssembledPrompt` | **implemented** |
| 14 | `LangfuseTracingService.trace_ai_reply` (no-op if disabled) → `AiGatewayService.complete` (OpenAI HTTP) | **implemented** / **partial** (Langfuse dev-only) |
| 15 | `PromptRunService.create_prompt_run`; outgoing AI message persisted on success/fallback | **implemented** |
| 16 | Webhook JSON: `reply_to_customer`, `lead_*`, `notify_owner`, optional `notification` | **implemented** |
| 17 | n8n `Shape Telegram Customer Reply` → `Telegram Send Message` to customer `chatId` | **implemented** |
| 18 | Parallel: `IF Notify Owner` on `$('POST Backend')` → owner Telegram (`AlpsteinAIbot`, `TELEGRAM_CHAT_ID`) | **implemented** (T13.5 pattern); T14.5 regression gate **open** |

**Test webhook path:** Same backend contract via `alpstein-incoming-message-test` workflow; `channel=test`, default `demo_barbershop_001` unless env override — **implemented**, repo export `active: false`.

**Uncertain / ops-dependent:** Whether runtime n8n workflow `2lMuaSWD1XFOXLEK` is currently active; ops doc states deactivated post-test. Repo exports are **not** active by default.

---

## 4. Backend architecture

All components below exist in code unless marked otherwise.

### Entry and orchestration

| Component | Role | Source |
|-----------|------|--------|
| `POST /api/v1/webhook/message` | HTTP entry, commit/rollback, error envelope | [`backend/app/api/routes/webhook.py`](../../backend/app/api/routes/webhook.py) |
| `WebhookMessageService` | Full message pipeline: resolve entities, dedupe, lead, AI reply, notify flags | [`webhook_message_service.py`](../../backend/app/services/webhook_message_service.py) |
| `AiReplyOrchestrationCoordinator` | Skips AI chain when `is_duplicate` | [`ai_reply_orchestration_coordinator.py`](../../backend/app/services/ai_reply_orchestration_coordinator.py) |
| `AiReplyOrchestrationService` | Config → knowledge → history → greeting → intent → prompt → gateway → PromptRun | [`ai_reply_orchestration_service.py`](../../backend/app/services/ai_reply_orchestration_service.py) |
| `AiReplyFallbackService` | Tenant/platform fallback when gateway fails or empty text | [`ai_reply_fallback_service.py`](../../backend/app/services/ai_reply_fallback_service.py) |

### AI and prompt

| Component | Role | Source |
|-----------|------|--------|
| `AiConfigurationService` | Loads tenant/business profiles, channel rules, platform templates | [`ai_configuration_service.py`](../../backend/app/services/ai_configuration_service.py) |
| `KnowledgeRetrievalService` | Token-ranked snippets from `tenant_knowledge_sources` | [`knowledge_retrieval_service.py`](../../backend/app/services/knowledge_retrieval_service.py) |
| `PromptBuilderService` | Eight-section assembly, trim budget | [`prompt_builder_service.py`](../../backend/app/services/prompt_builder_service.py) |
| `ConversationIntentService` | Heuristic intent for current turn | [`conversation_intent_service.py`](../../backend/app/services/conversation_intent_service.py) |
| `GreetingPolicyService` | FIRST_CONTACT / FOLLOW_UP / SOFT_RETURN + reply language | [`greeting_policy_service.py`](../../backend/app/services/greeting_policy_service.py) |
| `AiGatewayService` | Sole OpenAI HTTP (`app/services/ai_gateway/_openai.py`) | [`ai_gateway_service.py`](../../backend/app/services/ai_gateway_service.py) |
| `PromptRunService` | Persists execution audit (`final_prompt` redacted, not in API) | [`prompt_run_service.py`](../../backend/app/services/prompt_run_service.py) |
| `LangfuseTracingService` | Optional dev spans + generation observations | [`langfuse_tracing_service.py`](../../backend/app/services/langfuse_tracing_service.py) |

### Domain and persistence helpers

| Component | Role | Source |
|-----------|------|--------|
| `BusinessService`, `CustomerService`, `ConversationService` | Entity resolution for webhook | respective `*_service.py` |
| `MessageService` | Incoming/outgoing messages, history load, idempotency lookup | [`message_service.py`](../../backend/app/services/message_service.py) |
| `LeadService` | Active lead find/create/update | [`lead_service.py`](../../backend/app/services/lead_service.py) |
| `LeadSignalDetectionService` | MVP keyword heuristics (urgent, handoff) | [`lead_signal_detection_service.py`](../../backend/app/services/lead_signal_detection_service.py) |
| `NotificationPolicyService` | Pure policy → `notify_owner` + notification type | [`notification_policy_service.py`](../../backend/app/services/notification_policy_service.py) |
| `validate_tenant_context` | Cross-entity tenant/business consistency | [`tenant_context_validator.py`](../../backend/app/services/tenant_context_validator.py) |

### Transport fields (not persisted as business config)

- `operator_business_context` — validated on webhook, passed through orchestration, appended in PromptBuilder §3 overlay; **not** stored in DB; **not** in webhook response ([`webhook.py`](../../backend/app/schemas/webhook.py), T14-OC-2).
- `source`, `attribution` — ATTR-2 Pydantic validation only; **not** read by `WebhookMessageService` — **spec-only persistence path**.

No repository layer — services use `AsyncSession` directly (**intentional MVP**).

---

## 5. PromptBuilder runtime flow

Canonical section order ([`assembled_prompt.py`](../../backend/app/schemas/assembled_prompt.py)):

```text
1. platform_system          (§1 — system kind)
2. task_instructions        (§2 — system kind)
3. tenant_business_context  (§3 — data)
4. tenant_behavior          (§4 — data)
5. channel_rules            (§5 — data)
6. knowledge                (§6 — data)
7. conversation_history     (§7 — data)
8. current_customer_message (§8 — data)
```

### §1 Platform system

- Content from platform `prompt_templates.system_prompt` via `AiConfigurationService`.
- **Status:** **implemented**

### §2 Task instructions

Built by `_build_task_instructions_body` ([`prompt_builder_service.py`](../../backend/app/services/prompt_builder_service.py)):

1. Base `reply_to_customer` task registry text (always).
2. **Alpstein product path** (`alpstein_product_behavior_enabled=True`, only `alpstein_ai_demo_001`):
   - `PRE_SALES_CORE_CHARTER` + one `build_intent_instruction_block(intent)` slice.
   - **Status:** **implemented**
3. **Non-Alpstein path** (all other businesses):
   - Core task + generic greeting block only; no pre-sales charter or intent slices.
   - **Status:** **implemented**
4. **Greeting block** (when `GreetingPolicy` resolved):
   - Appended via `build_greeting_instruction_block` (`alpstein_greeting` flag selects intro variant).
   - **Status:** **implemented**

`PRE_SALES_TASK_APPENDIX` was removed from the codebase in P1 (2026-05-27); it is not assembled at runtime.

### §3 Tenant business context

- DB `tenant_business_profiles` text + optional `OPERATOR BUSINESS NOTES` from webhook.
- Operator notes appended after DB profile; labeled reference data.
- **Status:** **implemented**

### §4 Tenant AI behavior

- From `tenant_ai_profiles` (tone, language prefs, fallback text reference, handoff flags).
- **Status:** **implemented**

### §5 Channel rules

- From `tenant_channel_settings` for active channel.
- **Status:** **implemented**

### §6 Knowledge

- From `KnowledgeRetrievalService` snippets.
- **Status:** **implemented**

### §7 Conversation history

- Last 10–20 messages, customer/ai/owner senders, oldest→newest.
- **Status:** **implemented**
- **History Safety (HF-1):** When dialogue lines exist, `HISTORY_SAFETY_PREAMBLE` is prepended inside §7 ([`history_safety_prompt_instructions.py`](../../backend/app/services/history_safety_prompt_instructions.py)); prior `ai` rows use label `ai (dialogue only, not business facts)`. Preamble states current tenant profile, operator notes, knowledge, and task instructions override stale assistant content in history. Trim budget treats preamble separately from dialogue lines ([`_build_conversation_history`](../../backend/app/services/prompt_builder_service.py)). Tests: `tests/test_history_safety_prompt_builder.py`.
- **Status (HF-1):** **implemented**
- When history is empty, §7 is omitted or shows `(not provided)` — no preamble injected.

### §8 Current customer message

- Capped at 8,000 chars with truncation marker.
- **Status:** **implemented**

### Trim behavior

- Total assembly budget: 24,000 chars (`PROMPT_ASSEMBLY_MAX_CHARS`).
- Fixed sections: §1, §2, §8.
- Variable sections §3–§7 trimmed in order: `channel_rules` → `tenant_behavior` → `tenant_business_context` → `knowledge` → `conversation_history`.
- **Status:** **implemented**

---

## 6. Conversational orchestration

| Area | Runtime behavior | Status |
|------|------------------|--------|
| **Intent routing** | Rule-based `ConversationIntentService`; enabled only when `business.external_id == alpstein_ai_demo_001` ([`conversation_intent_policy.py`](../../backend/app/services/conversation_intent_policy.py)) | **partial** (one business) |
| **Intent types** | confused, pricing_interest, implementation_interest, technical_interest, technical_how, off_topic, social_greeting, unsupported_system, etc. | **implemented** (heuristics) |
| **Named CRM/ERP** | Routes to `unsupported_system` before `implementation_interest` unless technical-how patterns match | **implemented** |
| **Greeting orchestration** | Modes from history + 24h inactivity; language from message + Telegram `language_code` in raw_payload | **implemented** |
| **History handling** | §7 loads 10–20 recent messages; HF-1 preamble in §7 marks history as dialogue-only; `ai` sender labeled non-authoritative for business facts; current context sections override stale assistant turns | **implemented** |
| **Lead qualification** | Every non-duplicate message creates or updates a lead; not LLM-based | **implemented** |
| **notify_owner relation** | `NotificationPolicyService`: urgent > handoff > ai_failure > new_lead; duplicates suppress; lead_updated-only suppresses | **implemented** |
| **Pricing behavior** | Intent slice `pricing_interest` when matched (Alpstein demo only); non-Alpstein relies on core task + tenant/operator context | **partial** |
| **Off-topic behavior** | Intent `off_topic` + instruction block (Alpstein demo only); non-Alpstein relies on core task | **partial** |
| **Unsupported systems** | Dedicated intent + block when named ERP/CRM without feasibility framing | **implemented** (Alpstein demo) |

Ideal behaviors described only in `docs/architecture/conversation-intent-policy-mvp.md` but not coded (e.g. CIP-C Langfuse fields, CIP-D live smoke) are **not** runtime truth.

---

## 7. n8n ingress topology

### Role (actual)

| Responsibility | Owner |
|----------------|--------|
| Channel triggers (Telegram, test webhook) | n8n |
| Payload normalization to backend contract | n8n Code nodes |
| `operator_business_context` injection | n8n Set node (Telegram path) |
| HTTP to backend with shared token | n8n |
| Customer reply delivery | n8n (Telegram Send / Respond to Webhook) |
| Owner notification | n8n (separate bot credential) |
| AI, prompts, leads, DB writes | **backend only** |
| PostgreSQL writes | **backend only** (MVP rule) |

### Workflows in repo

| Export name | File | Repo `active` | Purpose |
|-------------|------|---------------|---------|
| `alpstein-incoming-message-test` | `t13_workflow1_test_webhook_skeleton.json` | `false` | Test channel; Gate 1 + Gate 2 owner notify |
| `alpstein-incoming-message-telegram` | `t14_workflow_telegram_customer_ingress_skeleton.json` | `false` | Telegram customer ingress |
| `My workflow 2` | `My_workflow.json` | `false` | Ad-hoc/partial export — **not canonical** |

### Runtime vs repo

- Documented runtime workflow id (Telegram): `2lMuaSWD1XFOXLEK` — ops note: **deactivated post-test**.
- **Drift:** Active runtime workflows may differ from repo exports until T14.6 export gate closes.
- n8n Docker: `127.0.0.1:15679`, public `https://n8n.alpstein-ai.ch`.

### Owner notify pattern

- Conditions read `$('POST Backend')` fields: `notify_owner`, `notification`, not duplicate.
- Telegram ingress: customer reply and owner notify are **sibling branches** from POST success (not serial).

---

## 8. Telegram flow

| Element | Runtime detail | Status |
|---------|----------------|--------|
| **Customer bot** | Credential `alpsteinai_0001bot`; trigger on `message` | **implemented** |
| **Owner bot** | Credential `AlpsteinAIbot`; uses `TELEGRAM_CHAT_ID` env | **implemented** |
| **Business id** | Default `alpstein_ai_demo_001` in normalize node | **implemented** |
| **Chat id** | Customer send uses normalized `telegram_chat_id`; not owner env var | **implemented** |
| **external_message_id** | `tg:{chat_id}:{message_id}` | **implemented** |
| **Dedupe** | Backend lookup by `(business_id, external_message_id)`; duplicate suppresses lead + notify + AI | **implemented** |
| **operator_business_context** | Set in n8n; Alpstein AI product context (post greeting switch) | **implemented** |
| **Contact block in n8n** | Pre-sales contact ownership: backend prompts scrubbed; ops contact block in n8n **partial** (documented, not verified this sweep) | **partial** |

### Open gates

| ID | Description | Status |
|----|-------------|--------|
| **T14.5** | Owner-notify + duplicate regression on Telegram path | **open** ([`tasks/todo/t14-telegram-customer-ingress.md`](../../tasks/todo/t14-telegram-customer-ingress.md)) |
| **T14.6** | Scrubbed export + repo as source of truth | **open** |

---

## 9. Database and persistence

### Migrations (verified in repo)

| Rev | Tables / change |
|-----|-----------------|
| `0001` | `tenants`, `businesses` |
| `0002` | `customers` |
| `0003` | `conversations` |
| `0004` | `messages` |
| `0005` | Partial unique index `(business_id, external_message_id)` WHERE NOT NULL |
| `0006` | AI config tables + `prompt_templates`, `prompt_runs` |
| `0007` | `leads` |

### Active persistence per request

| Data | Persisted | Notes |
|------|-----------|-------|
| Customer, conversation | Yes | get-or-create |
| Incoming message | Yes | unless duplicate returns existing row |
| Outgoing AI message | Yes | on successful/fallback reply |
| Lead | Yes | create or update on non-duplicate |
| PromptRun | Yes | on every AI execution attempt |
| operator_business_context | **No** | transport-only |
| source / attribution (ATTR-2) | **No** | validated at boundary only |
| Langfuse traces | External SaaS | dev-only when enabled |

### Gaps

| Gap | Status |
|-----|--------|
| ATTR-3+ attribution persistence | **planned** |
| T10-F3 concurrent duplicate race | **deferred** optional hardening |
| operator_business_context DB storage | **out of MVP** (by design) |

---

## 10. Multi-tenant model

### Isolation (implemented)

- Client-owned rows carry `tenant_id`; business-scoped rows carry `business_id`.
- Services filter by `tenant_id` (and `business_id` where applicable); `validate_tenant_context` on cross-entity operations.
- Business lookup for webhook: `business_id` string = `businesses.external_id` (global unique).

### Demo businesses (runtime)

| external_id | Role | Intent policy | Typical path |
|-------------|------|---------------|--------------|
| `alpstein_ai_demo_001` | Alpstein AI product demo | **enabled** | Telegram ingress (n8n default) |
| `demo_barbershop_001` | Legacy barbershop seed | **disabled** (product behavior) | Test webhook default, many unit tests |

### Hardcoded gates

- `intent_policy_enabled_for_business` — exact match on `alpstein_ai_demo_001` only ([`conversation_intent_policy.py`](../../backend/app/services/conversation_intent_policy.py)).
- Dev seed creates barbershop demo data ([`dev_ai_configuration.py`](../../backend/app/seed/dev_ai_configuration.py)); separate Alpstein demo business added for Telegram separation.

### operator_business_context ownership

- **Owned by:** n8n operator (Set node) per request.
- **Consumed by:** backend PromptBuilder §3 overlay only.
- **Not tenant-config UI;** not versioned; not merged into DB profile.

### Contamination risks (factual)

| Risk | Detail |
|------|--------|
| History vs operator context | HF-1 preamble instructs model to prefer current operator/tenant context over stale `ai` lines; LLM may still err — not a versioning system |
| Langfuse demo tag | Tag `alpstein_ai_demo_001` applied when `business_external_id == demo_barbershop_001` ([`langfuse_tracing_service.py`](../../backend/app/services/langfuse_tracing_service.py)) — misleading trace labels |
| Single-business intent | Other tenants do not get intent slices; behavior differs by `external_id` |

### Non-Alpstein tenant behavior

- Any business except `alpstein_ai_demo_001`: core task + generic greeting only; no pre-sales charter, no intent slices, no Alpstein product intro.
- Multi-tenant data model supports multiple tenants; production rollout rules beyond demo seeds are **not** encoded in runtime policy services.

---

## 11. Observability

| Mechanism | State | Limitations |
|-----------|-------|-------------|
| **PromptRun** (`prompt_runs` table) | **implemented** | `final_prompt` stored redacted; not exposed in webhook API |
| **Langfuse** | **partial** — active when keys set and (`LANGFUSE_TRACING_ENABLED` or env in `development/dev/local/test`) | Not production observability by default; failures swallowed |
| **Langfuse span metadata** | business_id, conversation_id, channel, greeting_mode, customer_language, operator_context preview, assembled_prompt dump | **implemented** |
| **Langfuse greeting tag** | `greeting_orchestration` | **implemented** |
| **Langfuse intent metadata** | Keys defined in [`langfuse_intent_trace.py`](../../backend/app/schemas/langfuse_intent_trace.py) | **not wired** to `_build_metadata` (CIP-C) |
| **n8n execution IDs** | Documented in ops/task files (e.g. exec 89–91) | Manual ops debugger; no automated link to PromptRun |
| **Webhook response** | No `final_prompt`, no operator context, no internal AI errors beyond fallback flag semantics | By design |

---

## 12. Runtime/spec drift table

| Area | Runtime truth | Docs/spec claim | Severity | Recommended owner |
|------|---------------|-----------------|----------|-------------------|
| **CIP-C Langfuse intent metadata** | Constants only; not in Langfuse metadata | `conversation-intent-policy-mvp.md` § CIP-C | **Important** | `alpstein-backend-engineer` |
| **ATTR persistence** | Schema validates; no DB write | Attribution design docs | **Important** | `alpstein-backend-engineer` + `alpstein-database-architect` |
| **Legacy appendix path** | Removed from codebase (P1); non-Alpstein uses minimal §2; Alpstein uses CIP charter + intent | Intent policy doc | **Resolved** (P0 + P1) | — |
| **Langfuse demo tag** | Tags `alpstein_ai_demo_001` when business is `demo_barbershop_001` | `langfuse-tracing.md` may imply Alpstein demo tag matches business | **Important** | `alpstein-backend-engineer` (CIP-C) |
| **n8n repo vs runtime** | Repo exports `active: false`; runtime id `2lMuaSWD1XFOXLEK` deactivated per ops | Some status docs historically said “missing n8n” | **Important** | `alpstein-n8n-integration-engineer` (T14.6) |
| **Intent in specs** | CIP behavior in `docs/architecture/` | `prompt-builder-rules.md` may not list intent §2 amendment | **Minor** | `alpstein-api-designer` / spec task |
| **operator contact in n8n** | Backend scrubbed; n8n contact block ops follow-up | `pre-sales-contact-ownership.md` | **Minor** | Ops + `alpstein-n8n-integration-engineer` |
| **Test count** | 308 test functions | Older docs cite 252 | **Minor** | `alpstein-project-archivist` on sweeps |

**Resolved drift (no longer open):** **HF-1 History Safety** — §7 preamble + non-authoritative `ai` dialogue labels (**implemented** in `history_safety_prompt_instructions.py` / `PromptBuilderService`); prior audit and plan task treated as spec-only.

---

## 13. Canonical boundaries

```text
┌─────────────────────────────────────────────────────────────┐
│  n8n: ingress, normalize, operator context inject, routing   │
│       customer reply send, owner notify — NO AI, NO DB       │
└───────────────────────────┬─────────────────────────────────┘
                            │ POST /api/v1/webhook/message
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend: validation, tenant scope, persistence, leads,      │
│           greeting + intent policy, PromptBuilder, Gateway,  │
│           PromptRun, webhook response flags                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     ┌─────────────────┐        ┌─────────────────┐
     │  PostgreSQL     │        │  OpenAI API     │
     │  (tenant data)  │        │  (via Gateway)  │
     └─────────────────┘        └─────────────────┘
              │
              ▼ (dev only)
     ┌─────────────────┐
     │  Langfuse       │  observes; does not control replies
     └─────────────────┘
```

| Boundary | Rule |
|----------|------|
| Backend owns AI orchestration | No OpenAI nodes in n8n |
| n8n owns ingress/automation routing | No business rules in n8n beyond normalize/shape |
| PromptBuilder owns prompt assembly | No prompt text assembly in n8n |
| DB owns tenant/conversation persistence | n8n must not write PostgreSQL |
| Langfuse observes | Does not change prompt or routing |
| Telegram | One implemented customer channel path; not the full multi-channel platform |

---

## 14. Non-canonical / out of scope

Not part of canonical runtime today:

- CRM control panel / ERPNext customer-facing product
- Vector DB / embeddings / long-term memory
- Autonomous multi-agent systems (LangGraph, etc.)
- WhatsApp / Instagram / website chat ingress (beyond schema placeholders)
- ATTR-3+ persistence
- Production Langfuse as operational requirement
- Billing, dashboard, self-service tenant onboarding UI
- Repository layer abstraction
- T13.6 structured retries, T13.7 full E2E checklist
- n8n PostgreSQL writes
- AI direct database modification
- Configurable per-tenant intent policy (hardcoded to one `external_id`)

---

## 15. Operational notes

| Topic | Note |
|-------|------|
| **Repo vs runtime drift** | Workflow JSON exports have `"active": false`; production activation is manual. T14.6 targets export hygiene. |
| **Workflow freeze** | Before re-import, document runtime id and deactivate to avoid duplicate Telegram triggers (one trigger per bot). |
| **Backend listener** | Documented dev/proof: `0.0.0.0:8010`, Docker bridge `172.20.0.1:8010` from n8n container — environment-specific. |
| **Rollback** | No unified compose rollback artifact; n8n workflow version in UI + git export; DB via Alembic replay ([`database-recovery.md`](../ops/database-recovery.md)). |
| **Documents to update when this map changes** | `docs/project-status/current-state.md`, `engineering-archive.md`, `next-steps.md`; link this file from `docs/architecture/` index when created |
| **My_workflow.json** | Non-canonical duplicate; do not treat as source of truth |

---

## 16. Open decisions

Unresolved — require human decision, not archivist resolution:

1. **Business-aware prompt assembly** — extend intent policy beyond `alpstein_ai_demo_001` vs keep single-business MVP.
2. **Langfuse metadata wiring** — CIP-C scope and priority.
3. **Active workflow export freeze** — T14.6 gate: which runtime id becomes repo canonical.
4. **Multi-tenant rollout rules** — how new businesses get intent policy, operator context, and seed data without contamination.
5. **Langfuse tag semantics** — fix barbershop→Alpstein tag mapping or document as intentional.
6. **Attribution persistence scope** — ATTR-3 column design and write path ownership.

---

## Source file index

| Topic | Path |
|-------|------|
| Webhook pipeline | [`backend/app/services/webhook_message_service.py`](../../backend/app/services/webhook_message_service.py) |
| AI orchestration | [`backend/app/services/ai_reply_orchestration_service.py`](../../backend/app/services/ai_reply_orchestration_service.py) |
| Prompt assembly | [`backend/app/services/prompt_builder_service.py`](../../backend/app/services/prompt_builder_service.py) |
| Intent gate | [`backend/app/services/conversation_intent_policy.py`](../../backend/app/services/conversation_intent_policy.py) |
| Telegram n8n export | [`n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json`](../../n8n/workflows/t14_workflow_telegram_customer_ingress_skeleton.json) |
| Test n8n export | [`n8n/workflows/t13_workflow1_test_webhook_skeleton.json`](../../n8n/workflows/t13_workflow1_test_webhook_skeleton.json) |
| Webhook contract spec | [`specs/api/webhooks.md`](../../specs/api/webhooks.md) |
| Prompt rules spec | [`specs/architecture/prompt-builder-rules.md`](../../specs/architecture/prompt-builder-rules.md) |
