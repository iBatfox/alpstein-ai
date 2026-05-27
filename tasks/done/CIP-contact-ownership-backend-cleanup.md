# Contact ownership — remove hardcoded contacts from backend prompts

**Status:** Done (pending human review)  
**Date:** 2026-05-24

## Problem

CIP-B intent slices and legacy `PRE_SALES_TASK_APPENDIX` contained hardcoded Ivan Bataiev phone/email. Contact values belong in workflow/operator context, not Python.

## Changes

- `pre_sales_prompt_instructions.py` — name preservation + contact source rules in core charter; generic contact policy in legacy appendix
- `intent_prompt_instructions.py` — implementation/technical/pricing/unsupported slices reference OPERATOR BUSINESS NOTES only
- Tests — no literal phone/email/name in assembled §2 (intent + legacy paths)
- Docs — `pre-sales-contact-ownership.md`, updates to conversation-intent and technical-pre-sales docs

## Out of scope

- n8n Set node content update (ops follow-up)
- DB / Langfuse / CIP-C

## Ops follow-up

Add business contact block to `operator_business_context` in Telegram ingress workflow — see [`pre-sales-contact-ownership.md`](../../docs/architecture/pre-sales-contact-ownership.md).
