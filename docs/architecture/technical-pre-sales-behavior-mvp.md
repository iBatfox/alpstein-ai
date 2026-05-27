**Doc status:** historical reference only (deprecated duplicate)  
**Tier:** architecture/deprecated (pending move)  
**Canonical source:** `docs/architecture/canonical-runtime-architecture.md` (§2/§6) + `docs/architecture/conversation-intent-policy-mvp.md` (behavior spec)  
**Note:** This doc describes the pre-CIP monolithic approach and must not be used as a current runtime description.

# Technical Pre-Sales Behavior MVP

**Note:** Alpstein demo (`alpstein_ai_demo_001`) now uses **Conversation Intent Policy (CIP-B)** — see [`conversation-intent-policy-mvp.md`](conversation-intent-policy-mvp.md). This doc describes the earlier monolithic appendix approach (still used for non-intent businesses).

## Goal

Alpstein AI demo assistant acts as a **technical pre-sales consultant**, not a generic marketing FAQ bot.

## Contact ownership

- **Backend** defines *when* and *how* to use contacts (no invented details).
- **Runtime contact values** belong in `operator_business_context` (n8n) or future business contact profile — see [`pre-sales-contact-ownership.md`](pre-sales-contact-ownership.md).
- Personal names, phones, and emails in prompts must **not** be hardcoded in Python.

## Implementation (historical / legacy path)

| Layer | Change |
|-------|--------|
| **Platform task** | `PRE_SALES_TASK_APPENDIX` for non–intent-policy businesses |
| **Intent path** | `PRE_SALES_CORE_CHARTER` + per-intent slices (CIP-B) |
| **Greeting** | `greeting_prompt_instructions.py` |
| **Data** | `scripts/update_alpstein_pre_sales_behavior.sql` (tenant facts only) |

## Tests

`backend/tests/test_conversation_intent_prompt_builder.py` — intent assembly, no hardcoded contacts in §2.

## Live test

Use Langfuse to verify §2 size and `CONVERSATION INTENT` block on `alpstein_ai_demo_001`.
