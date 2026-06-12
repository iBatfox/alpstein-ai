# T-orange-park-clean-configuration

## Goal

Eliminate legacy Orange Park AI/contact behavior and rebuild one clean configuration chain from source documents through seed, PostgreSQL, Prompt Builder, and AI.

## Scope

- Audit which Orange Park configuration fields reach Prompt Builder.
- Keep business facts in `TenantBusinessProfile`.
- Keep AI behavior in `TenantAIProfile`.
- Keep conversation examples in `TenantKnowledgeSource`.
- Remove obsolete manual phone/contact forms and duplicate behavior.
- Preserve the Orange Park native Telegram contact-button state machine.
- Run the Orange Park seed and validate active PostgreSQL rows.

## Requirements

- Native Telegram contact sharing is the only phone collection method.
- Manually typed phone numbers do not count as shared Telegram contact.
- Ask only for name fields missing from the Telegram contact payload.
- Final reply: `Дякуємо. Запит передано менеджеру. Очікуйте дзвінок.`
- Do not modify other businesses.
- No Bitrix, Mini App, or n8n architecture changes.
- No commit or push.

## Validation

- Focused and relevant backend tests pass.
- Active Orange Park DB contains required native-contact rules.
- Active Orange Park DB contains none of the listed obsolete phrases.
- Final report includes files changed, DB changes, removed rules, remaining active sources, tests, and git status.

## Out Of Scope

- Changes to non-Orange Park tenant configuration.
- Bitrix integration.
- Telegram Mini App.
- n8n architecture redesign.

## Final Validation Report

Validation date: 2026-06-12

### 1. Runtime Audit

| Rule source | Status | Runtime behavior |
| --- | --- | --- |
| `TenantBusinessProfile.business_description` | ACTIVE | Loaded by `AiConfigurationService` and emitted in Prompt Builder's tenant business context. Contains factual business data only. |
| `TenantBusinessProfile.business_limitations` | ACTIVE | Loaded and emitted in tenant business context. Contains unavailable/unstable fact categories only. |
| `TenantAIProfile.metadata.behavior_instructions` | ACTIVE | Explicitly mapped by Prompt Builder into tenant behavior. This is the sole normative Orange Park AI behavior document. |
| `TenantAIProfile.metadata.behavior_rules` | OBSOLETE / REMOVED | The old DB array was replaced. Prompt Builder does not consume this legacy key. |
| `TenantAIProfile.ask_for_name` | OBSOLETE / REMOVED | Set to `NULL`; no generic name-collection flag reaches the prompt. |
| `TenantAIProfile.ask_for_phone` | OBSOLETE / REMOVED | Set to `NULL`; no generic phone-collection flag reaches the prompt. |
| `TenantAIProfile.forbidden_promises` | ACTIVE | Emitted in tenant behavior. Reduced to unsupported business promises, not conversation-flow rules. |
| `TenantKnowledgeSource.conversation_style` | ACTIVE WHEN RETRIEVED | Contains examples only. It no longer contains a generated runtime summary or a duplicate contact flow. |
| `TenantKnowledgeSource.faq` | ACTIVE WHEN RETRIEVED | Contains FAQ facts and manager-confirmation boundaries, without manual contact collection. |
| `TenantKnowledgeSource.pricing` | ACTIVE WHEN RETRIEVED | Contains documented pricing facts and time-sensitivity, without manual contact collection. |
| `TenantChannelSettings` | ACTIVE | Telegram response limits and greeting only. It does not contain contact-flow rules. |
| Orange Park webhook contact state machine | ACTIVE | Handles the native contact button, rejects manually typed phone as contact completion, asks only for missing Telegram name fields, and sends the final handoff reply. |
| Sales materials document | UNUSED BY RUNTIME | Retained as positioning/reference material but removed from seed mapping and active prompt configuration. |
| Old generated conversation-style runtime summary | OBSOLETE / REMOVED | Generator and generated duplicate behavior were deleted. |

No active rule remains classified as `DUPLICATED`. The policy defines behavior; the webhook implements the transport-specific state transition.

### 2. Clean Configuration Chain

```text
docs/businesses/orange-park/05_policies_and_rules/orange_park_ai_policies.md
  -> orange_park_configuration.py
  -> TenantAIProfile.metadata.behavior_instructions
  -> AiConfigurationService._map_ai_profile
  -> PromptBuilderService._build_tenant_behavior
  -> AI tenant_behavior prompt section
```

```text
docs/businesses/orange-park/01_business_profile_facts/orange_park_facts.md
  -> orange_park_configuration.py
  -> TenantBusinessProfile.business_description
  -> AiConfigurationService._map_business_profile
  -> Prompt Builder tenant_business_context
  -> AI
```

