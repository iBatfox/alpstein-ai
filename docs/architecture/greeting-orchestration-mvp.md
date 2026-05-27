**Doc status:** runtime-derived  
**Tier:** conversational/orchestration (pending move)  
**Canonical anchor:** [`canonical-runtime-architecture.md`](canonical-runtime-architecture.md) §6 — **implemented**

# Greeting orchestration (MVP)

**Status:** Implemented (backend)  
**Date:** 2026-05-25

## Design choice

**Option B (preferred):** Backend derives greeting mode from conversation history (no DB flag, no n8n OpenAI).

| Mode | When | Assistant behavior |
|------|------|------------------|
| `first_contact` | No prior `ai` messages in conversation | Full greet + Alpstein AI intro + how can I help |
| `follow_up` | Prior `ai` messages exist | No full intro; answer directly |
| `soft_return` | Prior `ai` messages + gap ≥ 24h since last prior message | Short greeting allowed; no full intro |

Greeting rules are appended to **`task_instructions`** (platform system authority), not tenant reference sections.

## Language

1. Detect from current `message.text` (heuristics).
2. Else Telegram `message.from.language_code` from `raw_payload` when present.
3. Else English.

Supported: German, English, Russian, French, Italian, Spanish, Ukrainian.

**Never** instruct the model to claim limited language support.

## Code

| Component | Path |
|-----------|------|
| Policy | `app/services/greeting_policy_service.py` |
| Language detection | `app/services/customer_language_detection.py` |
| Prompt block | `app/services/greeting_prompt_instructions.py` |
| Wire | `AiReplyOrchestrationService` → `PromptBuilderService` |

## Limits

- Does not clear polluted `messages` history; start a new conversation/customer to drop old greeting loops.
- Model output is not deterministic; instructions reduce repetition but do not guarantee exact wording per language.

## Tests

`tests/test_greeting_policy_service.py`, `tests/test_customer_language_detection.py`, `tests/test_greeting_prompt_builder.py`
