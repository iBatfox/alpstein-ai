# Orange Park Dialog Engine v3 Cutover Audit

Audit date: 2026-06-15

## Result

Orange Park is deployed on Dialog Engine v3. The active backend, PostgreSQL
configuration, and existing n8n workflow now agree on the v3 runtime.

- No commit or push was performed.
- No Bitrix secret was changed or printed.
- Shared AI, PromptBuilder, `LegacyWebhookFlow`, and
  `operator_business_context` behavior for other businesses remains intact.

## Runtime Changes

### Removed Or Retired Orange Park Legacy Logic

- Removed the Orange Park-specific `_operator_business_context_for_prompt`
  compatibility bypass.
- Removed old deterministic consultant replies, history-guessed area fallback,
  budget/contact guards, idle confirmation contact triggers, AI-text contact
  button scanning, and v1/v2 metadata compatibility branches.
- Removed the stale Orange Park operator overlay from the active n8n workflow.
- Kept shared platform AI and webhook behavior for non-Orange Park businesses.

### Completed v3 State Consumers

- `qualification` now consumes living/investment purpose and advances to
  apartment type selection.
- `purchase_path` now consumes full payment, installment, and financing
  answers.
- 2-room, 3-room, and 4-room markers route to apartment sales.
- Idle `Так`, `Ок`, and `Давай` do not request contact.

Deterministic v3 intents remain:

- `about_project`
- `apartment_sales`
- `commercial_sales`
- `purchase_terms`
- `manager_contact`
- `unknown`

## Deployed Backend

- Container: `alpstein_backend`
- Image: `alpstein-ai-backend:local`
- Health: `healthy`
- Ready endpoint: passed
- `/app/app/services/orange_park_dialog_service.py`: present
- `OrangeParkDialogService` import: passed
- Deployed service/seed search for `orange_park_v2` and
  `contact_flow_version`: no matches

The backend was rebuilt and recreated without recreating PostgreSQL.

## Seed And Database

The seed was run inside the deployed backend container so it used the same
migration-0027 database as the active runtime.

- Dry-run: passed and rolled back.
- Normal seed: passed and committed.
- Business language: `uk`.
- AI metadata: `dialog_engine_version=orange_park_v3`, `language=uk`,
  Bitrix contact sync enabled.
- Telegram channel metadata: `dialog_engine_version=orange_park_v3`,
  `language=uk`, Bitrix contact sync enabled.
- Default flow metadata: `dialog_engine_version=orange_park_v3`,
  `language=uk`, `crm.bitrix.enabled=true`.

Exactly six Orange Park sources are active:

1. `01_business_profile`
2. `02_sales_presentation`
3. `03_sales_scenarios`
4. `04_purchase_rules`
5. `05_apartment_catalog`
6. `06_commercial_catalog`

The following old rows remain for audit history but are inactive:

- `Orange Park FAQ`
- `Orange Park Prices And Availability - Manager Confirmed Only`
- `Orange Park Conversation Style Guide`

## n8n

- Existing workflow ID retained: `LOVCcKZ1YAMnBIFg`
- Existing workflow name retained: `orange-park-telegram-mvp`
- Active after import and restart: yes
- Node count retained: 5
- Process retained:
  `Telegram Trigger -> Normalize -> POST Backend -> Shape Reply -> Send`
- Telegram credentials/settings retained.
- `operator_business_context` removed from Orange Park normalization and POST.
- `No Bitrix24` removed.
- Native `request_contact: true` button shaping retained.
- No Bitrix node was added.

## Runtime Smoke

The smoke used the deployed HTTP webhook and the same normalized payload
contract sent by n8n.

- `/start`: Ukrainian v3 greeting.
- Stale manager-contact state followed by `/start` and `Так`: no contact
  request, proving reset history is ignored.
- `Розкажіть про ЖК`: v3 project reply.
- `Які є квартири?`: v3 apartment path.
- Two-room living-purpose phrase: consumed without premature handoff.
- `Які є умови покупки?`: v3 purchase terms.
- `Розтермінування`: purchase-path state consumed.
- Manager request: contact metadata returned immediately.
- No manual phone form or surname question appeared.
- No internal materials/docs/RAG wording appeared.

Orange Park PromptRun count was `129` before and `129` after the deterministic
smoke and contact checks. Normal v3 paths did not enter PromptBuilder/AI Gateway.

Provider limitation: a real Telegram customer account was not available in the
workspace, so Telegram-side delivery and visual button rendering were not
observed. The active workflow, normalized contract, backend response metadata,
and button-shaping code were verified separately.

## Bitrix

A pre-existing, clearly labeled Bitrix test customer was reused. No real
customer phone was printed.

- Manager request returned native contact-request metadata.
- First contact share: updated lead `39001`.
- Second distinct contact share: updated the same lead `39001`.
- Duplicate lead created: no.
- `lead_created=false`, `lead_updated=true`.
- Source: Telegram.
- Customer confirmation:
  `Дякуємо. Запит передано менеджеру. Очікуйте дзвінок.`
- Bitrix failure containment remains covered by webhook tests: CRM failure does
  not block that customer confirmation.

## Tests

Required:

- `tests/test_orange_park_dialog_service.py`: 26 passed.
- `tests/test_webhook_message_service.py`: 20 passed, one existing
  `datetime.utcnow()` deprecation warning.
- `tests/test_orange_park_bitrix_service.py`: 7 passed.

Broader relevant suite:

- Seed, Orange Park workflow, webhook route, and message service: 32 passed.
- Focused seed/dialog run during deployment fixes: 31 passed.
- `git diff --check`: passed.

Tests were added or rewritten for qualification, purchase path, 2/3/4-room
routing, `/start` reset, idle confirmations, native contact metadata, contact
payload, Bitrix success/failure, seed metadata, workflow overlay removal, and
non-Orange Park AI wiring.

## Remaining Legacy References

No requested legacy phrase remains in active Orange Park backend code, seed
content, business docs, or the Orange Park n8n workflow.

Excluding this report and the cleanup report that enumerate the search terms,
remaining Orange Park legacy occurrences are:

- `orange_park_v1`: historical pre-cutover runtime audit only.
- `orange_park_v2` and `contact_flow_version`: historical contact diagnostics,
  response-scenario audit, and pre-cutover runtime audit.
- `No Bitrix24`: those historical audits/diagnostics and the historical
  Telegram-only plan; one negative workflow test asserts it is absent.
- `manual contact form`: historical configuration trace and historical native
  contact-button task.
- `Ім'я:` and `Прізвище:`: historical configuration trace and historical
  budget/contact task.
- `Телефон:`: the same historical files plus one negative webhook test
  assertion proving the label is absent from customer replies.
- `у матеріалах`: cleanup report search accounting only.
- `документації`: historical customer-wording task plus cleanup report search
  accounting.

All prior task/audit files containing obsolete behavior are now marked
historical or superseded at the top.

`operator_business_context` remains intentionally in shared platform schemas,
PromptBuilder/orchestration, observability, specs, unified non-Orange
workflows, tests, and historical platform tasks. It is a supported shared
contract and was removed only from the active Orange Park workflow/runtime.

## Git Status

Final status is dirty as expected:

- 18 modified tracked files
- 14 deleted legacy Orange Park documentation files
- 21 untracked files/directories
- 53 status entries

The changes include the v3 dialog and Bitrix services, seed/config updates,
tests, active workflow export cleanup, six new knowledge-source directories,
deleted legacy Orange Park docs, and historical task annotations. Pre-existing
unrelated worktree changes were not reverted.

No commit or push was performed.
