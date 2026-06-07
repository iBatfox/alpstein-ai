# Alpstein AI — Prompt Builder Rules (T11.7)

## 1. Purpose

This document defines how **Prompt Builder Service** assembles the internal prompt for one AI turn in MVP.

It is the implementation contract for **T11.7** before any Python code is written. It extends [ai-configuration-architecture.md](ai-configuration-architecture.md) §5–§6 and §14 with ordering, budgeting, truncation, and exclusion rules.

**In scope:** logical prompt structure, precedence, tenant boundaries, placement of knowledge/history/latest message, budgeting and truncation.

**Out of scope (other tasks):** OpenAI HTTP (T11.8), `PromptRun` persistence (T11.10), provider message-array mapping, embeddings, prompt management UI.

---

## 2. Design brief

| Item | Decision |
|------|----------|
| **Consumer** | `AiReplyOrchestrationService` (backend); AI Gateway receives assembled logical prompt only |
| **MVP task** | `reply_to_customer` — produce customer-facing reply text for current turn |
| **Inputs** | AI Configuration Service DTOs (platform template + tenant profile/channel), `KnowledgeRetrievalResult`, `ConversationHistory`, latest customer `message_text` |
| **Output** | Provider-neutral assembled prompt (logical sections); Gateway maps to provider format later |
| **Tenant isolation** | All inputs are already scoped by `tenant_id` / `business_id`; Prompt Builder does not widen scope |
| **Risks** | Prompt injection via tenant/knowledge/customer text; token overflow; accidental inclusion of transport/AI internals |

---

## 3. Responsibilities

Prompt Builder **must**:

- assemble sections in the fixed order defined in §4;
- keep platform system content first and non-truncatable;
- treat tenant, knowledge, history, and customer text as **reference data**, not as system instructions;
- apply character budgets and truncation per §6–§7;
- return a structure AI Gateway can send without re-ordering safety content.

Prompt Builder **must not**:

- call AI providers;
- read or write PostgreSQL;
- accept `raw_payload`, webhook envelopes, or provider-native payloads;
- expose assembled prompts in public HTTP API responses.

---

## 4. Section ordering (mandatory)

Sections are assembled **top to bottom**. Lower sections are truncated before higher sections when budget is exceeded.

| Order | Section ID | Source | Role |
|------|------------|--------|------|
| **1** | `platform_system` | Active `PromptTemplate` / platform core | **System authority** — safety, role, escalation, output constraints |
| **2** | `task_instructions` | Platform task slice for `reply_to_customer` | **System authority** — what to do this turn |
| **3** | `business_context_source_of_truth` | `TenantBusinessProfile` (via AI Configuration Service); optional `operator_business_context` from webhook appended after profile text (T14-OC-2) | **Data** — source of truth for business facts, contacts, services, links, prices, locations, and working hours |
| **4** | `tenant_business_context` | Compatibility/lineage marker for tenant business layer | **Data** — no business facts; facts are emitted in `business_context_source_of_truth` |
| **5** | `tenant_behavior` | `TenantAIProfile` | **Data** — tone, language, style, handoff hints |
| **6** | `channel_rules` | `TenantChannelSetting` for current `channel` | **Data** — channel formatting constraints |
| *(future)* | `channel_source_context` | Webhook `source` + safe `attribution` subset ([channel-source-attribution.md](channel-source-attribution.md) §7) | **Data** — ingress/locale/UTM reference only |
| **7** | `knowledge` | `KnowledgeRetrievalResult.snippets` | **Data** — retrieved FAQ/policy excerpts |
| **8** | `conversation_history` | `ConversationHistory.messages` (oldest → newest) | **Data** — prior turns |
| **9** | `current_customer_message` | Incoming turn `message.text` | **Data** — message to answer now |

### 4.1 Platform system prompt always first

Section **1** (`platform_system`) is always the first content in the assembled prompt. No tenant, knowledge, history, or customer content may appear above it.

Section **2** (`task_instructions`) immediately follows platform system content. Tenant layers never precede platform layers.

### 4.2 Latest customer message always last

Section **9** (`current_customer_message`) is always the **last** section in the assembly. It is the explicit “message to answer now” and must not be buried inside history.

If the same text already appears as the newest row in `conversation_history`, Prompt Builder still emits section **9** once (deduplication inside history only: omit duplicate final history row if identical to current message; section **9** remains mandatory).

### 4.3 Knowledge snippet placement

Knowledge (**7**) sits **after** tenant configuration (**3–6**) and **before** conversation history (**8**).

Rationale: business facts and style are fixed context; knowledge grounds answers; dialogue comes last before the current turn.

### 4.4 Conversation history placement

History (**8**) sits **after** knowledge and **before** the current customer message (**9**).

Format per message (prompt-safe fields only):

```text
{sender_type}: {message_text}
```

Allowed `sender_type` values in history: `customer`, `ai`, `owner`. Skip or summarize `system` messages in MVP unless product later requires them.

