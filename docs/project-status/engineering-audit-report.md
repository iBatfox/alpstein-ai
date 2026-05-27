**Doc status:** archived  
**Tier:** project-status/historical (pending move)  
**Note:** Findings partially remediated 2026-05-27; use [`documentation-topology-status.md`](documentation-topology-status.md) + canonical map for current state

# Alpstein AI — Engineering Audit Report

**Document type:** internal engineering audit (not marketing)  
**As-of:** 2026-05-25  
**Method:** repository review of `specs/`, `docs/`, `tasks/`, `backend/app/`, `n8n/workflows/` — no runtime changes performed  
**Rule:** status labels are **implemented** | **partial** | **spec-only** | **deprecated** | **planned** | **abandoned**

**Companion docs:** [`engineering-archive.md`](engineering-archive.md) (chronology), [`completed.md`](completed.md) (slice log), [`next-steps.md`](next-steps.md) (queue — **partially stale**)

---

## 1. Executive summary

### What Alpstein AI is (architecturally)

Alpstein AI is a **spec-driven, multi-tenant MVP** for SMB customer messaging automation:

- **n8n** receives provider webhooks, normalizes payloads, optionally attaches `operator_business_context`, calls **Python FastAPI** over HTTPS with a shared token.
- **Backend** owns business logic: tenant resolution, persistence, lead creation, notification policy, **AI orchestration** (configuration → knowledge → Prompt Builder → OpenAI via Gateway only → PromptRun audit).
- **PostgreSQL** stores tenants, businesses, customers, conversations, messages, leads, AI config tables, and `prompt_runs`. n8n does **not** write the DB in MVP.

The primary live integration path proven in ops docs is **Telegram customer ingress** (`alpstein_ai_demo_001`) plus **test webhook** and **owner Telegram notify** (dual-bot credential model).

### Maturity level

| Layer | Maturity |
|-------|----------|
| Specs (architecture, flows, schema) | **High** — broad coverage |
| Backend core + AI stack | **High** for MVP scope |
| Conversational behavior (intent, greeting, history safety) | **Medium** — intent/greeting implemented for one demo business; history safety **not** implemented |
| n8n / ops | **Medium** — workflows exist; T14.5–T14.6 and T13.6 not closed |
| Documentation hygiene | **Low–medium** — significant staleness and duplication |
| Production hardening | **Low** — dev-oriented tracing, optional idempotency race, no unified compose |

**Overall:** strong **vertical MVP backend** with **active prompt-engineering iteration**; weaker **documentation single source of truth** and **cross-business behavior consistency**.

### Biggest strengths

1. **Clear architectural boundaries** — backend owns AI; n8n owns transport; specs enforce this (AGENTS.md, decisions).
2. **Complete incoming-message slice** — webhook → persist → AI → lead → notify flags with tests (T10–T12, T11).
3. **Configuration-driven AI** — platform templates + tenant profiles + knowledge retrieval + PromptRun logging.
4. **Recent conversational refinements** — greeting orchestration, per-turn intent for Alpstein demo (CIP-A/B), operator context overlay (T14-OC), contact ownership cleanup.
5. **Operational evidence culture** — n8n execution IDs, Gate 1/2, Telegram ingress runbooks.

### Biggest risks

1. **Documentation drift** — `current-state.md`, `next-steps.md`, `engineering-archive.md`, and `backlog.md` contradict runtime (e.g. CIP marked “not implemented” in next-steps while CIP-B is done).
2. **History contamination** — HF-1 mitigates stale `ai` rows; LLM may still err — not a versioning system.
3. **Split-brain pre-sales behavior** — **resolved (P0 + P1):** Alpstein demo uses charter + intent; non-Alpstein uses core task + generic greeting only; legacy appendix removed from codebase.
4. **Langfuse tag drift** — demo tag still keyed to `demo_barbershop_001` constant, not `alpstein_ai_demo_001`; intent metadata (CIP-C) missing.
5. **Incomplete channel/attribution** — ATTR-2 validation only; no persistence or Prompt Builder block.
6. **Telegram ops gap** — T14.5 regression and T14.6 export scrub not signed off; workflow export `active: false`.

---

