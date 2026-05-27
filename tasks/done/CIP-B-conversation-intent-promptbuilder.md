# CIP-B — Conversation Intent PromptBuilder wire

**Status:** Done (pending human review)  
**Date:** 2026-05-24

## Goal

Reduce §2 `task_instructions` size for Alpstein AI demo by replacing the monolithic `PRE_SALES_TASK_APPENDIX` with a short core charter plus one active intent behavior slice per turn.

## Scope delivered

- `PRE_SALES_CORE_CHARTER` + `intent_prompt_instructions.py` (7 intents)
- `PromptBuilderService` — intent path for `intent_policy_enabled=True`
- Legacy `PRE_SALES_TASK_APPENDIX` only when intent policy disabled (non–`alpstein_ai_demo_001`)
- `AiReplyOrchestrationService` resolves intent before prompt build (Alpstein demo only)
- CIP-A cleanup: short-reply inheritance uses priorities 1–4 only (`_resolve_inheritable_intents`)
- Tests: `test_conversation_intent_prompt_builder.py`, orchestration wire tests
- Docs: `conversation-intent-policy-mvp.md`, this task file

## Out of scope (as requested)

- CIP-C Langfuse runtime metadata
- DB migration, n8n, tenant data edits

## Verification

```bash
cd backend && .venv/bin/pytest \
  tests/test_conversation_intent_service.py \
  tests/test_conversation_intent_prompt_builder.py \
  tests/test_greeting_prompt_builder.py \
  tests/test_ai_reply_orchestration_service.py -q
```

## Live test

Telegram path on `alpstein_ai_demo_001` — confirm Langfuse §2 is shorter and contains `CONVERSATION INTENT (active turn): <intent>`.