```text
FAQ / pricing / conversation examples
  -> orange_park_configuration.py
  -> TenantKnowledgeSource
  -> tenant-scoped knowledge retrieval
  -> Prompt Builder knowledge section
  -> AI
```

### 3. Removed Obsolete Rules

Removed from source documents, seed mappings, active profile fields, knowledge content, and generated summaries:

- Manual Ukrainian and Russian contact forms.
- Instructions to type or leave a phone number.
- `If phone is missing`.
- `If phone is already provided`.
- `ask only for phone`.
- `ask only for first and last name`.
- `Напишіть, будь ласка, номер телефону`.
- `Залиште, будь ласка, ваш номер телефону`.
- Duplicate contact completion and manager-handoff rules.
- Generic `ask_for_name` and `ask_for_phone` prompt flags.

### 4. Remaining Active Contact Rules

The normative policy and assembled prompt contain each required rule once:

- `Для зв'язку з менеджером, будь ласка, натисніть кнопку «📱 Поділитися номером».`
- `Use native Telegram contact sharing.`
- `Do not ask customer to type phone manually.`
- A manually typed phone number results in another request to use the Telegram contact button.
- Telegram `first_name` and `last_name` are reused; only absent name fields are requested.
- `Дякуємо. Запит передано менеджеру. Очікуйте дзвінок.`

### 5. Database Changes

The Orange Park seed was run and committed successfully for:

- Tenant ID: `45bc74ec-7481-4369-a2c8-b2b9933e23d9`
- Business ID: `fc001d9d-b5b1-4260-ba15-d28b30964b56`
- One `TenantBusinessProfile`
- One `TenantAIProfile`
- One Telegram `TenantChannelSetting`
- Three active knowledge sources: `faq`, `pricing`, `conversation_style`

The AI profile now has `behavior_instructions`, no `behavior_rules`, and `ask_for_name` / `ask_for_phone` are `NULL`.

Pre-seed and post-seed hashes were identical for every non-Orange tenant, business, business profile, AI profile, knowledge source, and channel setting. No other business configuration changed.

### 6. Active DB and Prompt Proof

Active DB search returned zero matches for all eight prohibited phrases:

- `Будь ласка, залиште дані у такому форматі`
- `Пожалуйста, оставьте данные`
- `If phone is missing`
- `If phone is already provided`
- `ask only for phone`
- `ask only for first and last name`
- `Напишіть, будь ласка, номер телефону`
- `Залиште, будь ласка, ваш номер телефону`

The assembled `customer_reply_v1` prompt also returned zero prohibited matches. Each required native-contact phrase appeared exactly once. The prompt does not contain `ask_for_name` or `ask_for_phone`.

### 7. Files Changed For This Configuration

- `backend/app/seed/orange_park_configuration.py`
- `backend/app/services/prompt_builder_service.py`
- `backend/app/services/webhook_message_service.py`
- `backend/tests/test_orange_park_configuration_seed.py`
- `backend/tests/test_prompt_builder_service.py`
- `backend/tests/test_webhook_message_service.py`
- `docs/businesses/orange-park/01_business_profile_facts/orange_park_facts.md`
- `docs/businesses/orange-park/02_ai_behavior_and_sales_materials/orange_park_sales_materials.md`
- `docs/businesses/orange-park/03_faq/orange_park_faq.md`
- `docs/businesses/orange-park/04_prices_and_availability/orange_park_prices_and_availability.md`
- `docs/businesses/orange-park/05_policies_and_rules/orange_park_ai_policies.md`
- `docs/businesses/orange-park/07_conversation_examples/orange_park_conversation_style_guide.md`
- `tasks/in-progress/T-orange-park-clean-configuration.md`

The already-modified `n8n/workflows/orange-park-telegram-mvp.json` was not changed as part of this cleanup. No Bitrix or Mini App files were changed.

### 8. Test Results

- Full backend suite: `779 passed, 4 skipped`.
- Final focused Orange Park/configuration suite: `45 passed, 5 deselected`.
- Seed dry-run: successful and rolled back.
- Final Orange Park seed: successful and committed.
- `git diff --check`: passed.
- Runtime prompt validation: zero obsolete matches; required phrase counts `[1, 1, 1, 1]`.
- Non-Orange DB fingerprint comparison: unchanged.

### 9. Git Status

The worktree remains intentionally uncommitted. Modified tracked files include the Orange Park configuration files listed above plus a pre-existing n8n workflow modification. Existing unrelated untracked documentation/task files remain present and untouched.

No commit or push was performed.