## 2. Current architecture map

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ n8n (transport)                                                          │
│  Telegram Trigger / Test Webhook → Normalize → [Add Business Context]   │
│  → POST /api/v1/webhook/message (X-Alpstein-Webhook-Token)              │
│  ← reply_to_customer, lead_*, notify_owner, notification                 │
│  → Shape reply → Telegram Send (customer bot)                           │
│  → IF notify_owner → Owner Telegram (Alpstein bot + TELEGRAM_CHAT_ID)   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ normalized JSON
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ FastAPI backend                                                          │
│  WebhookMessageService                                                   │
│    BusinessService → CustomerService → ConversationService               │
│    MessageService (idempotent save, history, outgoing ai)                │
│    LeadSignalDetectionService → LeadService                              │
│    NotificationPolicyService                                             │
│    AiReplyOrchestrationCoordinator (skip AI if duplicate)                │
│      AiReplyOrchestrationService                                         │
│        AiConfigurationService → KnowledgeRetrievalService                │
│        GreetingPolicyService + ConversationIntentService (demo only)     │
│        PromptBuilderService → AiGatewayService (OpenAI)                  │
│        PromptRunService + LangfuseTracingService (dev)                   │
│        AiReplyFallbackService                                            │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PostgreSQL (0001–0007) — multi-tenant via tenant_id + business_id       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Layer notes (actual behavior)

| Layer | Status | Location / notes |
|-------|--------|------------------|
| **Backend API** | **Implemented** | `POST /api/v1/webhook/message`, `GET /health` |
| **PromptBuilder** | **Implemented** | 8 sections; §2 branches on `intent_policy_enabled` |
| **Orchestration** | **Implemented** | `AiReplyOrchestrationService`, coordinator duplicate guard |
| **Intent routing** | **Partial** | `ConversationIntentService` + slices; **only** `alpstein_ai_demo_001` |
| **Greeting orchestration** | **Implemented** | `GreetingPolicyService` → §2 greeting block |
| **History safety** | **Spec-only** | Plan task done; **no** PromptBuilder instruction |
| **Attribution** | **Partial** | ATTR-2 Pydantic; not persisted; not in prompts |
| **Langfuse** | **Partial** | Tracing works; missing intent fields; stale demo tag |
| **n8n ingress** | **Implemented** | T13 test + T14 Telegram skeleton in repo |
| **Telegram flow** | **Partial** | Pipeline verified (exec 55–57, 89–91); T14.5–T14.6 open |
| **DB** | **Implemented** | 7 migrations, async SQLAlchemy, no repository layer |
| **Multi-tenant** | **Implemented** | `tenant_id` on client data; validator service |
| **Operator context** | **Implemented** | Webhook field → §3 append; not stored |
| **Channel abstraction** | **Implemented** | Enum `channel`; per-channel settings; adapters in n8n |

---

## 3. Implemented systems inventory

### Conversational behavior

| System | Status |
|--------|--------|
| Platform `prompt_templates` + task registry | **Implemented** |
| `PRE_SALES_CORE_CHARTER` + intent slices (Alpstein demo only) | **Implemented** (CIP-B) |
| Non-Alpstein §2 (core task + generic greeting only) | **Implemented** (P0 + P1) |
| `GreetingPolicyService` (first/follow-up/soft_return + language) | **Implemented** |
| `ConversationIntentService` (heuristics) | **Implemented** (CIP-A); scoped to one `business_id` |
| History safety / context freshness | **Implemented** (HF-1) |
| Lead signal keywords (urgent/handoff) | **Implemented**; **not** tied to intent |

### Orchestration

| System | Status |
|--------|--------|
| `WebhookMessageService` full path | **Implemented** |
| `AiReplyOrchestrationCoordinator` duplicate skip | **Implemented** |
| `AiReplyFallbackService` | **Implemented** |
| Intent + greeting in orchestration | **Implemented** |

### Persistence

| System | Status |
|--------|--------|
| Core entities + leads + AI tables + prompt_runs | **Implemented** |
| Message idempotency index | **Implemented** |
| Attribution persistence (ATTR-3) | **Planned** |
| Intent per message stored | **Out of scope** (MVP) |

### Observability

| System | Status |
|--------|--------|
| PromptRun rows (redacted, not in API) | **Implemented** |
| Langfuse span + generation | **Partial** (dev-only; incomplete metadata) |
| Production metrics/alerts | **Planned** |

### Workflows (n8n)

