# Orange Park Dialog Engine v3 Runtime Sync

## Goal

Synchronize the deterministic Orange Park runtime with the six canonical v3
documents and add platform-wide Langfuse message-turn tracing independent of
PromptRun.

## Scope

- Orange Park deterministic state consumption and documented replies.
- Platform Langfuse lifecycle for deterministic and AI webhook paths.
- Existing Telegram contact metadata, Bitrix synchronization, n8n workflow,
  and tenant/business isolation remain unchanged.
- Legacy Orange Park documents must not influence runtime.

## Canonical Documentation

1. `01_business_profile`
2. `02_sales_presentation`
3. `03_sales_scenarios`
4. `04_purchase_rules`
5. `05_apartment_catalog`
6. `06_commercial_catalog`

## Required Validation

- Deterministic state-timeline smoke.
- Langfuse span verification for deterministic and AI paths.
- Deterministic tracing without PromptRun.
- Legacy-reference/runtime check.
- Other-business regression tests.
- Final git status.

## Constraints

- No n8n workflow change.
- No Bitrix contract or secret change.
- No migration.
- No commit or push.

## Implementation Report

### Documentation Sections Consumed

- `01_business_profile`: stable project facts remain the only deterministic
  project-fact source.
- `02_sales_presentation`: consultative response style and qualification
  boundary remain unchanged.
- `03_sales_scenarios`: stage-first state consumption, explicit state fields,
  apartment/commercial progression, manager-contact gates, idle confirmation
  handling, unknown fallback, and platform trace lifecycle.
- `04_purchase_rules`: canonical mappings and general explanations for
  `full_payment`, `installment`, `e_oselya`, `financing`, and `voucher`.
- `05_apartment_catalog`: non-live 2-room reference range `56-64 м²` without
  current-availability claims.
- `06_commercial_catalog`: commercial qualification remains non-live and
  manager-confirmed.

Legacy Orange Park documents are not read by the deterministic service or the
active seed.

### Runtime Synchronization

- Made state consumption stage-first before root fallback routing.
- Added canonical state fields `commercial_type` and `budget_interest`.
- Added exact 1/2/3/4-room mappings.
- Explicit living/investment purpose now consumes `qualification`,
  `apartment_area`, or `apartment_purpose` without resetting to root.
- Type plus purpose advances to `purchase_path`.
- Numeric area is consumed only during `apartment_area`.
- 2-room replies use the documented `56-64 м²` reference and explicitly deny
  that it proves current availability.
- Added all five documented purchase-path values and path-specific general
  explanations.
- Purchase selection advances to `manager_offer`; an active affirmative reply
  advances to native Telegram contact.
- Idle `так`, `ок`, `давай`, `добре`, and `+` do not request contact.
- Manual phone text from idle no longer triggers handoff.
- Unknown fallback now uses the documented Ukrainian question.
- Commercial qualification stores `commercial_type`.
- Ukrainian default, Telegram contact metadata, Bitrix synchronization, n8n
  workflow, and tenant/business scoping were preserved.

### Langfuse Synchronization

- Added an outer `message_turn` Langfuse span around every normalized webhook
  request, independent of business and channel.
- The span starts before business resolution and finishes after the response
  or records an error.
- Existing AI generation tracing remains nested inside the message-turn span.
- Deterministic Dialog Engine paths do not create PromptRuns.
- Trace metadata records resolved tenant, business, flow, conversation,
  inbound message, processing status, deterministic intent/stage/purchase
  path, and Bitrix CRM outcome where applicable.
- Channel tags now apply to every channel value rather than Telegram only.
- Langfuse activation now depends only on configured public and secret keys;
  environment and the former feature flag do not disable tracing.
- Missing credentials remain a safe no-op because remote Langfuse
  authentication is impossible without them.
- Platform observability specs and deployment/architecture docs were updated
  to match this policy.

Deployed verification:

- Langfuse credentials configured: yes.
- Active backend reports Langfuse active: yes.
- A production `Settings` instance with `LANGFUSE_TRACING_ENABLED=false` and
  configured credentials reports tracing active.
- Six deterministic timeline turns produced six real `message_turn` traces.
- Final verification trace:
  `b9ee8fe3f35159e64e4afb88c2d73622`.
- Trace metadata: `business_id=orange-park`, `channel=telegram`.
- Observation metadata:
  `runtime_path=deterministic_dialog_engine`,
  `dialog_intent=apartment_sales`, `dialog_stage=apartment_area`.
- PromptRun count before timeline: `129`.
- PromptRun count after timeline and final trace smoke: `129`.

Bitrix trace coverage is asserted for both:

- success: `crm_sync_status=create`;
- contained failure: `crm_sync_status=failed_deferred`.

### State Timeline

Deployed deterministic smoke:

| Input | Intent | Stage | Apartment | Purpose | Purchase | Contact |
| --- | --- | --- | --- | --- | --- | --- |
| `/start` | `unknown` | `idle` | - | - | - | false |
| `Які є квартири?` | `apartment_sales` | `apartment_type` | - | - | - | false |
| `2 кімнатна` | `apartment_sales` | `apartment_area` | `2-room` | - | - | false |
| `Для проживання` | `apartment_sales` | `purchase_path` | `2-room` | `living` | - | false |
| `Повна оплата` | `apartment_sales` | `manager_offer` | `2-room` | `living` | `full_payment` | false |
| `Так` | `manager_contact` | `awaiting_contact` | `2-room` | `living` | `full_payment` | true |

The final independent `2 кімнатна` smoke returned the `56-64 м²` reference,
asked for area, did not request contact, and created a real Langfuse trace.

### Seed And Deployment

- Backend rebuilt and recreated successfully.
- Backend health: healthy.
- Existing n8n container remained running and was not changed.
- Seed dry-run: passed and rolled back.
- Normal seed: passed and committed the six canonical source contents.
- No migration was added or run by this task.

### Tests

- Orange Park dialog service: 30 passed.
- Webhook message service: 20 passed.
- Langfuse tracing service: 9 passed.
- Focused runtime/tracing set: 59 passed.
- Broader webhook, observability, route, message, AI, and platform regressions:
  62 passed.
- Full backend suite: 813 passed, 4 skipped.
- Existing `datetime.utcnow()` deprecation warnings remain.
- Python compile check: passed.
- `git diff --check`: passed.
- Active runtime legacy search: no v1/v2, contact-flow-version, manual-phone,
  stale business-type, or `No Bitrix24` behavior references.

### Files Changed By This Task

- `backend/app/core/config.py`
- `backend/app/services/langfuse_tracing_service.py`
- `backend/app/services/orange_park_dialog_service.py`
- `backend/app/services/webhook_message_service.py`
- `backend/tests/test_langfuse_tracing_service.py`
- `backend/tests/test_orange_park_configuration_seed.py`
- `backend/tests/test_orange_park_dialog_service.py`
- `backend/tests/test_webhook_message_service.py`
- `docs/architecture/canonical-runtime-architecture.md`
- `docs/architecture/langfuse-tracing.md`
- `docs/businesses/orange-park/README.md`
- `docs/businesses/orange-park/03_sales_scenarios/orange_park_sales_scenarios.md`
- `docs/deployment/deployment-contract.md`
- `specs/architecture/observability-metadata.md`
- `specs/observability/message-trace-lifecycle.md`
- `tasks/in-progress/T-orange-park-v3-runtime-sync.md`

### Git Status

The shared worktree remains dirty from the broader Orange Park v3 work and
pre-existing unrelated changes:

- 25 modified tracked files;
- 14 deleted legacy Orange Park documentation files;
- 23 untracked files/directories;
- 62 total status entries.

The existing dirty n8n export was not modified by this task. No commit or push
was performed.
