# T-orange-park-customer-facing-wording

> Historical record only. Superseded by Orange Park Dialog Engine v3.

## Goal

Remove internal documentation and retrieval terminology from Orange Park
Telegram customer replies.

## Scope

- Orange Park Telegram AI policy.
- Orange Park conversation style guide.
- Deterministic Orange Park replies in `WebhookMessageService`.
- Focused tests and live backend smoke.

## Requirements

- Do not mention internal materials, documentation, source files, prompts,
  context, RAG, knowledge bases, or similar implementation details to customers.
- Keep replies helpful, concise, and sales-consultant oriented.
- Do not invent prices, availability, discounts, or financing terms.
- Keep manager confirmation for current or unstable commercial information.
- Do not change Bitrix or n8n.

## Tests

- One-room reply contains no internal wording.
- Purchase-terms reply contains no internal wording.
- Numeric area fallback contains no `документації`.
- Replies remain helpful and contain no invented price or availability.
- Run focused and broader relevant tests.

## Out Of Scope

- Bitrix behavior.
- n8n workflows.
- Other businesses or channels.
- Commit or push.

## Implementation Result

- Added an Orange Park policy rule prohibiting internal retrieval and
  documentation terminology in customer-facing replies.
- Reworded availability and financing examples in the conversation style guide.
- Reworded deterministic purchase, one-room, and numeric-area replies.
- Added assertions rejecting:
  - `матеріал`
  - `документац`
  - `source`
  - `context`
  - `база знань`
- Retained manager confirmation for exact current terms and availability.
- No Bitrix or n8n changes were made for this task.

## Validation

- Focused Orange Park suite: 46 passed.
- Full backend suite: 800 passed, 4 skipped.
- Python compile check: passed.
- `git diff --check`: passed.
- Live backend smoke passed for:
  - `/start`
  - `Цікавить 1-кімнатна квартира`
  - `Які є умови покупки?`
  - `Мене цікавить до 35 квадратів`
  - `25`
- No live reply contained a prohibited internal marker.
- Orange Park configuration seed dry-run passed against the active Compose
  database, then the scoped seed was committed successfully.
- Backend container is healthy.
- No commit or push performed.
> Historical record only. Superseded by Orange Park Dialog Engine v3. Wording
> examples below do not describe active customer responses.
