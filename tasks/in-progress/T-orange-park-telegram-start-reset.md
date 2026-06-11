# T-orange-park-telegram-start-reset

## Goal

Handle Orange Park Telegram `/start` before AI prompt construction so stale conversation history is not loaded into Prompt Builder or AI Gateway.

## Scope

- Add an Orange Park Telegram-only `/start` guard in backend webhook processing.
- Persist the incoming `/start` and outgoing welcome message.
- Archive pre-start prompt history for the same Orange Park Telegram conversation/customer.
- Add focused tests.

## Requirements

- Detect exact `/start` and `/start ...`.
- Scope by Orange Park tenant/business/channel/customer conversation.
- Do not call AI Gateway.
- Do not load old conversation history into Prompt Builder.
- Do not create PromptRun.
- Do not create lead.
- Do not call Bitrix or any CRM integration.
- Do not delete knowledge/profile/config rows.

## Validation

- Targeted backend tests.
- Orange Park webhook `/start` smoke test.