| System | Status |
|--------|--------|
| Test webhook workflow (T13) | **Implemented** (repo + Gate 1/2 evidence) |
| Telegram customer ingress (T14) | **Implemented** in repo; export inactive |
| WhatsApp | **Deferred** |
| n8n retries (T13.6) | **Deferred** |

### Prompt engineering

| System | Status |
|--------|--------|
| Eight-section Prompt Builder | **Implemented** |
| Operator business notes in §3 | **Implemented** |
| Contact ownership (no hardcoded PII in Python) | **Implemented** |
| Tenant profile content refactor (Alpstein demo) | **Implemented** (data task) |
| Monolithic pre-sales for non-demo businesses | **Implemented** (legacy path) |

### Attribution

| System | Status |
|--------|--------|
| `specs/architecture/channel-source-attribution.md` | **Implemented** (spec) |
| ATTR-2 webhook schemas | **Implemented** |
| ATTR-3–7 | **Planned** |

### Ops

| System | Status |
|--------|--------|
| n8n Docker + HTTPS proxy docs | **Implemented** |
| Env/credential checklist | **Implemented** |
| Database recovery runbook | **Implemented** |
| Post-T13.5 stabilization checklist | **Implemented** (operator-complete per docs) |

### Deprecated / abandoned

| Item | Status |
|------|--------|
| Stub `reply_to_customer` in webhook | **Deprecated** (removed T11.14) |
| Hardcoded Ivan contact in `PRE_SALES_*` | **Deprecated** (removed; see contact ownership) |
| `test_pre_sales_prompt_builder.py` | **Abandoned** (file absent; doc references updated) |
| Reusing `demo_barbershop_001` for Alpstein AI tests | **Deprecated** (separation done) |
| `n8n/workflows/My_workflow.json` | **Orphan** — not referenced in ops docs |

---

## 4. Prompt / orchestration audit

### Current prompt layering (§1–§8)

| § | Content | Authority |
|---|---------|-----------|
| 1 | `platform_system` from DB template | Platform |
| 2 | Task registry + (charter **or** legacy appendix) + intent slice + greeting | Platform |
| 3 | Tenant business profile + OPERATOR BUSINESS NOTES | Reference data |
| 4 | Tenant AI behavior | Reference data |
| 5 | Channel rules | Reference data |
| 6 | Knowledge snippets | Reference data |
| 7 | Conversation history | Reference data (but model may treat as facts — **risk**) |
| 8 | Current customer message | Reference data |

### Current §2 structure (runtime)

**When `business.external_id == alpstein_ai_demo_001`:**

```text
reply_to_customer (registry)
+ PRE_SALES_CORE_CHARTER
+ CONVERSATION INTENT (active turn): <one slice>
+ GREETING ORCHESTRATION (if policy resolved)
```

**Otherwise:**

```text
reply_to_customer + generic greeting only (no pre-sales charter or intent)
```

Evidence: `prompt_builder_service._build_task_instructions_body`, `conversation_intent_policy.py`.

### Intent routing state

| Aspect | State |
|--------|-------|
| Detection | **Implemented** — regex/heuristics, priority order, short-reply inheritance (priorities 1–4) |
| Prompt slices | **Implemented** — `intent_prompt_instructions.py` |
| Scope | **Partial** — single business external id |
| Specs canonical layer | **Missing** — `specs/architecture/prompt-builder-rules.md` has no intent §2 breakdown |

### Greeting state

**Implemented** and composed **after** intent slice. Orthogonal to intent (lifecycle vs turn intent). Documented in `greeting-orchestration-mvp.md`.

### Remaining contamination risks

| Risk | Severity | Notes |
|------|----------|-------|
| History repeats stale contacts/pricing/tone | **High** | No history safety block |
| `tenant_ai_profiles` (ask_for_name, language) vs operator context | **Medium** | DB profile still influences model |
| Legacy appendix for `demo_barbershop_001` | **Medium** | Full brochure-style rules every turn |
| Knowledge snippets marketing tone | **Medium** | Token ranking may inject noisy snippets |
| Duplicated contact rules | **Low** | Charter + intent slices + legacy appendix (Alpstein path reduced) |

### Unresolved prompt debt

1. **History Safety (HF)** — planned, not coded (`tasks/done/Plan Context Freshness History Safety Policy.md`).
2. **CIP-C** — Langfuse `conversation_intent`, `intent_matched_rule`.
3. **CIP-D** — live Telegram smoke with intent verification.
4. **Spec sync** — `prompt-builder-rules.md` §2 for intent + charter.
5. **Extend or retire legacy appendix** — product decision for non-Alpstein businesses.
6. **Operator contact in n8n** — ops dependency per `pre-sales-contact-ownership.md`.

