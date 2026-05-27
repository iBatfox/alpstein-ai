**Doc status:** runtime-derived  
**Tier:** conversational/policies (pending move)  
**Canonical anchor:** [`canonical-runtime-architecture.md`](canonical-runtime-architecture.md) §6 — CIP-B **implemented** for `alpstein_ai_demo_001`; CIP-C/D open

# Conversation Intent Policy — MVP architecture spec

**Status:** CIP-A done · **CIP-B implemented** (prompt assembly + orchestration wire) · CIP-C Langfuse pending  
**Date:** 2026-05-25 (updated 2026-05-24)  
**Authoring context:** Reviewer approved intent-based routing but warned that §2 `task_instructions` is overloaded. This spec defines a **replacement** for the monolithic `PRE_SALES_TASK_APPENDIX`, not an addition on top of it.

**Related (current runtime):**

| Document / code | Role |
|-----------------|------|
| [`greeting-orchestration-mvp.md`](greeting-orchestration-mvp.md) | Conversation **lifecycle** greeting (first / follow-up / soft return) — **keep separate** |
| [`technical-pre-sales-behavior-mvp.md`](technical-pre-sales-behavior-mvp.md) | Describes today’s always-on `PRE_SALES_TASK_APPENDIX` — **to be refactored** per this spec |
| [`prompt-builder-rules.md`](../../specs/architecture/prompt-builder-rules.md) | Canonical section ordering |
| `backend/app/services/pre_sales_prompt_instructions.py` | Current monolithic appendix (~54 lines, every turn) |

**Scope of this document:** architecture and behavior contract only.

**Implemented (CIP-B):** `ConversationIntentService` wired in `AiReplyOrchestrationService` for `alpstein_ai_demo_001` only; §2 uses `PRE_SALES_CORE_CHARTER` + one intent slice; legacy `PRE_SALES_TASK_APPENDIX` retained for other businesses.

**Still pending:** CIP-C Langfuse metadata, CIP-D live smoke, DB/tenant content edits.

---

## 1. Problem

### 1.1 §2 `task_instructions` is too large

Today `PromptBuilderService.build_reply_to_customer` assembles section **2** as:

```text
PLATFORM_TASK_REGISTRY["reply_to_customer"]
  + PRE_SALES_TASK_APPENDIX   ← always appended (~54 lines)
  + greeting block            ← when GreetingPolicyService supplies policy
```

Every customer turn receives the **full** pre-sales appendix: CRM rules, pricing rules, contact policy, channel lists, implementation capture, closing rules, and style constraints — regardless of whether the customer asked “hello”, “how much?”, or “can you integrate Bitrix?”.

**Observed effects (engineering / review):**

- **Brochure tone** — model defaults to capability lists and marketing phrasing because broad “explain Alpstein” guidance is always active.
- **Rule conflict** — contact/CRM/pricing/off-topic instructions compete in the same turn; the model picks inconsistent subsets.
- **Compliance drop** — when too many platform rules are always on, the model follows the loudest fragment (e.g. repeated contact ask, German-only onboarding from history + profile) instead of the turn-relevant rule.
- **Prompt budget waste** — `task_instructions` grows before variable sections; truncation hits tenant/knowledge/history first (`VARIABLE_SECTION_TRIM_ORDER`), while the bloated §2 remains intact.

### 1.2 This spec’s mandate

**Conversation Intent Policy** must **replace** monolithic pre-sales behavior with:

1. A **small static core charter** (always on).
2. **One active intent behavior slice** per turn (heuristic-selected).
3. **Greeting orchestration** unchanged in responsibility but composed clearly alongside intent (not merged into intent detection).

**Net effect:** smaller average §2 size, not larger.

---

## 2. Design principles

