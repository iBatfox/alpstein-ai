# P0 — Global Alpstein contamination fix

**Status:** Done (pending human review)  
**Date:** 2026-05-24

## Problem

§2 task_instructions applied Alpstein pre-sales appendix and Alpstein greeting intro to all tenants (e.g. barbershop demo).

## Fix

Single gate: `alpstein_product_behavior_enabled_for_business()` in `conversation_intent_policy.py`.

| Tenant | §2 |
|--------|-----|
| `alpstein_ai_demo_001` | Core task + pre-sales charter + intent slice + Alpstein greeting |
| All others | Core task + generic greeting only |

`PRE_SALES_TASK_APPENDIX` no longer injected at runtime (constant retained for tests/docs only).

## Verify

```bash
cd backend && .venv/bin/pytest tests/test_product_behavior_gating.py tests/test_greeting_prompt_builder.py -q
```
