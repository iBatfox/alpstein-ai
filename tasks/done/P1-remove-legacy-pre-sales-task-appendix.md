# P1 — Remove legacy PRE_SALES_TASK_APPENDIX

**Status:** done  
**Depends on:** P0 global Alpstein contamination fix (`8ad8489`)

## Goal

Fully remove `PRE_SALES_TASK_APPENDIX` from the active backend codebase after P0 stopped runtime assembly.

## Changes

- Deleted `PRE_SALES_TASK_APPENDIX` constant from `pre_sales_prompt_instructions.py`.
- Removed dead `_LEGACY_APPENDIX_HEADER` from `prompt_builder_service.py`.
- Updated tests: removed appendix-only baselines; contamination and intent tests retained.
- Updated `canonical-runtime-architecture.md`, `current-state.md`, `completed.md`.

## Runtime §2 (unchanged behavior)

| Business | §2 contents |
|----------|-------------|
| `alpstein_ai_demo_001` | core task + `PRE_SALES_CORE_CHARTER` + intent slice + Alpstein greeting |
| All others | core task + generic greeting only |

## Verification

- No `PRE_SALES_TASK_APPENDIX` in `backend/app/`.
- Greeting, intent, HF-1, and contamination tests green.