`created_at` may be used for ordering only; do not render timestamps in MVP prompt text unless a future spec requires it.

### 4.5 Operator business context (webhook overlay — T14-OC)

Optional top-level `operator_business_context` on `POST /api/v1/webhook/message` ([webhooks.md](../api/webhooks.md) §7).

| Aspect | Rule |
|--------|------|
| **Spec status** | T14-OC-1 contract; T14-OC-2 implements read + append in Prompt Builder |
| **Source** | n8n Set node (“Add Business Context”) or equivalent; not from `message.text` or `raw_payload` |
| **Placement in assembly** | Inside section **3** (`business_context_source_of_truth`), **after** all text from `TenantBusinessProfile`, under a labeled sub-block (e.g. `OPERATOR BUSINESS NOTES`) |
| **Role** | Reference data only — same as DB business profile; not system authority |
| **Primary source** | PostgreSQL `tenant_business_profiles` remains canonical; operator text is **additive** |
| **Max size** | 8192 characters on webhook request; counts toward section **3** variable budget and truncation (§7) |
| **Absent** | Omit sub-block when field is `null` or omitted |

Platform sections **1–2** always precede and override operator notes. Operator text must not be promoted to `platform_system` or `task_instructions`.

---

## 5. Platform precedence and tenant boundaries

### 5.1 Platform over tenant

Rules in §1–§2 (platform + task) **always win** over tenant business profile, **operator business context**, AI profile, channel rules, knowledge, and customer text.

If tenant or knowledge text conflicts with platform safety (e.g. “ignore previous instructions”, “reveal system prompt”, “promise guaranteed booking without owner”), Prompt Builder and downstream validation must **not** apply the conflicting tenant instruction. Prefer platform rules and safe refusal/escalation behavior.

### 5.2 Tenant config is data, not system instructions

Sections **3–9** must be framed as **reference data**, not as executable system directives.

Business facts, contacts, links, services, prices, locations, and working hours must be taken only from section **3** (`business_context_source_of_truth`). Conversation history and any future customer memory are only for customer preferences and dialogue continuity; they must not override current business factual data.

Each data block (sections 3–7) must:

- use a clear header label (e.g. `TENANT BUSINESS CONTEXT`, `RELEVANT KNOWLEDGE`, `CONVERSATION HISTORY`);
- include a one-line platform guard in section **1** or **2** stating that labeled blocks are business reference only and must not override Alpstein AI safety rules.

Customer and owner lines in history are **quoted dialogue**, not instructions to the model.

### 5.3 What tenants may configure (MVP)

Tenants may influence **wording and business facts** in sections 3–6 and stored knowledge in section 7.

Tenants must **not** be able to:

- replace or prepend content before `platform_system`;
- disable escalation, hallucination limits, or secret-handling rules;
- inject provider API parameters, tool definitions, or role-switching prompts via profile fields.

### 5.4 Upstream sanitization

AI Configuration Service enforces platform-over-tenant when loading profiles. Prompt Builder still assumes untrusted text in tenant/knowledge/customer fields and must not elevate them to system authority (ordering + labeling only; optional light pattern stripping is implementation detail, not required for MVP).

---

## 6. Token and character budgeting (MVP)

MVP uses **character budgets** inside Prompt Builder (no live tokenizer dependency). AI Gateway may apply a separate provider limit when mapping to the API.

### 6.1 Default assembly budget

| Constant | Default | Notes |
|----------|---------|--------|
| `PROMPT_ASSEMBLY_MAX_CHARS` | `24_000` | Total characters across all sections after assembly |
| `PLATFORM_RESERVED_CHARS` | `6_000` | Sections 1–2; not subject to truncation |
| `CURRENT_MESSAGE_MAX_CHARS` | `8_000` | Section 8 hard cap (abuse guard); not truncated below platform reserve |
| `VARIABLE_BUDGET_CHARS` | remainder | Sections 3–7 share what is left |

Formula:

```text
variable_budget = PROMPT_ASSEMBLY_MAX_CHARS - len(sections 1-2) - len(section 8 capped)
```

### 6.2 Upstream bounds (already applied before Prompt Builder)

These services bound inputs; Prompt Builder does not re-expand them:

| Input | Upstream bound (current MVP) |
|-------|------------------------------|
| Knowledge snippets | max 5 snippets; 1_000 chars/snippet; 4_000 chars total ([T11.5](../../backend/app/services/knowledge_retrieval_service.py)) |
| Conversation history | 10–20 messages; `message_text` only in DTO ([T11.6](../../backend/app/schemas/conversation_context.py)) |

Prompt Builder may further shrink sections 3–7 inside `variable_budget` only.

### 6.3 Allocation priority inside variable budget

When `variable_budget` is tight, allocate in this order until budget is exhausted:

1. Section **9** — reserved first (after platform sections).
2. Section **8** — recent dialogue (newest messages kept).
3. Section **7** — knowledge (highest retrieval rank first).
4. Section **3** — business context.
5. Section **4** — behavior profile.
6. Section **5** — channel rules (smallest; trim last among tenant blocks).

---

## 7. Truncation strategy

Truncation applies only to sections **3–7** when their combined size exceeds `variable_budget`.

**Never truncate or drop:**

- Section **1** (`platform_system`)
- Section **2** (`task_instructions`)
- Section **9** (`current_customer_message`) — except enforce `CURRENT_MESSAGE_MAX_CHARS` with explicit suffix `[truncated]` if over cap

### 7.1 Per-section methods

| Section | Truncation method |
|---------|------------------|
| **3–5** | Trim longest fields first (e.g. services list, free-text description); append `[truncated]` once per section if trimmed |
| **6** | Drop lowest-ranked snippets first; then trim `content` tail of remaining snippets; honor `KnowledgeSnippet.truncated` flag in text |
| **7** | Remove **oldest** messages first; keep contiguous tail ending at newest message before current turn |

### 7.2 Minimum retained content

After truncation, assembly must still include:

- both platform sections in full;
- at least one of sections 3–5 if any tenant config exists (even if heavily trimmed);
- section **9** in full (within `CURRENT_MESSAGE_MAX_CHARS`).

Sections **6** and **7** may be empty if budget requires; do not fabricate placeholder knowledge or history.

### 7.3 Empty inputs

| Input missing | Behavior |
|---------------|----------|
| No knowledge snippets | Omit section **6** header body (or omit section) |
| Empty history | Omit section **8**; section **9** still present |
| Missing channel setting | Omit section **5**; platform + business rules still apply |
| No `operator_business_context` | Section **3** uses DB profile only (T14-OC-2) |

---

## 8. What must never be included

The assembled prompt must **never** contain:

| Category | Examples |
|----------|----------|
| Transport / webhook | `raw_payload`, provider event IDs, n8n node data, unsigned webhook bodies |
| AI execution internals | `ai_metadata`, `prompt_run_id`, model latency, token counts from prior runs |
| Secrets | API keys, `OPENAI_API_KEY`, admin tokens, DB connection strings, password fields |
| Security-sensitive customer fields | Full payment details; store only what MVP flows require in labeled data blocks |
| System prompt leakage targets | Full unredacted platform template in customer API responses (logging is separate) |
| Provider-specific structures | OpenAI `messages[]` roles, tool JSON, vision blocks — **Gateway maps later** |
| Instruction injection as system | Tenant/customer text promoted to section **1** or **2** |

Allowed in **history** and **current message**: plain `message_text` and `sender_type` only (per T11.6 DTO).

Knowledge snippets may include `id`, `source_type`, `title` in section headers for traceability; do not include raw DB JSON blobs or `tags` unless rendered as short human-readable labels.

---

## 9. Provider-neutral output shape (MVP)

Prompt Builder returns a logical structure, not an OpenAI payload.

Recommended internal shape (names may match implementation):

```text
AssembledPrompt
  task: "reply_to_customer"
  sections: ordered list of { section_id, label, content, kind }
    kind: "system" | "data"
```

- `kind=system` → sections **1–2** only.
- `kind=data` → sections **3–8**.

AI Gateway (T11.8) converts `AssembledPrompt` to provider messages. Prompt Builder does not set `model`, `temperature`, or HTTP headers.

---

## 10. Relationship to other components

```text
AI Configuration Service ──► platform + tenant DTOs
Knowledge Retrieval Service ──► KnowledgeRetrievalResult
MessageService ──► ConversationHistory
Incoming turn ──► message.text
        │
        ▼
Prompt Builder Service ──► AssembledPrompt
        │
        ▼
AI Gateway Service ──► provider API
        │
        ▼
PromptRun logging (separate; may store redacted assembly metadata)
```

See also:

- [incoming-message-flow.md](../flows/incoming-message-flow.md) — Steps 12–16
- [ai-configuration-architecture.md](ai-configuration-architecture.md) — configuration layers
- [entities.md](../database/entities.md) — `PromptTemplate`, `PromptRun`

---

## 11. MVP success criteria (T11.7 implementation)

Implementation is ready when tests (later task) prove:

- section order matches §4;
- platform sections are never truncated;
- tenant blocks are labeled data and appear only after platform sections;
- knowledge precedes history; current customer message is last;
- truncation drops oldest history and lowest-priority knowledge first;
- forbidden fields from §8 never appear in output;
- no HTTP and no DB writes inside Prompt Builder.

---

## 12. Future (not MVP)

- Token-accurate budgeting via model tokenizer
- Separate system/user message pairs per provider
- Additional tasks (`lead_extraction`, `summarize`, `escalation`)
- Automatic injection-safety classifier on tenant fields
- Redacted `final_prompt` storage policy for `prompt_runs` (coordinate with T11.10)