| Principle | Rule |
|-----------|------|
| **Short static core** | Core charter ≤ ~25 lines / ~1.2k characters target (implementation may enforce soft cap in tests). |
| **Dynamic per turn** | Exactly **one** `intent_behavior` block appended after core charter for the resolved intent. |
| **No giant prompt** | Intent slices are compact (≤ ~15 lines each target). Full appendix text must not be duplicated across slices. |
| **Backend-only routing** | `ConversationIntentService` runs in Python before Prompt Builder; **no n8n intent logic**. |
| **No LLM classifier (MVP)** | Heuristics on current message (+ optional previous customer line for short replies). |
| **No LangGraph / multi-agent** | Single `reply_to_customer` path; no subgraphs or tool loops. |
| **Platform authority** | Intent blocks live in section **2** with core task + greeting; tenants cannot override via `operator_business_context` or profiles. |
| **Replace, don’t stack** | On implementation, `PRE_SALES_TASK_APPENDIX` is **removed** or reduced to core charter only — intent policy is not layered on the full legacy appendix. |

**Non-goals (MVP):** intent persistence in DB, per-tenant intent catalogs, multilingual intent models, confidence-based routing to a second model.

---

## 3. Prompt composition target

### 3.1 Current (as of 2026-05-25)

```text
1. platform_system          ← prompt_templates.system_prompt
2. task_instructions        ← reply_to_customer registry
                              + PRE_SALES_TASK_APPENDIX (full, always)
                              + greeting block (optional)
3. tenant_business_context  ← DB + optional operator_business_context
4. tenant_behavior
5. channel_rules
6. knowledge
7. conversation_history
8. current_customer_message
```

### 3.2 Target (after Conversation Intent Policy implementation)

```text
1. platform_system
2. task_instructions
     ├── reply_to_customer (short core task from registry — unchanged role)
     ├── PRE_SALES_CORE_CHARTER (new, short — replaces bulk of appendix)
     ├── INTENT_BEHAVIOR: <one slice>   ← ConversationIntentService
     └── GREETING ORCHESTRATION block   ← GreetingPolicyService (when applicable)
3–8. unchanged
```

### 3.3 Assembly order inside §2 (fixed)

```text
[core task]
[core charter]
[intent_behavior slice for resolved intent]
[greeting block if greeting_policy present]
```

Greeting block **after** intent slice so lifecycle greeting does not override intent-specific contact/pricing rules for that turn.

### 3.4 Size budget (MVP targets — for tests / review)

| Block | Target max (chars) | Notes |
|-------|-------------------|--------|
| Core task (`reply_to_customer`) | existing registry | No growth |
| Core charter | ~1,200 | Role, style, global safety one-liners |
| Active intent slice | ~900 | One intent only |
| Greeting block | existing | Per `greeting-orchestration-mvp.md` |
| **Total §2** | ~3,500 soft cap | Must be **less than** current appendix + registry + greeting typical stack |

---

## 4. Intent list (MVP)

Canonical enum `ConversationIntent` (implementation name):

| Intent ID | Alias in docs | Description |
|-----------|---------------|-------------|
| `social_greeting` | greeting / social opener | Pure hello, thanks, bye, small talk without a technical/buying question |
| `technical_interest` | default | Product/capability/integration questions at medium depth |
| `implementation_interest` | buying / build intent | Clear desire to start, deploy, buy, or book a call |
| `pricing_interest` | commercial | Price, cost, timeline, contract, budget |
| `unsupported_system` | CRM/platform gap | Named system Alpstein may not support; integration feasibility |
| `confused_customer` | clarification | Vague, contradictory, or “I don’t understand” |
| `off_topic` | guardrail | Clearly outside Alpstein AI scope |

**Default intent:** `technical_interest` when no higher-priority rule matches.

**Scope (MVP product):** Primarily **`alpstein_ai_demo_001`** / Alpstein AI assistant persona. Other demo businesses may keep legacy behavior until a follow-up spec extends intent policy (see §13 open questions).

---

## 5. Greeting separation

Two orthogonal policies contribute to §2:

