# Orange Park Dialog Engine v3 Runtime Audit

> Historical pre-cutover audit. Superseded by
> `T-orange-park-v3-cutover-audit.md`.

Audit date: 2026-06-15

Scope: repository worktree, active backend container, active PostgreSQL data,
active n8n workflow, Orange Park documentation, prompt construction, Telegram
contact flow, and Bitrix synchronization.

Constraints observed:

- no runtime code changed;
- no migrations run;
- no seed run;
- no commits created;
- no Telegram webhook or Bitrix API request sent.

## Executive Summary

Orange Park currently has three different sources of runtime truth:

1. **Active backend runtime:** an intermediate **v2 + Bitrix** build. It does not
   contain `orange_park_dialog_service.py` and still routes most messages through
   the shared AI prompt path.
2. **Active database and n8n runtime:** still carry the old Telegram MVP
   configuration, old knowledge rows, old AI policy/profile data, and an n8n
   `operator_business_context` overlay that says `No Bitrix24`.
3. **Repository worktree:** contains an uncommitted v3 deterministic engine,
   six new documents, a v3 seed, and a cleaned n8n export. This candidate is not
   the code/configuration currently serving Telegram.

The most important result is therefore:

> Dialog Engine v3 exists in the worktree but is not the active Orange Park
> runtime.

The deployed backend container reports Alembic revision `0027`, Bitrix is
configured, and the database flow has `crm.bitrix.enabled=true`, but the
container still has `ORANGE_PARK_CONTACT_FLOW_VERSION="orange_park_v2"` and the
old consultant/area/budget handlers. This is a fractured deployment: schema and
Bitrix integration are newer than the dialog engine and knowledge configuration.

## A. Active v3 Components

These components exist in the repository worktree and pass focused tests:

| Component | Worktree status | Active runtime status |
|---|---|---|
| `OrangeParkDialogService` | Implemented, deterministic v3 | **Not deployed** |
| v3 webhook short-circuit | Implemented for normal `Flow` | **Not deployed** |
| v3 dialog metadata | Implemented as `metadata.orange_park_dialog` | **Not active** |
| v3 contact metadata gate | Exact `dialog_engine_version=orange_park_v3` | **Not active** |
| six-document v3 seed | Implemented | **Not applied to active DB** |
| cleaned n8n export | Removes operator overlay | **Not imported into active n8n** |
| Bitrix create/update service | Implemented | **Active in deployed intermediate build** |
| migration `0027` | Present in worktree | **Applied; DB is at `0027`** |

Focused verification:

```text
34 passed in 1.76s
```

Tests:

- `backend/tests/test_orange_park_dialog_service.py`
- `backend/tests/test_orange_park_configuration_seed.py`
- `backend/tests/test_orange_park_bitrix_service.py`

## B. Remaining Legacy Components

### Active deployed runtime

The active backend container still contains:

- `ORANGE_PARK_CONTACT_FLOW_VERSION = "orange_park_v2"`;
- deterministic `/start`;
- deterministic consultant replies for purchase terms and one-room apartments;
- history-guessed numeric apartment-area fallback;
- budget/current-options guard;
- manual-phone rejection and native Telegram contact request;
- AI reply text scanning to infer whether the contact button is needed;
- old v2 contact/start/apartment metadata handlers;
- general AI orchestration and PromptBuilder fallback for all non-intercepted
  Orange Park messages;
- platform `LegacyWebhookFlow` compatibility path.

The active database still contains exactly three active old knowledge rows:

| Title | Type | Active |
|---|---|---|
| `Orange Park FAQ` | `faq` | yes |
| `Orange Park Prices And Availability - Manager Confirmed Only` | `pricing` | yes |
| `Orange Park Conversation Style Guide` | `conversation_style` | yes |

No six v3 knowledge rows are present. There are no disabled Orange Park
knowledge rows in the queried database; the old rows were never deactivated in
this active database.

The active tenant profiles are also old:

- profile name: `Orange Park Telegram MVP`;
- stage: `telegram_only_mvp`;
- business profile points to
  `01_business_profile_facts/orange_park_facts.md`;
- AI profile points to
  `05_policies_and_rules/orange_park_ai_policies.md`;
- AI policy metadata still says `No Bitrix24 or external CRM behavior`;
- channel metadata has no `dialog_engine_version=orange_park_v3`.

### Worktree compatibility and residual code

The v3 worktree still retains:

- `LegacyWebhookFlow` and the raw-SQL legacy webhook processing branch;
- `_LegacyMessageHistoryService` and legacy message/conversation persistence
  helpers;