---

## 5. Documentation consistency audit

### Duplicated docs

| Topic | Copies | Recommendation |
|-------|--------|----------------|
| n8n T13 plan | `docs/project-status/t13-n8n-workflow-plan.md` + `tasks/done/t13-n8n-workflow-slice.md` + `tasks/todo/t13-n8n-workflow-slice.md` | Archive **todo** copy; keep plan + done |
| T14 plan | `tasks/todo/t14-telegram-customer-ingress.md` + ops `telegram-customer-ingress.md` + `n8n-workflow-telegram-customer-ingress.md` | OK split (plan vs mapping vs workflow); sync status |
| Pre-sales behavior | `technical-pre-sales-behavior-mvp.md` + `conversation-intent-policy-mvp.md` + `pre-sales-contact-ownership.md` | Merge index under one “Conversational policy” hub |
| Attribution | `specs/.../channel-source-attribution.md` + `docs/project-status/channel-source-attribution-design.md` | Design index OK; mark ATTR-2 done |
| T11 design | `t11-prompt-builder-design.md` (draft) + `specs/.../prompt-builder-rules.md` | Mark draft superseded |
| Engineering history | `engineering-archive.md` + this audit + `completed.md` | Archive = chronology; audit = snapshot; completed = log |

### Conflicting / outdated docs