| Service | Input | Output | Controls |
|---------|--------|--------|----------|
| **`GreetingPolicyService`** | `ConversationHistory`, current message, timestamp, optional `raw_payload` | `GreetingPolicy` (`first_contact` \| `follow_up` \| `soft_return`, language) | Whether to **introduce** Alpstein AI, avoid full intro repeat, soft return tone |
| **`ConversationIntentService`** | Current message text, optional previous **customer** message | `ConversationIntent` + `matched_rule` id for tracing | **What kind of answer** this turn needs (pricing vs technical vs social, etc.) |

### 5.1 Interaction rules

- Both may apply on the same turn (e.g. `first_contact` + `technical_interest` → intro allowed by greeting block + technical depth by intent slice).
- **`social_greeting`** intent is about **message content** (“Hi”, “Thanks”) — not the same as `GreetingMode.FIRST_CONTACT`.
  - Example: first message “Hello” → likely `social_greeting` + `first_contact` → short warm reply + intro per greeting block; intent slice limits brochure dumping.
  - Example: fifth message “Hi again” → `social_greeting` + `follow_up` → brief reply, no full intro (greeting), no CRM lecture (intent).
- Greeting block must **not** re-embed full pre-sales CRM/pricing rules (those live in intent slices only).

### 5.2 Language

- Reply language remains owned by **`GreetingPolicyService`** / `customer_language_detection` (unchanged).
- Intent slices refer to “reply in the customer’s language” without redefining detection logic.

---

## 6. Intent behavior table

Each slice is platform-controlled text in `intent_prompt_instructions.py` (planned). Wording below is **normative for implementation**.

### 6.1 `social_greeting`

| Aspect | Rule |
|--------|------|
| **Purpose** | Acknowledge social openers without launching a sales narrative |
| **Expected behavior** | 1–3 sentences; warm, human; optional light “how can I help?” |
| **Avoid** | Capability lists, CRM names, pricing, contact details, channel enumeration |
| **Contact policy** | Do not ask for phone/email |
| **Length** | Short (≤ ~400 chars reply target) |

### 6.2 `technical_interest` (default)

| Aspect | Rule |
|--------|------|
| **Purpose** | Answer product/integration questions at **medium** technical depth |
| **Expected behavior** | Direct answer first; 1 concrete example if helpful; mention channels/CRM only when relevant to the question |
| **Avoid** | Marketing brochure lists; deep internal stack dumps; guaranteed integrations |
| **Contact policy** | No contact unless customer asked how to reach a human |
| **Length** | Medium (≤ ~900 chars typical) |

### 6.3 `implementation_interest`

| Aspect | Rule |
|--------|------|
| **Purpose** | Move qualified interest toward human follow-up |
| **Expected behavior** | Confirm understanding of need; ask for **phone or email** (and optional company + one-line task); offer short call/follow-up |
| **Avoid** | Inventing price/timeline; repeating full product tour |
| **Contact policy** | Use contact details from **OPERATOR BUSINESS NOTES** only if present; else ask customer for phone/email — **no hardcoded backend contacts** |
| **Length** | Medium-short |

### 6.4 `pricing_interest`

| Aspect | Rule |
|--------|------|
| **Purpose** | Handle commercial questions safely |
| **Expected behavior** | No invented numbers; ask scope questions (channels, volume, CRM); offer human follow-up for quote |
| **Avoid** | Specific CHF/USD figures, contract terms, discounts unless in reference data |
| **Contact policy** | Offer human follow-up; contact details only if asked |
| **Length** | Short–medium |

### 6.5 `unsupported_system`

| Aspect | Rule |
|--------|------|
| **Purpose** | Named CRM/ERP/tool outside known support |
| **Expected behavior** | Honest feasibility framing (API/webhook review may be possible); no certified-connector claims |
| **Avoid** | “We fully support X” without evidence; listing every CRM |
| **Contact policy** | Suggest technical review / human contact when customer wants to proceed |
| **Length** | Short–medium |

### 6.6 `confused_customer`

| Aspect | Rule |
|--------|------|
| **Purpose** | Reduce confusion |
| **Expected behavior** | One simple clarifying question OR one concrete example (not both long); restate what Alpstein does in one sentence |
| **Avoid** | Long essays; multiple numbered menus |
| **Contact policy** | None unless customer asks |
| **Length** | Short |