- `_resolve_reply_to_customer_legacy()`, which still invokes shared AI
  orchestration and accepts `operator_business_context`;
- three Bitrix enablement metadata shapes:
  `crm.bitrix.enabled`, `integrations.bitrix.enabled`, and `bitrix_enabled`;
- the old-named contact stage value
  `orange_park_telegram_native_contact`;
- deterministic output persisted through `save_outgoing_ai_message()`, so
  deterministic replies are still represented as AI messages;
- old v2 metadata in existing database messages. Worktree v3 ignores it by
  requiring the exact v3 version.

The legacy flow is currently unreachable in the active database because the
`flows` table exists and Orange Park has an active default flow. It becomes
reachable only if the table is absent or the missing-table compatibility error
is triggered.

## C. Safe to Remove

Safe only after the v3 backend, seed, and n8n export are deployed and verified
together:

- old deleted documentation directories:
  `01_business_profile_facts`, `02_ai_behavior_and_sales_materials`, `03_faq`,
  `04_prices_and_availability`, `05_policies_and_rules`, `06_promotions`, and
  `07_conversation_examples`;
- old Orange Park-specific v2 metadata readers/writers;
- old consultant, history-area, budget/current-options, and AI-text-scanning
  handlers already removed in the worktree;
- stale n8n `operator_business_context` overlay;
- historical Orange Park task files after they are moved to a clearly marked
  archive/done location;
- empty `.gitkeep` placeholders in `08_bitrix24_mapping`, `09_telegram_bot`,
  `10_tests`, and `generated` if those directories are not required by project
  policy.

Do not delete old DB rows before the v3 seed has created all six replacements
and runtime verification confirms the new configuration.

## D. Requires Migration or Controlled Cutover

These are not safe as file-only cleanup:

1. Rebuild/redeploy backend so the active image contains the v3 dialog service
   and v3 webhook routing.
2. Apply the v3 seed to the intended active database. It must create/update the
   six canonical rows and deactivate the three old rows.
3. Import and activate the cleaned n8n export; verify active/export parity.
4. Verify active AI/business/channel profiles carry
   `dialog_engine_version=orange_park_v3`.
5. Decide whether old PromptRun and message metadata are retained for audit or
   archived under a retention policy. They must not be treated as current
   configuration.
6. Remove the platform `LegacyWebhookFlow` only under a separate platform-wide
   migration, because it is not Orange Park-specific.

## E. High-Risk Removals

- Removing the old active knowledge rows before applying the v3 seed would
  leave the currently deployed AI path without Orange Park knowledge.
- Removing PromptBuilder/AI configuration because v3 bypasses it would break
  the `LegacyWebhookFlow` branch and other tenants.
- Removing all old message metadata can damage auditability, duplicate replay,
  and historical contact diagnostics.
- Removing Bitrix compatibility metadata shapes can disable CRM sync for flows
  using an older metadata layout.
- Removing n8n contact-button shaping before backend/export parity is proven can
  make the native contact request invisible to users.
- Deploying only migration `0027` without the matching dialog/seed/n8n changes
  reproduces the current split-brain state.

## F. Documentation Classification and Cleanup Plan

### Current filesystem

| File | Classification | Runtime use |
|---|---|---|
| `README.md` | ACTIVE V3 | Index only; not injected |
| `01_business_profile/orange_park_business_profile.md` | ACTIVE V3 | v3 seed business profile + knowledge |
| `02_sales_presentation/orange_park_sales_presentation.md` | ACTIVE V3 | v3 knowledge |
| `03_sales_scenarios/orange_park_sales_scenarios.md` | ACTIVE V3 | v3 AI profile + knowledge |
| `04_purchase_rules/orange_park_purchase_rules.md` | ACTIVE V3 | v3 knowledge |
| `05_apartment_catalog/orange_park_apartment_catalog.md` | ACTIVE V3 | v3 knowledge extension point |
| `06_commercial_catalog/orange_park_commercial_catalog.md` | ACTIVE V3 | v3 knowledge extension point |
| `00_intake/orange-park-client-source.pdf` | UNUSED runtime | Original input/archive source |
| `.env` | UNUSED documentation | Local secret-bearing file; do not archive publicly |
| `00_intake/.gitkeep` | UNUSED | Directory placeholder |
| `08_bitrix24_mapping/.gitkeep` | UNUSED | Directory placeholder |
| `09_telegram_bot/.gitkeep` | UNUSED | Directory placeholder |
| `10_tests/.gitkeep` | UNUSED | Directory placeholder |
| `generated/.gitkeep` | UNUSED | Directory placeholder |