| Document | Issue |
|----------|-------|
| `docs/project-status/current-state.md` | Says **T13 missing**, **252 tests**, no greeting/intent/n8n complete — **severely stale** |
| `docs/project-status/next-steps.md` | § “Conversation Intent Policy — not implemented” **conflicts** with CIP-B done + completed.md |
| `docs/project-status/backlog.md` | All P0 checkboxes open — **obsolete** vs completed work |
| `docs/project-status/engineering-archive.md` | Pre–CIP-B snapshot; omits intent, contact cleanup |
| `conversation-intent-policy-mvp.md` intro table | Still says technical-pre-sales “to be refactored” — **partially fixed** in technical-pre-sales doc |
| `docs/architecture/langfuse-tracing.md` | Tags `alpstein_ai_demo_001` in text; code uses `demo_barbershop_001` for tag |
| `technical-pre-sales-behavior-mvp.md` | References removed `test_pre_sales_prompt_builder.py` — **fixed** to intent tests |
| `tasks/todo/t14-telegram-customer-ingress.md` | Says T14-OC-2 required before context — **done**; OC note stale |
| `tasks/todo/CIP-A-start.md`, `CIP-B.md` | Should be **done/** or deleted — work completed |

### Specs vs runtime mismatches

| Spec | Runtime |
|------|---------|
| `prompt-builder-rules.md` §2 | No document of intent charter/slices |
| `channel-source-attribution.md` ATTR-3+ | Not in services |
| `incoming-message-flow.md` | Mostly aligned; intent not named |
| Langfuse doc | Missing intent metadata (planned CIP-C) |

### Orphaned / low-trust artifacts

- `n8n/workflows/My_workflow.json`
- `n8n/workflows/backups/*.json` (backup only)
- `tasks/todo/t13-n8n-workflow-slice.md` (duplicate of done)
- `docs/project-status/t11-prompt-builder-design.md` (draft pointer)

---

## 6. Task system audit

### Completed (representative — see `tasks/done/` ~85 files)

- **T2–T10:** persistence, webhook, schemas  
- **T11.1–T11.16:** full AI stack  
- **T10-F1, T12.1–T12.7:** auth, leads, notify  
- **T13.0–T13.5:** n8n runtime + workflows + Gate 2  
- **T14.1–T14.4, T14-OC-1–3, greeting deploy, Alpstein switch**  
- **CIP-A/B, contact cleanup, intent spec, pre-sales plan, demo separation, ATTR-2**  
- **Plan:** History Safety (design only)

### Partially completed / open

| ID | State |
|----|-------|
| **T14.5** | **Planned** — Telegram regression |
| **T14.6** | **Planned** — scrubbed export |
| **CIP-C** | **Planned** — Langfuse intent metadata |
| **CIP-D** | **Planned** — live smoke |
| **ATTR-3–7** | **Planned** |
| **T13.6, T13.7** | **Deferred** |
| **T10-F3** | **Deferred** — idempotency race |
| **History Safety implementation** | **Planned** (HF — see §15) |

### Obsolete todo files (should archive or delete)

- `tasks/todo/t13-n8n-workflow-slice.md` (done)  
- `tasks/todo/CIP-A-start.md`, `tasks/todo/CIP-B.md` (done)  

### Tasks that should merge

- T14 plan + ops workflow doc — keep linked, single **status header** in todo file updated from gates  
- Attribution: `channel-source-attribution-design.md` → pointer only to spec + ATTR task table  

### Review conclusions captured in tasks (high signal)

- §2 overload → CIP spec + CIP-B  
- Operator context not overriding behavior → investigation + demo separation + profile refactor  
- Contact in Python prompts → contact ownership cleanup  
- History stale vs current context → History Safety **plan only**

---

## 7. Runtime vs spec audit

| Area | Spec / doc | Runtime | Match? |
|------|------------|---------|--------|
| Webhook normalized shape | `webhooks.md` | `webhook.py` + attribution schemas | **Yes** |
| `operator_business_context` | `webhooks.md` §7 | Wired to Prompt Builder | **Yes** |
| Intent in §2 | `conversation-intent-policy-mvp.md` | CIP-B for `alpstein_ai_demo_001` only | **Partial** (not in `specs/`) |
| Greeting | `greeting-orchestration-mvp.md` | Implemented | **Yes** |
| n8n no OpenAI | `n8n-architecture.md` | No OpenAI nodes in exports | **Yes** |
| n8n no DB writes | MVP scope | No PG nodes | **Yes** |
| Attribution persistence | channel-source-attribution §10 | Not saved | **No** |
| History safety | Plan task | Not in PromptBuilder | **No** |
| Langfuse tags | `langfuse-tracing.md` | `DEMO_BUSINESS_EXTERNAL_ID = demo_barbershop_001` | **No** for Alpstein demo |
| `current-state.md` n8n | Says missing | T13/T14 done | **No** |
| Test count “252” | current-state | More tests exist (40+ files) | **Stale** |

### Tests vs runtime

- `test_conversation_intent_service.py`, `test_conversation_intent_prompt_builder.py` — align with CIP-B  
- `test_webhook_attribution_schemas.py` — ATTR-2 only  
- No `test_history_safety_*` — consistent with not implemented  
- Legacy pre-sales prompt tests **removed** — good; spec §10 still mentions replacement (done)

---

## 8. Technical debt audit

| Category | Debt | Priority |
|----------|------|----------|
| **Orchestration** | Intent only on one business; lead signals ignore intent | P1 |
| **Prompt** | Legacy appendix on non-demo businesses; no history safety | P0–P1 |
| **History contamination** | Polluted `messages` rows drive loops | P0 |
| **Workflow** | T14.5–T14.6 open; T13.6 retries; export inactive | P1 |
| **Documentation** | current-state, backlog, next-steps, engineering-archive stale | P1 |
| **Tenant isolation** | Generally sound; risk is **wrong business_id** in n8n workflow | P0 ops |
| **Rollout** | Docker bridge IP, manual env, workflow import | P1 |
| **Observability** | Langfuse dev-only; wrong demo tag; no intent fields | P2 |
| **Attribution** | Validated but discarded at persistence | P2 |
| **Concurrency** | T10-F3 duplicate race | P3 |

---

## 9. Multi-tenant audit

| Control | Status |
|---------|--------|
| `tenant_id` on client-owned rows | **Implemented** |
| `validate_tenant_context` on writes | **Implemented** |
| Business resolution via `business_id` string | **Implemented** |
| `operator_business_context` | Scoped by resolved business; **not stored**; n8n workflow binds one business per deployment |
| Contact ownership | **Implemented** policy — values in operator context, not hardcoded in code |
| Demo separation `alpstein_ai_demo_001` vs `demo_barbershop_001` | **Implemented** (data + n8n switch) |
| Cross-channel identity | **Out of MVP** — conversation key = customer + channel |

**Risks:** misconfigured n8n `business_id`; operator context on wrong workflow; shared conversation history across context changes without rotation.

---

## 10. Conversation architecture maturity

| Capability | Maturity | Notes |
|------------|----------|-------|
| Greeting orchestration | **Production-ready (MVP)** | Backend-only; tested |
| Intent routing | **Prototype on one business** | Heuristics; needs CIP-C/D + spec sync |
| Technical pre-sales | **Split** | Strong for Alpstein demo; legacy elsewhere |
| Pricing behavior | **Implemented** via intent slice (demo only) | |
| Unsupported-system handling | **Implemented** (demo) | Bitrix → `unsupported_system` in service |
| Off-topic handling | **Implemented** (demo) | Conservative patterns |
| History safety | **Not started** | Highest gap for “context change” scenarios |
| Lead qualification | **Basic** | Keywords + create/update; not intent-aware |

---

## 11. Observability audit

### Langfuse (partial)

**Useful today:** assembled prompt in metadata, greeting_mode, operator context preview, OpenAI generation I/O, session = conversation_id.

**Missing (planned CIP-C):** `conversation_intent`, `intent_matched_rule`, `intent_used_previous_message`.

**Incorrect:** tag `alpstein_ai_demo_001` documented but code tags `demo_barbershop_001` (`langfuse_tracing_service.DEMO_BUSINESS_EXTERNAL_ID`).

### Missing telemetry (production)

- Webhook error rates, AI failure rate, fallback rate  
- Lead/notify funnel metrics  
- n8n execution failure alerts  
- PromptRun analytics UI  

### Operational debugging quality

**Good:** PromptRun table, Langfuse prompt dump, n8n execution IDs in task docs.  
**Weak:** no single “system status” doc; stale current-state misleads onboarding.

---

## 12. Documentation restructuring proposal

### Proposed top-level structure

```text
docs/
  README.md                    ← entry: what to read first
  architecture/
    README.md                  ← index of behavioral specs
    system/                    ← move decisions, multi-tenant, channel creds
    conversational/            ← greeting, intent, pre-sales, contact ownership, history safety (when spec'd)
    ai/                        ← langfuse, prompt-builder (pointer to specs/)
  ops/
    README.md                  ← runbooks index
  project-status/
    current-state.md           ← MUST be regenerated from audit quarterly
    completed.md
    next-steps.md              ← single queue, no contradictions
    engineering-archive.md
    engineering-audit-report.md  ← this file
specs/                         ← canonical contracts (unchanged role)
tasks/
  todo/                        ← only open work
  done/                        ← archive
```

### Canonical sources of truth

| Topic | Canonical |
|-------|-----------|
| API/webhook contract | `specs/api/webhooks.md` |
| Prompt section order | `specs/architecture/prompt-builder-rules.md` (+ **add** intent §2 amendment) |
| Intent behavior | `docs/architecture/conversation-intent-policy-mvp.md` until merged into specs |
| Greeting | `docs/architecture/greeting-orchestration-mvp.md` |
| n8n Telegram | `docs/ops/n8n-workflow-telegram-customer-ingress.md` |
| What shipped | `docs/project-status/completed.md` |
| What’s next | `docs/project-status/next-steps.md` |

### Archive candidates

- `tasks/todo/t13-n8n-workflow-slice.md`  
- `tasks/todo/CIP-*.md` (move to done)  
- `docs/project-status/t11-prompt-builder-design.md` (banner: superseded)  
- `docs/project-status/backlog.md` (replace with next-steps or delete)

---

## 13. Recommended next engineering priorities

### Critical

1. **HF-1 — History Safety in PromptBuilder** (implement plan from `tasks/done/Plan Context Freshness…`) — blocks trustworthy context updates.  
2. **Fix documentation gatekeepers** — regenerate `current-state.md`; fix `next-steps.md` CIP contradiction.  
3. **T14.5** — Telegram owner-notify + duplicate regression (ops truth for production demo).

### Important

4. **CIP-C** — Langfuse intent metadata + fix demo business tag constant.  
5. **CIP-D** — Telegram live smoke with intent + smaller §2 verification.  
6. **T14.6** — scrubbed n8n export + repo as source of truth.  
7. **Spec amendment** — `prompt-builder-rules.md` for §2 intent composition.  
8. **Ops** — operator contact block in n8n per `pre-sales-contact-ownership.md`.

### Later

9. **ATTR-3** — attribution persistence.  
10. **Extend intent policy** to other businesses or remove legacy appendix.  
11. **T13.6** — n8n retries.  
12. **WhatsApp** ingress.  
13. **T10-F3** — idempotency race.

### Dangerous distractions (defer)

- Vector DB / embeddings  
- LangGraph / multi-agent  
- CRM admin panel (not in MVP specs)  
- n8n business logic or OpenAI nodes  
- Dashboard / billing  

---

## 14. Anti-patterns to avoid

Based on project history (`engineering-archive.md`, investigation tasks):

1. **Giant always-on §2 appendices** — caused brochure tone; replaced by CIP for one business — do not reintroduce stacking.  
2. **Prompt duplication** — same CRM/contact rules in DB profile, operator context, and platform appendix.  
3. **Architecture thrashing** — moving AI or prompts to n8n (rejected; keep rejecting).  
4. **Premature vector DB / agents** — explicit MVP exclusions.  
5. **Uncontrolled workflow logic** — leads, intent, pricing rules in n8n Code nodes.  
6. **Documentation fragmentation** — multiple “current state” truths; fix with one regeneratable `current-state.md`.  
7. **Assuming operator context overrides history** — it does not without History Safety.  
8. **Hardcoding PII in Python prompts** — corrected; keep in operator/workflow layer.

---

## 15. Current roadmap recommendation (ordered)

| Order | Item | Rationale |
|-------|------|-----------|
| 1 | **HF-1** (History Safety implementation) | Highest behavioral correctness after CIP-B + operator edits |
| 2 | **Docs consolidation pass** | Fix current-state, next-steps, archive; archive obsolete todos |
| 3 | **CIP-C** | Debug intent in Langfuse; fix `demo_barbershop` tag drift |
| 4 | **T14.5** | Close Telegram regression gate |
| 5 | **CIP-D** | End-to-end intent smoke on Telegram |
| 6 | **T14.6** | Export hygiene |
| 7 | **Spec sync** (`prompt-builder-rules` + webhooks if needed) | Prevent spec/runtime drift |
| 8 | **ATTR-3** | When analytics/CRM export needed |
| 9 | **Live stabilization** | Production compose, monitoring, T13.6 — after gates above |
| 10 | **Multi-channel** (WhatsApp) | After Telegram stable |
| 11 | **CRM panel** | **Not in current MVP specs** — spec gap / product decision before engineering |

**Note on HF-1 vs CIP-C:** HF-1 unblocks context-change correctness; CIP-C is parallelizable but lower user impact than history safety.

---

## 16. Appendix

### Major architecture pivots (chronological)

1. Spec-driven MVP (2026-05-24).  
2. Backend-owned AI orchestration.  
3. T11 full AI stack + PromptRun.  
4. T12 leads/notifications in backend.  
5. T13 n8n transport + owner Telegram.  
6. T14 Telegram customer ingress + dual-bot credentials.  
7. T14-OC operator context via webhook.  
8. Demo business separation (`alpstein_ai_demo_001`).  
9. Greeting orchestration MVP.  
10. Conversation Intent Policy CIP-A/B (scoped demo).  
11. Contact ownership cleanup (no PII in Python prompts).

### Major discoveries

- `raw_payload` does not feed Prompt Builder for business context.  
- Operator context can be present in assembly yet **history + tenant_ai_profiles** dominate behavior.  
- Marketing-style `tenant_business_profiles` increased hallucination pressure (Langfuse evidence).  
- §2 size correlates with brochure tone and rule conflict.

### Unresolved decisions

1. Roll out intent policy beyond `alpstein_ai_demo_001` or deprecate legacy appendix globally?  
2. Implement History Safety A+C only, or also context versioning (D)?  
3. Align `LeadSignalDetectionService` with `implementation_interest` intent?  
4. When to start ATTR-3 vs CRM export needs?  
5. Production Langfuse: enable in prod or stay dev-only?

### Glossary

| Term | Meaning |
|------|---------|
| **§2** | `task_instructions` Prompt Builder section |
| **CIP** | Conversation Intent Policy (A=detect, B=prompt, C=Langfuse, D=smoke) |
| **HF / History Safety** | Context Freshness policy — history non-authoritative for business facts |
| **OC** | Operator `operator_business_context` overlay |
| **ATTR** | Channel source attribution slice series |
| **Gate 1/2** | n8n test webhook + owner Telegram verification |

---

*End of audit. Regenerate or amend when T14.5, CIP-C, or HF-1 land.*