### 6.7 `off_topic`

| Aspect | Rule |
|--------|------|
| **Purpose** | Bound the assistant scope |
| **Expected behavior** | Brief polite decline; one line on what Alpstein AI can help with; invite relevant question |
| **Avoid** | Encyclopedia answers; unrelated tutorials; roleplay |
| **Contact policy** | None |
| **Length** | Short (≤ ~350 chars) |

---

## 7. Detection rules (MVP heuristics)

**Classifier:** none (no LLM, no embedding similarity in MVP).

### 7.1 Inputs

1. **`current_customer_message`** — primary signal (required).
2. **`previous_customer_message`** — optional; used only when current message is “short reply” (≤ 4 words or ≤ 30 chars) to inherit topic (e.g. “Yes”, “Ok”, “Tell me more”).

**Not used for intent (MVP):** conversation history beyond previous customer line, `operator_business_context`, knowledge snippets, n8n metadata.

### 7.2 Normalization

- Lowercase for matching; strip punctuation for token rules.
- Detect language for keyword lists: apply **RU / DE / EN** keyword sets where listed; fallback to EN.

### 7.3 Priority order (first match wins)

Evaluate in this order — **stop at first match**:

| Priority | Intent | Heuristic summary (implement as named rules) |
|----------|--------|-----------------------------------------------|
| 1 | `confused_customer` | Phrases: “don’t understand”, “confused”, “what do you mean”, “не понял”, “не понимаю”, “что это”, “was meinst du” |
| 2 | `pricing_interest` | Price/cost/budget: “price”, “cost”, “how much”, “pricing”, “цена”, “сколько стоит”, “стоимость”, “Preis”, “was kostet” |
| 3 | `implementation_interest` | Buy/deploy/start: “want to implement”, “need integration”, “let’s start”, “book a call”, “хочу внедрить”, “нужна интеграция”, “начать проект” |
| 4 | `unsupported_system` | Named system + doubt verbs OR “do you support X”: Bitrix, Salesforce, HubSpot, Odoo, Zoho, ERPNext, SAP, etc. (maintain allowlist/denylist table in code) |
| 5 | `technical_interest` | Product/how questions: “how does”, “can you”, “API”, “webhook”, “n8n”, “Telegram”, “assistant”, “как работает”, “интеграция”, “API” |
| 6 | `off_topic` | Clear non-business chit-chat or unrelated domains (weather, recipes, homework) — **conservative** list to reduce false positives |
| 7 | `social_greeting` | Pure greeting/thanks/bye: “hi”, “hello”, “thanks”, “привет”, “спасибо”, “danke”, “hallo” with **no** technical/pricing tokens in same message |
| — | **default** | `technical_interest` |

### 7.4 Short-reply inheritance

If current message matches short-reply pattern and `previous_customer_message` is set:

- Re-run priority 1–4 on **previous** message only (not 5–7) to inherit `pricing_interest`, `implementation_interest`, `unsupported_system`, `confused_customer`.
- If no match, default `technical_interest`.

### 7.5 Outputs (for orchestration)

```python
@dataclass(frozen=True)
class ConversationIntentResolution:
    intent: ConversationIntent
    matched_rule: str          # e.g. "pricing_interest:en_price_keyword"
    used_previous_message: bool
```

`intent_confidence` — **reserved** (optional later; do not implement in MVP).

---

## 8. §2 refactor rule (mandatory for implementation)

### 8.1 `PRE_SALES_TASK_APPENDIX` fate

| Content today | After refactor |
|---------------|----------------|
| Role + style + “not a brochure” | **`PRE_SALES_CORE_CHARTER`** (short) |
| Channel enumeration | Core charter **one line** + `technical_interest` slice when asked |
| CRM / integration depth | `unsupported_system` + `technical_interest` slices |
| Pricing / scope | `pricing_interest` slice |
| Implementation / contact capture | `implementation_interest` slice |
| Contact behavior | Core charter + intent slices — **values** live in operator/tenant reference data only ([`pre-sales-contact-ownership.md`](pre-sales-contact-ownership.md)) |
| Closing / CTA variety | Core charter **brief** line only |