### Deleted from worktree but still present in `HEAD`

| File | Classification |
|---|---|
| `01_business_profile_facts/orange_park_facts.md` | LEGACY, ARCHIVE CANDIDATE |
| `02_ai_behavior_and_sales_materials/orange_park_sales_materials.md` | LEGACY, ARCHIVE CANDIDATE |
| `03_faq/orange_park_faq.md` | LEGACY, ARCHIVE CANDIDATE |
| `04_prices_and_availability/orange_park_prices_and_availability.md` | LEGACY, ARCHIVE CANDIDATE |
| `05_policies_and_rules/orange_park_ai_policies.md` | LEGACY, ARCHIVE CANDIDATE |
| `07_conversation_examples/orange_park_conversation_style_guide.md` | LEGACY, ARCHIVE CANDIDATE |
| `07_conversation_examples/orange_park_manager_chats_transcript.md` | ARCHIVE CANDIDATE, UNUSED runtime |

The deleted legacy files are still indirectly active because their content
remains in PostgreSQL profiles and knowledge rows. Deleting repository files
does not remove injected runtime content.

Cleanup order:

1. Deploy v3 backend.
2. Apply/verify v3 seed.
3. Import/verify n8n v3 export.
4. Confirm six active rows and three disabled old rows.
5. Confirm no new Orange Park PromptRun is created by standard Telegram flow.
6. Archive historical task/audit documents.
7. Finalize deletion of old source documents.

## Seed and Knowledge Audit

The worktree seed is tenant/business scoped and defines exactly six canonical
titles:

```text
01_business_profile
02_sales_presentation
03_sales_scenarios
04_purchase_rules
05_apartment_catalog
06_commercial_catalog
```

It deactivates every other active Orange Park knowledge title.

Duplicated v3 source material:

- `01_business_profile` is written both to
  `TenantBusinessProfile.business_description` and a knowledge row.
- `03_sales_scenarios` is written both to
  `TenantAiProfile.metadata.behavior_instructions` and a knowledge row.
- `AI_POLICIES_PATH` is a misleading compatibility name; it points to the same
  `03_sales_scenarios` file as `SALES_SCENARIOS_PATH`.

This duplication does not affect the standard worktree v3 path because it does
not build a prompt. It does affect the legacy AI fallback and would duplicate
similar content across prompt sections.

## Prompt Construction Audit

### Active deployed v2 runtime

The latest active Orange Park PromptRuns were created on
`2026-06-14 21:57:49` and the database contains 129 Orange Park PromptRuns.

| Prompt item | Status | Evidence |
|---|---|---|
| `BUSINESS CONTEXT SOURCE OF TRUTH` | ACTIVE | Present in latest PromptRuns |
| `TENANT BUSINESS CONTEXT` | ACTIVE | Present in latest PromptRuns |
| `TENANT AI BEHAVIOR` | ACTIVE | Present in latest PromptRuns |
| `RELEVANT KNOWLEDGE` | ACTIVE | Present in latest PromptRuns |
| old FAQ | ACTIVE | `Orange Park FAQ` present in latest PromptRuns |
| old conversation style | ACTIVE | Present in four of latest five sampled PromptRuns |
| old AI policies | ACTIVE | Present in latest PromptRuns/profile metadata |
| legacy operator context | INACTIVE in Orange Park prompt, ACTIVE in transport | Active n8n sends it; deployed backend deliberately strips it before PromptBuilder |

PromptBuilder places operator notes inside `TENANT BUSINESS CONTEXT`, not in a
separate canonical section. The deployed Orange Park helper returns `None` for
that overlay, so the contradictory `No Bitrix24` string is transported and
observed but not inserted into the Orange Park prompt.

### Worktree v3 standard path

All listed prompt items are **INACTIVE** for a normal Orange Park Telegram
message. `_resolve_orange_park_v3_reply()` returns before common AI
orchestration, knowledge retrieval, language detection, PromptBuilder,
PromptRun creation, and model gateway execution.

They are **PARTIALLY ACTIVE** at repository level because
`_resolve_reply_to_customer_legacy()` still invokes the common AI path if
`LegacyWebhookFlow` is selected.

## Dialog Engine Audit

### Expected conceptual routes

The requested diagram is a set of sibling routes, not a sequential chain:

```text
START
  +-> about_project
  +-> apartment_sales
  +-> commercial_sales
  +-> purchase_terms
  `-> manager_contact
```

### Active deployed v2 flow

```text
Telegram message
  -> /start? ----------------------> deterministic welcome/reset
  -> purchase/one-room marker? ----> deterministic consultant reply
  -> short numeric + inferred
     recent area context? ---------> deterministic area fallback
  -> phone/manager/price/
     availability/budget marker? --> deterministic contact request
  -> otherwise
       -> AI configuration
       -> old knowledge retrieval
       -> language/greeting policy
       -> PromptBuilder
       -> model gateway
       -> optional AI-text contact scan
```

This is not a dialog engine with explicit scenario state. Numeric context is
guessed from recent messages and most topics are probabilistic AI responses.

### Worktree v3 real state flow

```text
/start -> idle

about_project
  -> qualification
  -> no qualification-stage handler
  -> next unmatched answer falls back to idle

apartment_sales
  -> apartment_type
  -> apartment_area
  -> apartment_purpose
  -> purchase_path
  -> no generic purchase_path handler
  -> installment/eOselya keywords -> manager_offer
  -> short confirmation -> awaiting_contact
  -> Telegram contact -> completed

commercial_sales
  -> commercial_business_type
  -> commercial_format
  -> commercial_purpose
  -> manager_offer
  -> short confirmation -> awaiting_contact
  -> Telegram contact -> completed

purchase_terms
  -> purchase_path
  -> installment/eOselya keywords -> manager_offer
  -> other answers have no stage-specific handler

manager/price/availability/viewing/budget/manual phone
  -> awaiting_contact immediately
  -> Telegram contact -> completed
```

Differences and defects:

- `qualification` is written but never consumed.
- `purchase_path` is written but has no generic state handler.
- only one-room apartments receive a typed path; 2-room and 3-room markers
  route to a generic apartment-type question.
- all deterministic replies are Ukrainian; common language detection is
  bypassed.
- hardcoded budget markers include only three exact numbers in addition to the
  generic `бюджет` marker.
- generic price, viewing, and availability markers bypass qualification and
  request contact immediately.
- about-project transport wording leaks the internal phrase
  `в матеріалах комплексу`.
- output is saved as an AI message even though no AI runs.

## Bitrix Audit

### Active runtime

Bitrix is configured and active:

- flow metadata: `crm.bitrix.enabled=true`;
- backend setting is non-empty;
- timeout: 10 seconds;
- 5 Orange Park messages contain `bitrix_lead_id`;
- latest recorded sync: `2026-06-13 12:15:09`;
- 11 messages contain `contact_received`.

Implemented flow:

```text
native Telegram contact
  -> normalize phone
  -> crm.duplicate.findbycomm(entity=LEAD, type=PHONE)
  -> existing phone: crm.lead.update
  -> new phone: crm.lead.add
```

Lead payload:

- contact button: native Telegram `request_contact`;
- Telegram payload carries first name, last name, phone, Telegram ID, username;
- phone deduplication: yes;
- create/update: yes;
- conversation summary: full bounded conversation plus latest five customer
  messages;
- `SOURCE_ID`: `OTHER`;
- `SOURCE_DESCRIPTION`: `Telegram / Orange Park Telegram Bot`;
- comments explicitly contain `Source: Telegram`.

Old/residual behavior:

- active n8n note and operator overlay still say `No Bitrix24`;
- active AI profile also says no external CRM behavior;
- old v2 contact metadata is still the trigger format in deployed runtime;
- Bitrix failures are caught in the worktree v3 webhook so the customer reply
  continues, but there is no durable retry queue in this scope;
- three flow metadata layouts are accepted for compatibility.

## n8n Audit

### Active n8n workflow

Workflow `orange-park-telegram-mvp`, ID `LOVCcKZ1YAMnBIFg`, is active.
Its active version was last updated `2026-06-12 13:36:51`.

Active route:

```text
Telegram Trigger
  -> Normalize Telegram Message
  -> POST Backend
  -> Shape Telegram Reply
  -> Telegram Send Message
