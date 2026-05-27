**Doc status:** canonical governance  
**Tier:** architecture/behavior (governance layer — not runtime code)  
**As-of:** 2026-05-27  
**Runtime map:** [`canonical-runtime-architecture.md`](canonical-runtime-architecture.md)

# Canonical Conversational Policy Hierarchy

## 1. Purpose

This document formalizes the **authoritative conversational policy hierarchy** for Alpstein AI after:

- **HF-1** — History Safety preamble in §7
- **P0** — Business-aware §2 gating (`alpstein_product_behavior_enabled_for_business`)
- **P1** — Legacy `PRE_SALES_TASK_APPENDIX` removal
- **Canonical runtime stabilization** — eight-section PromptBuilder model as live path

### Why this hierarchy exists

Multi-layer prompts fail when:

- rules live in the wrong section (tenant data treated as system authority);
- stale dialogue overrides current business facts;
- product persona leaks across unrelated tenants;
- monolithic appendices compete with turn-specific behavior.

Governance defines **who may say what**, **what wins on conflict**, and **where new behavior must be added** — so conversational changes stay deterministic and auditable.

### Relationship to PromptBuilder and orchestration

| Layer | Role |
|-------|------|
| **Orchestration** (`AiReplyOrchestrationService`) | Resolves greeting mode, intent (when gated), loads config/history/knowledge; passes flags and DTOs to PromptBuilder |
| **PromptBuilder** (`PromptBuilderService`) | Assembles §1–§8 in fixed order; applies HF-1 labels; does not route intents or detect language |
| **This document** | Specifies precedence, ownership, and evolution rules |

**Clarification:** This is **not** a runtime redesign. It is a **governance/specification layer** that describes live behavior and constrains future changes. When this doc and code disagree, **code is runtime truth** until a governed change lands.

---

## 2. Authoritative conversational layers

Layers are listed **highest authority first**. All platform layers (§1–§2, HF-1 preamble) dominate reference-data layers (§3–§8).

### Layer summary table

| Layer | Prompt section | Authority | Runtime owner |
|-------|----------------|-----------|---------------|
| Platform system | §1 `platform_system` | **Platform — highest** | `AiConfigurationService` → `prompt_templates.system_prompt` |
| Core task registry | §2 (base) | **Platform — system** | `PromptBuilderService.PLATFORM_TASK_REGISTRY` |
| Pre-sales core charter | §2 (Alpstein only) | **Platform — system** | `pre_sales_prompt_instructions.PRE_SALES_CORE_CHARTER` |
| Intent behavior slice | §2 (Alpstein only, one per turn) | **Platform — system** | `ConversationIntentService` + `intent_prompt_instructions` |
| Greeting orchestration | §2 (when policy resolved) | **Platform — system** | `GreetingPolicyService` + `greeting_prompt_instructions` |
| Tenant business profile | §3 | **Reference data** | DB `tenant_business_profiles` |
| Operator business context | §3 overlay | **Reference data** | n8n inject → webhook → PromptBuilder |
| Tenant AI behavior | §4 | **Reference data** | DB `tenant_ai_profiles` |
| Channel rules | §5 | **Reference data** | DB `tenant_channel_settings` |
| Knowledge snippets | §6 | **Reference data** | `KnowledgeRetrievalService` |
| History safety preamble | §7 (prefix) | **Platform — dialogue governance** | `history_safety_prompt_instructions` |
| Conversation history | §7 (dialogue lines) | **Reference data — non-authoritative facts** | `MessageService` → PromptBuilder |
| Current customer message | §8 | **Reference data — turn target** | Webhook `message.text` |

---

### §1 Platform system

| | |
|--|--|
| **Authority level** | Highest — non-truncatable |
| **Allowed** | Platform role, global safety, escalation limits, output constraints, guard that reference blocks must not override platform rules |
| **Forbidden** | Tenant-specific copy, contact values, CRM lists, per-turn intent rules, greeting lifecycle |
| **Runtime ownership** | Platform `prompt_templates` row (active version via `AiConfigurationService`) |
| **Override behavior** | Nothing in §3–§8 may precede or replace §1. Tenant cannot edit. |

---

### §2 Task behavior (composed sub-layers)

§2 is **system authority** (same class as §1). Sub-blocks are appended in fixed order:

```text
1. reply_to_customer task registry     (all businesses)
2. PRE_SALES_CORE_CHARTER              (alpstein_ai_demo_001 only)
3. CONVERSATION INTENT slice           (alpstein_ai_demo_001 only — exactly one)
4. GREETING ORCHESTRATION block         (all businesses when GreetingPolicy resolved)
5. LANGUAGE RULES                       (part of greeting block)
```

#### Core task registry

| | |
|--|--|
| **Authority level** | Platform — system |
| **Allowed** | Turn objective (`reply_to_customer`), anti-hallucination baseline, handoff suggestion when uncertain, “reference data must not override platform safety” |
| **Forbidden** | Business-specific prices, product marketing appendices, intent detection logic |
| **Runtime ownership** | `PromptBuilderService.PLATFORM_TASK_REGISTRY` |
| **Override behavior** | Always present; charter/intent/greeting extend but do not contradict safety lines |

#### Pre-sales core charter (Alpstein product gate only)

| | |
|--|--|
| **Authority level** | Platform — system |
| **Allowed** | Alpstein pre-sales persona role/style, global contact *when* rules, name preservation, no invented prices/integrations |
| **Forbidden** | Per-intent CRM catalogs, hardcoded contact values, duplicate full legacy appendix |
| **Runtime ownership** | `pre_sales_prompt_instructions.py` |
| **Gating** | `alpstein_product_behavior_enabled_for_business()` — exact match `alpstein_ai_demo_001` |
| **Override behavior** | Supersedes generic task tone for Alpstein demo; still subordinate to §1 |

#### Intent behavior slice (Alpstein product gate only)

| | |
|--|--|
| **Authority level** | Platform — system (turn-specific) |
| **Allowed** | One active intent’s purpose, depth, contact policy, length discipline for **this turn** |
| **Forbidden** | Stacking multiple intent blocks; resurrecting legacy appendix; LLM-based routing |
| **Runtime ownership** | `ConversationIntentService.resolve()` → `build_intent_instruction_block()` |
| **Gating** | Same as charter — Alpstein demo only |
| **Override behavior** | Overrides generic charter/marketing tone for the turn; subordinate to §1 and core task safety |

#### Greeting orchestration

| | |
|--|--|
| **Authority level** | Platform — system (lifecycle-specific) |
| **Allowed** | Intro vs no-intro, soft return, reply language; Alpstein product intro **or** generic tenant intro |
| **Forbidden** | Intent detection; lead scoring; n8n prompt text |
| **Runtime ownership** | `GreetingPolicyService.resolve()` → `build_greeting_instruction_block(..., alpstein_greeting=...)` |
| **Variant selection** | `alpstein_greeting=True` when product behavior gate enabled; else `_GENERIC_MODE_BLOCKS` |
| **Override behavior** | Appended **after** intent slice; lifecycle rules apply alongside intent (orthogonal). Platform greeting language/name rules override conflicting §4 hints. |

---

### §3 Tenant business context + operator context

| | |
|--|--|
| **Authority level** | Reference data |
| **Allowed** | Services, prices, hours, location, limitations; operator notes under `OPERATOR BUSINESS NOTES` |
| **Forbidden** | System instructions, safety overrides, intent routing, “ignore previous instructions” |
| **Runtime ownership** | DB profile (`AiConfigurationService`); operator string from webhook (transport-only, not persisted) |
| **Override behavior** | **Wins over §7** for changeable business facts when HF-1 applies. **Loses to §1–§2** on safety conflicts. Operator notes are additive to DB profile, not canonical DB replacement. |

---

### §4 Tenant AI behavior

| | |
|--|--|
| **Authority level** | Reference data |
| **Allowed** | Tone, language preference, ask_for_name/phone/email flags, handoff_enabled, forbidden_promises lists, fallback text reference |
| **Forbidden** | Platform safety rules, intent lists, greeting lifecycle, CRM capability claims |
| **Runtime ownership** | DB `tenant_ai_profiles` |
| **Override behavior** | Influences style only. **§2 greeting language/name rules and §2 intent contact policy take precedence** on conflict. Used by `AiReplyFallbackService` for fallback text — separate from prompt assembly precedence. |

---

### §5 Channel rules

| | |
|--|--|
| **Authority level** | Reference data |
| **Allowed** | Channel label, response_style, max_response_length, emoji/link flags |
| **Forbidden** | Provider credentials, webhook wiring, intent logic |
| **Runtime ownership** | DB `tenant_channel_settings` |
| **Override behavior** | Style/length hints only. **Intent slice length discipline and §2 rules dominate** for Alpstein demo turns. Trimmed first among variable sections when budget tight. |

