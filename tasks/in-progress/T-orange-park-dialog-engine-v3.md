# T-orange-park-dialog-engine-v3

## Goal

Replace accumulated Orange Park Telegram response patches with one explicit,
scenario-based v3 dialog engine.

## Scope

- Route Orange Park Telegram messages through v3 intents and stages.
- Keep deterministic Ukrainian `/start`, native Telegram contact sharing, and
  Orange Park Bitrix24 create/update by phone.
- Persist explicit v3 dialog state in message metadata.
- Ignore legacy Orange Park metadata and pre-`/start` history.
- Reorganize Orange Park knowledge into six logical sources.
- Remove obsolete Orange Park v1/v2 response helpers and compatibility logic
  after v3 tests pass.

## Requirements

- Preserve tenant and business isolation on every state/history query.
- Do not invoke AI Gateway, create PromptRun records, or call Bitrix for
  `/start`.
- Do not request contact prematurely.
- Only advance short confirmations and numeric values when the active v3 state
  expects them.
- Return the native Telegram contact button immediately for manager handoff.
- Confirm contact receipt even when Bitrix synchronization fails.
- Do not hardcode live prices, availability, photos, or catalog API data.
- Do not change other businesses, global prompts, Mini App, or n8n architecture.

## Tests

- Cover the 25 scenarios listed in the task request.
- Run:
  - `.venv/bin/pytest tests/test_webhook_message_service.py`
  - `.venv/bin/pytest tests/test_orange_park_bitrix_service.py`
- Run relevant broader webhook and Orange Park configuration tests.

## Out Of Scope

- Live catalog, price, availability, photo, or gallery integrations.
- n8n redesign.
- Other tenant or business behavior.
- Commit or push.

## Implementation Result

- Added a deterministic Orange Park v3 dialog service with explicit state.
- Routed active Orange Park Telegram replies through v3 without AI Gateway or
  PromptRun creation.
- Kept native Telegram contact capture and Bitrix create/update by phone.
- Made Bitrix failures non-blocking for customer confirmation.
- Replaced the seeded Orange Park knowledge set with six v3 logical sources.
- Removed legacy response handlers, history-guessed numeric handling, broad
  idle confirmation triggers, and AI-text contact scanning.

## Verification

- `tests/test_webhook_message_service.py`: passed.
- `tests/test_orange_park_bitrix_service.py`: passed.
- Dialog, seed, Telegram workflow, webhook AI wiring, and route regressions:
  passed.
- Compile and `git diff --check`: passed.
- Live Telegram smoke was not run from this workspace.