```

Findings:

- no obsolete branches;
- no n8n-owned CRM branch;
- native contact payload normalization is active;
- contact keyboard shaping is active;
- legacy prompt overlay is still present in `operator_business_context`;
- POST body still sends that overlay;
- overlay says `Orange Park Telegram-only MVP. No Bitrix24...`;
- node notes still describe no CRM/Bitrix behavior;
- no v3 dialog metadata is produced by n8n, correctly leaving state to backend.

### Repository export

The worktree export removes `operator_business_context`, sends only normalized
business/channel/customer/message fields, and states that dialog v3 and Bitrix
sync are backend-owned. It has not been imported into the active n8n instance.

## Legacy Search Inventory

Search scope: entire repository, hidden files included, `.git` and PDFs
excluded, case-insensitive. The audit file itself was excluded.

| Term | Occurrences | Files | Orange Park runtime relevance |
|---|---:|---:|---|
| `orange_park_v1` | 1 | 1 | historical task only |
| `orange_park_v2` | 5 | 3 | historical files in worktree; active container still has it |
| `legacy` | 367 | 96 | 46 worktree runtime/test occurrences in flow/webhook area; most others platform/docs |
| `contact_flow_version` | 5 | 3 | historical worktree docs; active container still writes/reads it |
| `operator_business_context` | 293 | 74 | platform feature; active Orange n8n still sends it |
| `manual contact form` | 3 | 3 | historical task docs |
| `Ім'я:` | 8 | 3 | historical task docs |
| `Прізвище:` | 8 | 3 | historical task docs |
| `Телефон:` | 12 | 4 | historical docs plus one negative test assertion |
| `Orange Park FAQ` | 3 | 1 | historical task text; also active DB/runtime prompt |
| `Conversation Style Guide` | 6 | 2 | historical task text; also active DB/runtime prompt |
| `AI Policies` | 8 | 2 | historical task text; also active DB/runtime profile/prompt |
| `deterministic` | 160 | 70 | broad platform term; 60 Orange Park task/service occurrences |
| `consultant-first` | 2 | 2 | historical/in-progress task docs |
| `budget guard` | 0 | 0 | no exact phrase |
| `area fallback` | 3 | 3 | historical task docs |

Exact Orange-specific occurrence locations:

- `orange_park_v1`:
  `tasks/in-progress/T-orange-park-v3-legacy-cleanup.md:103`
- `orange_park_v2`:
  `T-orange-park-v3-legacy-cleanup.md:104`,
  `T-orange-park-response-scenario-audit.md:186`,
  `T-orange-park-contact-flow-and-metadata-diagnostics.md:247,279,310`
- `contact_flow_version`: the same three task files at
  `T-orange-park-v3-legacy-cleanup.md:107`,
  `T-orange-park-response-scenario-audit.md:186`, and
  `T-orange-park-contact-flow-and-metadata-diagnostics.md:247,279,310`
- `manual contact form`:
  `T-orange-park-full-configuration-trace.md`,
  `T-orange-park-telegram-contact-button-only.md`,
  `T-orange-park-v3-legacy-cleanup.md`
- manual field labels:
  `T-orange-park-budget-contact-guard.md`,
  `T-orange-park-full-configuration-trace.md`,
  `T-orange-park-v3-legacy-cleanup.md`, plus the negative assertion in
  `backend/tests/test_webhook_message_service.py:617`
- old FAQ/style/policies:
  `T-orange-park-full-configuration-trace.md`,
  `T-orange-park-customer-facing-wording.md`, and
  `T-orange-park-response-scenario-audit.md`
- `consultant-first`:
  `T-orange-park-consultant-first-behavior.md:1` and
  `T-orange-park-contact-flow-and-metadata-diagnostics.md:178`
- `area fallback`:
  `T-orange-park-v3-legacy-cleanup.md:36`,
  `T-orange-park-response-scenario-audit.md:30`,
  `T-orange-park-customer-facing-wording.md:28`

For broad platform terms, the complete file/count index was captured during the
audit. Runtime occurrences are concentrated in:

- `backend/app/services/flow_service.py`: 15 `legacy` occurrences;
- `backend/app/services/webhook_message_service.py`: 31 `legacy` and 7
  `operator_business_context` occurrences;
- PromptBuilder/orchestration/schema files: 41 active
  `operator_business_context` occurrences;
- Orange Park tests: legacy fallback, old metadata rejection, and v3 behavior
  coverage.

The broad terms `legacy`, `operator_business_context`, and `deterministic` are
platform concepts and must not be globally deleted as Orange Park cleanup.

## Duplicated Logic and Unreachable Code

Duplicated or overlapping:

- v3 stable facts exist in deterministic Python replies and v3 documents.
- business profile and sales scenarios are each seeded twice into different
  prompt sources.
- Bitrix enablement accepts three metadata layouts.
- normal and legacy webhook branches duplicate persistence/orchestration work.
- start greeting exists in dialog service and channel metadata.
- Telegram contact request is represented by nested metadata plus flat response
  aliases.