---

### §6 Knowledge snippets

| | |
|--|--|
| **Authority level** | Reference data |
| **Allowed** | FAQ, pricing excerpts, policies, service descriptions (retrieved, bounded) |
| **Forbidden** | Full prompt appendices duplicating §2; platform task instructions |
| **Runtime ownership** | `KnowledgeRetrievalService` (MVP: token rank, max 5 snippets / 4k chars) |
| **Override behavior** | Grounds factual answers. **§1–§2 safety wins** if snippet implies unsafe promises. **§3 profile + operator notes win** on factual conflict with stale §7. |

---

### §7 History (HF-1 governed)

| | |
|--|--|
| **Authority level** | Reference data for dialogue; **HF-1 preamble is platform dialogue governance** |
| **Allowed** | Prior customer/ai/owner lines; continuity and tone; HF-1 non-authoritative labeling |
| **Forbidden** | Authoritative contacts, prices, policies, integration guarantees sourced only from old `ai` lines |
| **Runtime ownership** | `MessageService.load_recent_conversation_history` (10–20 msgs); HF-1 in `PromptBuilderService._build_conversation_history` |
| **HF-1 (implemented)** | When dialogue exists: prepend `HISTORY_SAFETY_PREAMBLE`; label prior AI as `ai (dialogue only, not business facts)` |
| **Override behavior** | **History is non-authoritative for changeable facts after HF-1.** §3, §6, operator notes, and §2 task instructions override stale assistant content. Customer lines in history remain dialogue context only. Preamble trimmed separately from dialogue lines under budget pressure. |
| **Empty history** | §7 omitted or `(not provided)` — no preamble injected |

---

### §8 Current customer message

| | |
|--|--|
| **Authority level** | Reference data — explicit turn target |
| **Allowed** | Customer text to answer now (capped 8k chars) |
| **Forbidden** | Interpreted as system instructions |
| **Runtime ownership** | Webhook normalized payload |
| **Override behavior** | Always last section. Does not override §1–§2 safety. Intent detection reads this text in orchestration, not in PromptBuilder. |

---

### Out-of-prompt conversational signals (not layers)

These affect **backend flags**, not §2 assembly:

| Signal | Owner | Affects reply text? |
|--------|-------|-------------------|
| Lead create/update | `LeadService` / webhook pipeline | No |
| `LeadSignalDetectionService` (urgent/handoff keywords) | Keyword heuristics on customer text | No — affects `notify_owner` |
| `AiReplyFallbackService` | Gateway failure path | Fallback message only, not assembled prompt |

---

## 3. Rule precedence

### Global precedence (mandatory)

```text
§1 platform_system
  ↓ wins over
§2 task_instructions (registry → charter → intent → greeting)
  ↓ wins over
§3 tenant_business + operator notes
§4 tenant_behavior
§5 channel_rules
§6 knowledge
§7 history (HF-1 governed — facts non-authoritative)
§8 current_customer_message
```

**Never allowed:** §3–§8 content promoted to §1–§2; tenant/profile/knowledge overriding platform safety; multiple intent slices in one turn; legacy appendix resurrection.

### Conflict resolution examples

| Conflict | Resolution |
|----------|--------------|
| **Operator context vs history** | Current operator notes (§3) + HF-1 preamble → history `ai` lines must not supply conflicting contacts/prices |
| **Tenant profile vs greeting policy** | §2 greeting language rules and “do not ask for name unless…” override §4 `ask_for_name=yes` |
| **Current message vs stale history** | §8 is the turn target; §7 provides continuity only; facts from old `ai` replies discarded if they conflict with §3/§6 |
| **Intent slice vs generic charter** | Intent slice narrows turn behavior; charter provides global safety/style floor |
| **Channel max length vs intent length hint** | §2 intent/greeting discipline primary; §5 `max_response_length` is advisory reference data |
| **Knowledge vs tenant profile** | Both reference data — prefer §3 canonical profile for structured business fields; knowledge for FAQ-style excerpts |
| **§2 vs §1** | §1 wins on safety/role boundaries |

### History non-authority (HF-1 — runtime truth)

After HF-1, the model is explicitly instructed in §7 that:

- prior assistant messages are **not** authoritative business facts;
- current tenant context, operator notes, knowledge, and **task instructions** override history;
- changeable facts (contacts, prices, hours, policies, CRM claims) must come from current sections only.

