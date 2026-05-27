# HF-1 — History Safety in PromptBuilder

**Status:** Done (pending human review)  
**Date:** 2026-05-24

## Goal

Current tenant/operator context overrides stale facts in prior assistant messages.

## Changes

- `history_safety_prompt_instructions.py` — platform preamble + `ai` sender label
- `prompt_builder_service.py` — prepend preamble in §7; trim preserves preamble
- Tests: `test_history_safety_prompt_builder.py`
- Drift table: `canonical-runtime-architecture.md`

## Out of scope

- History purge, version tokens, n8n, Langfuse, LLM filtering

## Verify

```bash
cd backend && .venv/bin/pytest tests/test_history_safety_prompt_builder.py -q
```