Unreachable or conditionally unreachable:

- common AI orchestration is unreachable for standard Orange Park Telegram in
  the worktree v3 path.
- v3 dialog service is unreachable in the active deployed container because the
  file/import is absent.
- legacy webhook branch is unreachable under the current DB because `flows`
  exists and an active default flow resolves.
- `qualification` and generic `purchase_path` state transitions have no
  consuming handlers; their intended continuations are effectively absent.
- v3 knowledge and PromptBuilder configuration do not influence standard v3
  replies, because all responses are hardcoded before retrieval.

## File List

Primary runtime files inspected:

- `backend/app/services/webhook_message_service.py`
- active container `/app/app/services/webhook_message_service.py`
- `backend/app/services/orange_park_dialog_service.py`
- `backend/app/services/orange_park_bitrix_service.py`
- `backend/app/services/message_service.py`
- `backend/app/services/flow_service.py`
- `backend/app/services/prompt_builder_service.py`
- `backend/app/services/ai_reply_orchestration_service.py`
- `backend/app/services/ai_reply_orchestration_coordinator.py`
- `backend/app/services/ai_configuration_service.py`
- `backend/app/services/customer_language_detection.py`
- `backend/app/seed/orange_park_configuration.py`
- `backend/scripts/seed_orange_park_configuration.py`
- `backend/alembic/versions/0027_enable_orange_park_bitrix_leads.py`
- `backend/app/core/config.py`
- `n8n/workflows/orange-park-telegram-mvp.json`
- active n8n workflow export for ID `LOVCcKZ1YAMnBIFg`

Documentation inspected:

- every file under `docs/businesses/orange-park`;
- deleted Orange Park files from git `HEAD`;
- Orange Park in-progress audit/implementation task documents;
- relevant architecture and prompt specs.

Database inspected:

- `businesses`
- `flows`
- `tenant_business_profiles`
- `tenant_ai_profiles`
- `tenant_channel_settings`
- `tenant_knowledge_sources`
- `prompt_runs`
- Orange Park message metadata

## G. Estimated Completion

These percentages distinguish code written from behavior actually serving
users:

```text
Dialog Engine v3 implementation in worktree: 78%
Dialog Engine v3 deployed runtime:          0%
v3 database/knowledge cutover:              0%
v3 n8n cutover:                             0%
Bitrix contact integration:                85%
Legacy removed from worktree code:         75%
Legacy removed from active runtime:        20%
Legacy remaining in active runtime:        80%
Overall v3 production completion:          35%
```

The worktree score is below 100% because of missing state consumers, Ukrainian-
only behavior, hardcoded/document duplication, and absent end-to-end deployment
verification. The production score is lower because the active backend,
database, and n8n workflow are not on the same version.

## Final Runtime Architecture Diagram

### What is serving now

```text
Telegram
  |
  v
active n8n v4
  - normalizes text/contact
  - injects obsolete "No Bitrix24" operator context
  - sends native contact keyboard from backend metadata
  |
  v
active backend: Orange Park v2 + Bitrix
  |
  +-> old deterministic start/consultant/area/budget/contact handlers
  |
  +-> shared AI orchestration
  |     -> old TenantBusinessProfile
  |     -> old TenantAIProfile / AI Policies
  |     -> old FAQ/pricing/style knowledge
  |     -> PromptBuilder
  |     -> model gateway
  |
  `-> native Telegram contact
        -> phone duplicate lookup
        -> Bitrix lead create/update
        -> conversation summary
```

### What the worktree intends after coordinated cutover

```text
Telegram
  |
  v
clean n8n transport only
  |
  v
backend normal Flow
  |
  +-> Telegram contact -> Bitrix create/update
  |
  `-> OrangeParkDialogService v3
        -> explicit metadata state
        -> deterministic response
        -> optional contact request
        -> no retrieval, PromptBuilder, PromptRun, or model call

LegacyWebhookFlow only
  -> shared AI orchestration and prompt stack
```

## Git Status at Audit Completion

Branch:

```text
stabilization/runtime-baseline...origin/stabilization/runtime-baseline
```

The worktree was already dirty before this audit. It contains modified backend,
seed, tests, compose, n8n, and task files; deleted old Orange Park documents;
and untracked v3 service, Bitrix, migration, tests, six documentation
directories, and task files.

This audit added only:

```text
?? tasks/in-progress/T-orange-park-v3-runtime-audit.md
```

No commit was created.