HF-1 reduces but **does not eliminate** model error — there is no context versioning or history purge on operator update.

---

## 4. Current runtime conversational governance

**As-of 2026-05-27** — verified against `PromptBuilderService`, orchestration, and tests.

### Business-aware §2 gating

Single gate: `alpstein_product_behavior_enabled_for_business(business_external_id)` in `conversation_intent_policy.py`.

| `external_id` | §2 composition |
|---------------|----------------|
| `alpstein_ai_demo_001` | Core task + `PRE_SALES_CORE_CHARTER` + **one** intent slice + Alpstein greeting variant |
| **All others** | Core task + **generic** greeting variant only |

`PRE_SALES_TASK_APPENDIX` **removed from codebase (P1)** — not assembled at runtime.

### Greeting lifecycle ownership

- **Detection:** `GreetingPolicyService` — `first_contact` / `follow_up` / `soft_return` from prior `ai` messages + 24h inactivity
- **Language:** customer message heuristics → Telegram `language_code` → English
- **Prompt text:** §2 greeting block; Alpstein vs generic selected by `alpstein_greeting` flag
- **Scope:** All businesses

### Intent ownership

- **Detection:** `ConversationIntentService` — regex priority + short-reply inheritance (priorities 1–4)
- **Scope:** Alpstein demo only (same gate as product behavior)
- **Assembly:** Exactly one slice in §2; orchestration passes `ConversationIntentResolution` to PromptBuilder

### Task registry ownership

- Platform constant `PLATFORM_TASK_REGISTRY["reply_to_customer"]` — all businesses, always first in §2

### Tenant data ownership

- §3–§5 loaded by `AiConfigurationService` from PostgreSQL — tenant-scoped
- Not edited per request; operator overlay is request-scoped only

### operator_business_context ownership

- **Injected by:** n8n Set node (transport)
- **Consumed by:** PromptBuilder §3 append — not persisted, not in webhook response
- **Values:** Contact names/phones/emails belong here per [`pre-sales-contact-ownership.md`](pre-sales-contact-ownership.md)

### Trim / budget governance

- §1, §2, §8 fixed (not subject to variable trim)
- §3–§7 trim order: channel → behavior → business → knowledge → history (dialogue lines before HF-1 preamble when trimming history)

---

## 5. Remaining overlaps and drift risks

**Identification only — no redesign in this section.**

| Risk | Description | Severity |
|------|-------------|----------|
| **Duplicated contact rules** | Contact/name preservation appears in core task, `PRE_SALES_CORE_CHARTER`, and multiple intent slices | Low–Medium |
| **Duplicated greeting constraints** | “Do not repeat intro” in greeting blocks; “start short” in charter/intent footer | Low |
| **Tone overlap** | Charter global style + intent slice style + §4 `tone`/`response_style` | Medium |
| **Pricing behavior duplication** | Core task “do not invent prices”; charter safety; `pricing_interest` slice — intentional redundancy | Low |
| **Unsupported-system overlap** | Charter “no certified integrations” + `unsupported_system` slice — intentional | Low |
| **Channel vs intent length** | §5 `max_response_length` vs intent “Telegram-friendly” footer — no single enforced cap | Medium |
| **Hardcoded Alpstein gate** | Product behavior tied to one `external_id` string — scaling risk | Medium |
| **§4 vs §2 name ask** | `ask_for_name=true` (barbershop seed) vs greeting “do not ask for name unless…” | Medium |
| **Historical doc drift** | Older docs (`engineering-audit-report.md`, intent policy “before/after” tables) may still describe legacy appendix path | Low (governance) |
| **Spec gap** | `prompt-builder-rules.md` lacks intent/charter/HF-1 §2/§7 amendments | Medium |
| **Langfuse intent metadata** | CIP-C constants exist; not wired to traces | Medium (observability) |
| **Knowledge pollution** | DB/knowledge can contain marketing CRM lists that compete with §2 intent discipline | Medium |
| **HF-1 residual** | Model may still echo stale `ai` lines despite preamble — no versioned context invalidation | Medium |
| **Lead vs intent qualification** | `implementation_interest` asks for contact; lead keywords fire independently — no unified qualification state | Low (MVP) |

---

## 6. Canonical responsibilities

