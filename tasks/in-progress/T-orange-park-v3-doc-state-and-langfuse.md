# Orange Park v3 Documentation: State and Langfuse

## Goal

Define explicit Orange Park Dialog Engine v3 state consumption in the six
active documentation sources and document its platform observability boundary.

## Scope

- Active Orange Park v3 business documentation only.
- No runtime code, n8n, Bitrix, migration, commit, or push changes.
- No restoration or editing of legacy Orange Park source documents.

## Changes

### Files Changed

- `docs/businesses/orange-park/03_sales_scenarios/orange_park_sales_scenarios.md`
- `docs/businesses/orange-park/04_purchase_rules/orange_park_purchase_rules.md`
- `docs/businesses/orange-park/05_apartment_catalog/orange_park_apartment_catalog.md`
- `docs/businesses/orange-park/README.md`
- `tasks/in-progress/T-orange-park-v3-doc-state-and-langfuse.md`

### State Rules Added

- Added the v3 root intent map and explicit state-field contract.
- Defined stage-first consumption and preservation of unrelated valid fields.
- Added apartment type mappings for 1-, 2-, 3-, and 4-room replies.
- Added living and investment purpose mappings.
- Added numeric area consumption only during an active area stage.
- Added the non-live 2-room reference range of `56-64 м²`.
- Added commercial qualification and unknown/idle fallback rules.
- Explicitly prohibited stale-history state inference.

### Purchase Path Rules Added

- Added mappings for full payment, installment, єОселя, financing, and voucher.
- Required general explanations without current-term promises.
- Added `manager_offer` transition and agreement-based contact handoff.

### Manager Contact Rules Added

- Limited native contact requests to direct manager requests, active manager
  offer agreement, current price/availability/calculation/viewing needs, or
  sufficiently qualified sales context.
- Prohibited idle `так`, `ок`, `давай`, and `+` from triggering contact.
- Defined `contact_requested`, `contact_received`, `awaiting_contact`, and
  `completed` transitions.

### Observability Rule Added

- Documented the platform request-to-response message-trace lifecycle for
  deterministic, AI, contact, CRM-success, and CRM-failure paths across all
  channels.
- Kept Langfuse wording aligned with canonical platform specs: Langfuse is a
  supplementary sink when enabled, and production/staging activation remains
  conditional on the environment flag and configured keys.
- Documented that PromptRun and Langfuse are separate and that deterministic
  paths must not create PromptRuns solely for tracing.

## Source-of-Truth Note

This task changes documentation sources only. The deterministic Orange Park v3
service does not dynamically interpret these documents for state transitions,
so documentation changes alone do not alter deployed runtime behavior.

The requested statement that Langfuse is unconditionally mandatory for every
message conflicts with the approved platform production policy in
`specs/architecture/observability-metadata.md` section 16.6 and
`docs/architecture/canonical-runtime-architecture.md`. The updated documents
therefore require the platform message-trace lifecycle for every turn and
require Langfuse coverage when Langfuse is enabled.

## Validation

- Task-scope status contains only:
  - the Orange Park v3 README;
  - `03_sales_scenarios`;
  - `04_purchase_rules`;
  - `05_apartment_catalog`;
  - this report.
- The legacy Orange Park source directories were not edited or restored.
  Their deletions shown by Git are pre-existing cleanup changes.
- Active-source legacy grep found only the README statement that old FAQ,
  pricing, AI-policy, contact-form, and conversation-style sources are not
  runtime sources.
- Orange Park seed dry-run against the active backend database: passed and
  rolled back. No normal seed was run.
- `git diff --check`: passed.
- No runtime code, n8n workflow, Bitrix integration, or migration was changed
  by this task.

## Git Status

The shared worktree remains dirty from the broader Orange Park v3 cutover and
other pre-existing work:

- 18 modified tracked files;
- 14 deleted legacy documentation files;
- 22 untracked files/directories;
- 54 total status entries.

Within this task, Git reports the four documentation paths and this report
listed above. No commit or push was performed.