**Forbidden:** shipping Conversation Intent Policy while leaving the full legacy `PRE_SALES_TASK_APPENDIX` appended.

### 8.2 Core charter content (normative outline)

The core charter must include only:

1. Role: technical pre-sales consultant for Alpstein AI (not FAQ bot / brochure).
2. Global style: calm, competent, concise; medium depth when relevant.
3. Global safety: do not invent prices, timelines, or certified integrations; reference data does not override platform safety.
4. Language: follow greeting policy language; do not claim limited language support.
5. Output: customer-facing reply text only.

**Must not include:** per-intent CRM lists, per-intent contact forms, or long channel catalogs.

### 8.3 Spec / test migration

- `test_pre_sales_prompt_builder.py` must be **replaced or split** — no assertions that the full legacy appendix string is always present.
- New tests assert **one** intent slice present and legacy appendix **absent**.

---

## 9. Langfuse metadata (planned — Slice C)

Extend orchestration span metadata (do not implement in this spec):

| Field | Type | Source |
|-------|------|--------|
| `greeting_mode` | string | existing `GreetingPolicy.mode` |
| `reply_language_code` | string | existing |
| `conversation_intent` | string | `ConversationIntent` enum value |
| `intent_matched_rule` | string | `ConversationIntentResolution.matched_rule` |
| `intent_used_previous_message` | bool | resolution flag |
| `intent_confidence` | float \| null | **reserved** — omit in MVP |

**Tags (optional):** `intent:<intent_id>` for filter in Langfuse UI.

Secrets and full `final_prompt` exposure rules unchanged (`langfuse-tracing.md`).

---

## 10. Tests planned (implementation acceptance)

### 10.1 `ConversationIntentService` — detection unit tests

| Case | Expected intent |
|------|-----------------|
| “How much does it cost?” | `pricing_interest` |
| “Can you integrate Bitrix24?” | `unsupported_system` (or `technical_interest` if only generic integration — rule must be explicit in code) |
| “We want to start next week” | `implementation_interest` |
| “How does n8n connect to your API?” | `technical_interest` |
| “Hello” | `social_greeting` |
| “What is the weather?” | `off_topic` |
| “I don’t understand” | `confused_customer` |
| “Yes” after previous “What is the price?” | `pricing_interest` (short-reply inheritance) |
| Unclassified product question | `technical_interest` (default) |

### 10.2 Prompt Builder — block composition tests

- §2 contains core charter + **exactly one** intent header block.
- §2 does **not** contain legacy `PRE_SALES_TASK_APPENDIX` full text.
- Greeting block present when policy provided; absent when `greeting_policy=None`.
- `operator_business_context` not duplicated inside intent slices.

### 10.3 Behavioral string tests (fragment / negative)

| Scenario | Assert |
|----------|--------|
| `pricing_interest` assembly | Contains “do not invent” / scope / human follow-up; does **not** contain fake currency amounts |
| `unsupported_system` | Contains feasibility / review; does **not** contain “fully certified integration” |
| `implementation_interest` | Contains ask for phone or email |
| `technical_interest` | Medium-depth guidance present; no mandatory contact block |
| `confused_customer` | Single clarifying pattern; no long bullet menu |
| `off_topic` | Scope boundary; no encyclopedia instruction |
| `social_greeting` | No CRM platform list fragment from old appendix |

### 10.4 Regression

- Existing greeting tests remain green.
- `test_operator_business_context.py` unchanged in scope.
- Webhook integration tests: optional snapshot that §2 size decreased vs baseline (character count threshold).

---