| Subsystem | Owns | Must not own |
|-----------|------|--------------|
| **PromptBuilderService** | §1–§8 assembly order, HF-1 labels, trim budget, operator §3 overlay formatting | Intent detection, greeting mode detection, provider calls, DB writes |
| **GreetingPolicyService** | Lifecycle mode, reply language resolution | Intent routing, prompt string assembly, n8n logic |
| **ConversationIntentService** | Turn intent classification (Alpstein gate) | Prompt assembly, greeting mode, lead creation |
| **conversation_intent_policy** | Business scope gate for product behavior | Intent heuristics content |
| **AiConfigurationService** | Load templates, tenant profiles, channel rules | Full prompt merge, provider calls |
| **KnowledgeRetrievalService** | Rank/bound snippets for §6 | Prompt rules, intent |
| **MessageService** | Persist messages; load 10–20 history rows | Prompt assembly |
| **AiReplyOrchestrationService** | Chain config → knowledge → history → policies → build → gateway | Prompt text constants; n8n payloads |
| **tenant_business_profiles** | Business facts (§3) | Platform safety, intent, greeting rules |
| **tenant_ai_profiles** | Style/handoff/fallback hints (§4) | §2 task instructions |
| **operator_business_context** | Runtime contact/campaign values (§3 overlay) | Task instructions; persistence |
| **tenant_channel_settings** | Channel style hints (§5) | Provider API config |
| **LangfuseTracingService** | Observe spans, metadata, generations | Change routing or prompt content |
| **n8n** | Ingress, normalize, operator inject, send reply, owner notify | AI behavior, intent, greeting, prompt logic, PostgreSQL writes |

---

## 7. Anti-patterns

Explicitly forbidden in conversational governance:

| Anti-pattern | Why forbidden |
|--------------|---------------|
| **Giant prompts / mega-prompt** | Brochure tone, rule conflict, budget steals tenant/history context |
| **Appendix resurrection** | `PRE_SALES_TASK_APPENDIX` removed P1 — must not return stacked on intent |
| **Duplicated behavioral rules** | Same contact policy in charter + every slice + knowledge |
| **Hidden fallback prompts** | Fallback via `AiReplyFallbackService` only — not secret §2 blocks |
| **Runtime behavior in n8n** | Violates backend ownership boundary |
| **Stacked intent slices** | One intent per turn — CIP invariant |
| **Prompt logic in tenant knowledge** | Knowledge is §6 reference data only |
| **Speculative memory systems** | No vector long-term memory, context versioning, or agent swarms in MVP |
| **LLM intent classifier** | Heuristics first; metrics before complexity |
| **Tenant-editable §1** | Platform safety boundary |
| **Promoting operator/tenant text to §2** | Breaks precedence model |

---

## 8. Stability rules

### How conversational rules may evolve

1. **Spec or governance doc update first** (this file + relevant `docs/architecture/*-mvp.md`).
2. **Smallest runtime change** in the owning subsystem (see §6).
3. **Tests** for assembly fragments, gating, HF-1, and negative contamination assertions.
4. **Human review** before merge; no drive-by prompt rewrites.

### Where new behavior belongs

| Need | Belongs in |
|------|------------|
| New turn type (pricing, social, …) | New intent slice + `ConversationIntentService` rule — Alpstein gate until product expands |
| Intro / language / lifecycle | Greeting orchestration §2 block — generic vs Alpstein variant |
| Global safety change | §1 template and/or core task registry |
| Alpstein persona floor | `PRE_SALES_CORE_CHARTER` only — keep ≤ ~1.2k chars |
| Business facts | §3 DB profile or operator notes |
| Style preference | §4 tenant profile |
| FAQ / policy text | §6 knowledge — not §2 |
| Stale dialogue handling | §7 HF-1 preamble — not new memory system |
| Owner alert on keyword | `LeadSignalDetectionService` — not §2 |

### How to avoid drift

- Treat [`canonical-runtime-architecture.md`](canonical-runtime-architecture.md) as runtime map; this file as precedence map.
- Any §2 change: verify **both** Alpstein and non-Alpstein paths (`test_product_behavior_gating.py`).
- Any history change: run `test_history_safety_prompt_builder.py`.
- Do not update behavior docs without checking code gates in `conversation_intent_policy.py`.

### How to audit new prompt logic

Checklist for reviewers:

- [ ] Which § layer? Is it platform (§1–§2, HF-1) or reference (§3–§8)?
- [ ] Gated correctly (`alpstein_product_behavior_enabled`)?
- [ ] Exactly one intent slice if intent path?
- [ ] No legacy appendix strings?
- [ ] No hardcoded contact values in Python constants?
- [ ] Contamination tests for non-Alpstein businesses?
- [ ] HF-1 preamble still precedes dialogue when history non-empty?

