# T-orange-park-v3-legacy-cleanup

## Goal

Remove obsolete Orange Park dialog logic, metadata compatibility, seed content,
and documentation after Dialog Engine v3.

## Scope

- Remove remaining Orange Park-specific legacy handling from the webhook
  service and tests.
- Remove stale Orange Park operator context from the active n8n workflow.
- Keep only the six v3 Orange Park knowledge sources active after seeding.
- Rewrite or clearly mark obsolete Orange Park documentation as historical.
- Preserve v3 dialog, Telegram contact, Bitrix sync, and tenant isolation.

## Required Validation

- Run the Orange Park seed in dry-run and commit modes.
- Run the three required focused test files.
- Run relevant broader webhook, workflow, and seed tests.
- Search and report all remaining requested legacy strings.
- Do not commit or push.

## Implementation Report

### Removed Legacy Runtime

- Removed the Orange Park-specific `_operator_business_context_for_prompt`
  bypass from `WebhookMessageService`.
- Renamed the stale stage-one business/channel gate to
  `_is_orange_park_telegram`.
- Removed the stale Orange Park operator overlay from the active n8n workflow.
- The prior v3 implementation already removed:
  - deterministic consultant reply helpers;
  - history-guessed area fallback helpers;
  - budget/contact guards;
  - broad idle `Так`/`Ок` contact triggers;
  - AI-text contact-button scanning;
  - v1/v2 metadata compatibility branches.

Shared `operator_business_context` transport and AI orchestration remain for
other businesses. Orange Park v3 does not use that AI path.

### Rewritten Tests

- Updated webhook tests to validate v3 state and deterministic routing only.
- Kept coverage for `/start`, apartment area state, direct manager handoff,
  native contact button metadata, contact payload, Bitrix success/failure, and
  other-business AI wiring.
- Updated seed tests for:
  - `dialog_engine_version=orange_park_v3`;
  - Ukrainian language;
  - Bitrix contact sync enabled;
  - exactly six active v3 source definitions;
  - obsolete knowledge deactivation.

### Documentation Cleanup

- Deleted the obsolete pre-v3 facts, sales materials, FAQ, pricing,
  policy, promotion, conversation-style, and transcript files.
- Rewrote `docs/businesses/orange-park/README.md` around the six active v3
  sources.
- Marked old Orange Park task/audit documents containing legacy behavior as
  historical and non-runtime.

### Seed Result

Dry-run succeeded and rolled back:

- tenant: `orange-park`;
- business: `orange-park`;
- six v3 sources created in the transaction;
- obsolete sources deactivated in the transaction.

Normal seed succeeded and committed for:

- tenant id: `45bc74ec-7481-4369-a2c8-b2b9933e23d9`;
- business id: `fc001d9d-b5b1-4260-ba15-d28b30964b56`.

Committed DB verification:

- language: `uk`;
- AI profile dialog version: `orange_park_v3`;
- channel dialog version: `orange_park_v3`;
- AI/channel Bitrix contact sync: enabled;
- active sources: exactly `01_business_profile`,
  `02_sales_presentation`, `03_sales_scenarios`, `04_purchase_rules`,
  `05_apartment_catalog`, and `06_commercial_catalog`.

### Test Results

- `tests/test_orange_park_dialog_service.py`: 22 passed.
- `tests/test_webhook_message_service.py`: 20 passed.
- `tests/test_orange_park_bitrix_service.py`: 7 passed.
- Broader seed/workflow/webhook/message suites: 44 passed.
- JSON validation, Python compile, and `git diff --check`: passed.

Existing unrelated `datetime.utcnow()` deprecation warnings remain.

### Remaining Requested References

- `orange_park_v1`: none.
- `orange_park_v2`: historical-only references in:
  - `T-orange-park-contact-flow-and-metadata-diagnostics.md`;
  - `T-orange-park-response-scenario-audit.md`.
- `contact_flow_version`: historical-only references in the same two files.
- `No Bitrix24`: historical-only references in:
  - `T-orange-park-contact-flow-and-metadata-diagnostics.md`;
  - `T-orange-park-response-scenario-audit.md`;
  - `T-orange-park-telegram-only-mvp-plan.md`.
- `manual contact form`: historical-only references in:
  - `T-orange-park-full-configuration-trace.md`;
  - `T-orange-park-telegram-contact-button-only.md`.
- `Ім'я:` and `Прізвище:`: historical-only references in:
  - `T-orange-park-budget-contact-guard.md`;
  - `T-orange-park-full-configuration-trace.md`.
- `Телефон:`:
  - the same two historical files;
  - one negative webhook assertion proving the customer reply does not contain
    that manual-form label.
- `у матеріалах`: none outside original intake.
- `документації`: one historical wording task:
  - `T-orange-park-customer-facing-wording.md`.
- `operator_business_context`: remains as a shared platform webhook,
  observability, prompt-building, and non-Orange workflow contract. It remains
  in shared backend schemas/services/tests, architecture/audit/ops docs,
  unified ingress workflow skeletons, and historical platform tasks. It was
  removed from the active Orange Park n8n workflow and no Orange Park-specific
  compatibility helper remains.

### Live Smoke

Not run. The workflow file was updated locally, but no deploy was requested or
performed.

### Git Status

The worktree remains dirty with the Orange Park v3/Bitrix implementation,
cleanup changes, deleted legacy docs, six new knowledge directories, historical
task annotations, and unrelated pre-existing changes under `docs/interview`,
BCB task records, observability tests, config, Compose, and migration files.
No commit or push was performed.