## 11. Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Rule collisions** | Same message matches multiple intents | Strict priority order; unit tests per rule |
| **Overgrowing intents** | Adding intents duplicates appendix again | Cap slice size; review new intents as spec gaps |
| **History contamination** | Old `ai` replies bias model despite smaller §2 | Document unchanged; optional future “history summarize” out of scope |
| **Duplicated guidance** | Core charter repeats intent slice | Charter review checklist; test for duplicate phrases |
| **Premature classifier** | Pressure to add LLM intent before heuristics stable | Explicit MVP ban; revisit only after Langfuse intent metrics |
| **False `off_topic`** | Legitimate edge questions rejected | Conservative off_topic keywords; default to `technical_interest` when unsure |
| **Business scope creep** | Intent policy applied to barbershop demo | MVP scope flag per `business_id` or template key (see open questions) |
| **Implementation stacking** | Developer appends intent on full appendix | §8 refactor rule + failing test if legacy appendix present |

---

## 12. Implementation slices (post-approval)

**Do not start until this spec is reviewed and approved.**

| Slice | ID | Deliverable | Depends on | Suggested skill |
|-------|-----|-------------|------------|-----------------|
| **A** | CIP-A | `ConversationIntent` enum + `ConversationIntentService` + `matched_rule`; detection tests only | Spec approval | **Done** |
| **B** | CIP-B | `PRE_SALES_CORE_CHARTER` + per-intent blocks; Prompt Builder wire; legacy appendix gated; prompt tests | CIP-A | **Done** |
| **C** | CIP-C | Langfuse metadata fields | CIP-B | alpstein-backend-engineer |
| **D** | CIP-D | Live Telegram smoke (exec log): pricing, greeting, implementation, confused — Langfuse verify intent + smaller §2 | CIP-C, T14 runtime | alpstein-n8n-integration-engineer |

**Parallel constraint:** CIP-B must not merge without §8 refactor (net smaller §2).

**Suggested spec follow-up (optional):** add §4.5 to `prompt-builder-rules.md` when CIP-B starts (implementation task, not this doc).

---

## 13. Out of scope

- DB migration or storing intent on `messages` / `conversations`
- n8n workflow or operator intent fields
- Vector DB / RAG changes
- LangGraph, multi-agent, tool calling
- Lead scoring or notification policy changes based on intent
- Analytics dashboard / ATTR attribution pipeline
- New channels (WhatsApp, website chat adapters)
- LLM-based intent classifier
- Editing `tenant_business_profiles` or seed SQL in the same slice as CIP-B (content cleanup is separate ops)

---

## 14. Open questions (for reviewer)

1. **Business scope:** Intent policy for `alpstein_ai_demo_001` only, or all businesses using `reply_to_customer`?
2. **Bitrix message:** Classify as `unsupported_system` vs `technical_interest` when message is “integrate Bitrix” without doubt framing — pick one rule and document in CIP-A tests.
3. **`off_topic` aggressiveness:** Should uncertain messages default to `technical_interest` instead of `off_topic` (recommended: yes — keep off_topic list small)?
4. **`social_greeting` vs first message technical hook:** If user says “Hi, how much?” — pricing wins (priority 2); confirm no special case needed.
5. **Lead signals:** Should `implementation_interest` align with `LeadSignalDetectionService` handoff keywords, or remain independent (recommended: independent in MVP; align in P1)?
6. **prompt-builder-rules.md:** Update canonical spec in same PR as CIP-B or separate doc PR?

---

## 15. Approval gate

| State | Meaning |
|-------|---------|
| **This document** | Draft for review |
| **Implementation** | May start **Slice CIP-A** after explicit reviewer/founder approval of this file and resolution of §14 |
| **Runtime** | Unchanged until CIP-B deployed |

---

## Appendix — Mapping from legacy appendix sections

| Legacy `PRE_SALES_TASK_APPENDIX` section | New home |
|------------------------------------------|----------|
| Role, style, brochure avoidance | Core charter |
| Channels list | Core charter (one line) + `technical_interest` |
| Technical topics / stack | `technical_interest` |
| CRM questions | `unsupported_system` / `technical_interest` |
| Pricing and scope | `pricing_interest` |
| Implementation interest | `implementation_interest` |
| Contact policy | Core charter (constants) + `implementation_interest` |
| Closings | Core charter (brief) |