### How to review conversational changes

Use **alpstein-conversation-designer** for behavior specs; **alpstein-ai-integration-engineer** for PromptBuilder/intent/greeting code; **alpstein-reviewer** for boundary violations. n8n changes limited to operator **values**, not rules.

---

## 9. Open governance debt

| Item | Status | Impact |
|------|--------|--------|
| **Hardcoded `alpstein_ai_demo_001` gate** | Open product decision | New tenants lack intent/pricing/off-topic slices until gate model expands |
| **CIP-C observability** | Constants only; metadata not in Langfuse spans | Cannot audit live intent routing at scale |
| **CIP-D live smoke** | Planned | Behavioral verification still manual |
| **HF-1 residual contamination** | Mitigated, not eliminated | Operator/profile updates without new conversation may still see model echo old `ai` lines |
| **DB/knowledge pollution** | Content ops | Marketing CRM lists in knowledge undermine intent discipline |
| **Multi-business policy expansion** | Undecided | Roll intent to all tenants vs template-key-based profiles |
| **Onboarding policy for future tenants** | Undecided | No governed default for §2 beyond generic task + greeting |
| **`prompt-builder-rules.md` sync** | Spec gap | Canonical spec silent on intent, charter, HF-1, business gating |
| **Langfuse tag drift** | `demo_barbershop_001` tagged as Alpstein in traces | Misleading governance audits |
| **Lead vs intent qualification alignment** | Independent in MVP | Possible divergent contact-ask vs notify behavior |
| **Historical audit docs** | Stale sections | `engineering-audit-report.md` pre-P0/P1/HF-1 claims |

---

## 10. Conclusion

### Current architectural direction

Alpstein AI conversational control is **backend-centered**, **configuration-layered**, and **PromptBuilder-assembled**:

- Platform authority in §1–§2 (plus HF-1 dialogue governance in §7)
- Tenant/operator facts in §3–§6 as reference data
- Turn-specific behavior via **one intent slice** (Alpstein demo) and **greeting lifecycle** (all businesses)
- History explicitly **non-authoritative** for changeable facts after HF-1

### What is now canonical

- Eight-section assembly order (§1–§8)
- Business-aware §2 gating (P0)
- Legacy appendix **removed** (P1)
- HF-1 history safety preamble + non-authoritative `ai` labels
- Orthogonal greeting vs intent policies
- Operator contact **values** in §3 overlay; contact **behavior** in §2 platform text
- n8n free of AI behavioral logic

### What is deprecated

- `PRE_SALES_TASK_APPENDIX` monolithic path
- Global Alpstein pre-sales + product greeting on all businesses (pre-P0)
- Treating §7 `ai:` lines as authoritative business facts (pre-HF-1)
- Inferring behavior from specs alone without runtime verification

### What must not return

- Full legacy appendix on every turn
- Stacked intent slices or n8n intent routing
- Hardcoded personal contacts in Python prompt constants
- Giant unified mega-prompts replacing layered governance
- Autonomous multi-agent / long-term memory frameworks for MVP conversational control

---

## Related documents

| Document | Role |
|----------|------|
| [`canonical-runtime-architecture.md`](canonical-runtime-architecture.md) | Runtime map (what runs) |
| [`conversation-intent-policy-mvp.md`](conversation-intent-policy-mvp.md) | Intent design contract |
| [`greeting-orchestration-mvp.md`](greeting-orchestration-mvp.md) | Greeting lifecycle contract |
| [`pre-sales-contact-ownership.md`](pre-sales-contact-ownership.md) | Contact value vs behavior split |
| [`specs/architecture/prompt-builder-rules.md`](../../specs/architecture/prompt-builder-rules.md) | PromptBuilder implementation spec (partial sync — see §9) |
| [`tasks/done/HF-1-history-safety-promptbuilder.md`](../../tasks/done/HF-1-history-safety-promptbuilder.md) | HF-1 implementation record |
| [`tasks/done/P0-global-alpstein-contamination-fix.md`](../../tasks/done/P0-global-alpstein-contamination-fix.md) | Business gating record |
| [`tasks/done/P1-remove-legacy-pre-sales-task-appendix.md`](../../tasks/done/P1-remove-legacy-pre-sales-task-appendix.md) | Appendix removal record |
