# T-orange-park-business-docs-isolation-plan

## Goal

Analyze the current Alpstein AI backend business/document structure and define an isolated per-business documentation layout for the first real client project: Orange Park / ЖК Orange Park.

No runtime behavior, n8n workflow, Mini App, ingestion logic, commit, or push is part of this task.

## Current Findings

- Business identity enters runtime through the normalized webhook `business_id` string, which resolves to `businesses.external_id`.
- After business resolution, backend uses internal `businesses.id` plus `businesses.tenant_id`.
- Production isolation boundary is `tenant_id + business_id`.
- Production factual business context lives in `TenantBusinessProfile`.
- AI behavior and style live in `TenantAIProfile`.
- Channel behavior lives in `TenantChannelSetting`.
- FAQ, pricing details, policies, promotions, static availability notes, and long-form knowledge live in `TenantKnowledgeSource`.
- Platform prompts live in `PromptTemplate` and must not contain Orange Park-specific facts.
- `operator_business_context` is a short top-level webhook overlay appended by Prompt Builder; it is not the canonical production store.
- There is no MVP file upload/document ingestion API.
- Production AI configuration and knowledge are PostgreSQL-backed.
- Existing Mini App interview documents are filesystem-backed under `docs/interview/{alpstein_business_id}`, but that is separate draft/interview output and not the production Knowledge Retrieval path.

## Existing Relevant Files, Classes, And Services

Models:

- `backend/app/models/business.py`
- `backend/app/models/tenant.py`
- `backend/app/models/tenant_business_profile.py`
- `backend/app/models/tenant_ai_profile.py`
- `backend/app/models/tenant_knowledge_source.py`
- `backend/app/models/tenant_channel_setting.py`
- `backend/app/models/prompt_template.py`
- `backend/app/models/prompt_run.py`
- `backend/app/models/business_context_builder.py`

Services:

- `backend/app/services/business_service.py`
- `backend/app/services/ai_configuration_service.py`
- `backend/app/services/tenant_business_profile_service.py`
- `backend/app/services/tenant_ai_profile_service.py`
- `backend/app/services/tenant_knowledge_source_service.py`
- `backend/app/services/knowledge_retrieval_service.py`
- `backend/app/services/prompt_builder_service.py`
- `backend/app/services/business_context_builder_service.py`
- `backend/app/services/telegram_mini_app_interview_service.py`

Specs:

- `specs/architecture/ai-configuration-architecture.md`
- `specs/architecture/prompt-builder-rules.md`
- `specs/api/webhooks.md`
- `specs/database/entities.md`
- `specs/database/database-schema.md`

## Recommended Per-Business Documentation Structure

Use a per-business pre-ingestion folder keyed by the same external business identity used by integrations:

```text
docs/businesses/orange-park/
  README.md
  00_intake/
  01_business_profile_facts/
  02_ai_behavior_and_sales_materials/
  03_faq/
  04_prices_and_availability/
  05_policies_and_rules/
  06_promotions/
  07_conversation_examples/
  08_bitrix24_mapping/
  09_telegram_bot/
  10_tests/
  generated/
```

Use `01_business_profile_facts/` rather than `01_operator_business_context/` because `operator_business_context` already has a specific runtime meaning: a short per-request webhook overlay from n8n, not the canonical factual store.

## Mapping To Existing Backend Cells

### TenantBusinessProfile

Use for stable factual business data:

- business description;
- project/location facts;
- services;
- stable pricing summary;
- working hours;
- city, region, country;
- business limitations.

Source folders:

- `01_business_profile_facts/`
- stable summaries from `04_prices_and_availability/`
- stable limitations from `05_policies_and_rules/`

### TenantAIProfile

Use for assistant behavior and sales style:

- tone;
- language;
- response style;
- lead qualification questions;
- handoff rules;
- forbidden promises;
- fallback behavior.

Source folders:

- `02_ai_behavior_and_sales_materials/`
- selected patterns from `07_conversation_examples/`

### Channel Settings

Use for per-channel reply behavior:

- Telegram-specific response length;
- emoji/link rules;
- channel-specific formatting constraints;
- channel-specific reply style.

Source folder:

- `09_telegram_bot/`

Do not store Telegram bot tokens in documentation files.

### TenantKnowledgeSource

Use for retrievable business knowledge:

- FAQ;
- detailed pricing;
- policies;
- rules;
- promotions;
- static availability notes;
- service details;
- long-form sales reference material.

Source folders:

- `03_faq/`
- `04_prices_and_availability/`
- `05_policies_and_rules/`
- `06_promotions/`
- longer reference material from `02_ai_behavior_and_sales_materials/`

Possible `source_type` values after ingestion:

- `faq`
- `pricing`
- `policy`
- `promotion`
- `availability`
- `sales_material`

### PromptTemplate

Do not use for Orange Park-specific facts.

`PromptTemplate` is platform-owned and must remain generic. It controls system behavior, safety rules, task instructions, and prompt structure.

## Proposed Orange Park Workspace

```text
docs/businesses/orange-park/
  README.md
  00_intake/.gitkeep
  01_business_profile_facts/.gitkeep
  02_ai_behavior_and_sales_materials/.gitkeep
  03_faq/.gitkeep
  04_prices_and_availability/.gitkeep
  05_policies_and_rules/.gitkeep
  06_promotions/.gitkeep
  07_conversation_examples/.gitkeep
  08_bitrix24_mapping/.gitkeep
  09_telegram_bot/.gitkeep
  10_tests/.gitkeep
  generated/.gitkeep
```

Recommended `README.md` identifiers:

```text
business_external_id: orange-park
display_name: Orange Park / ЖК Orange Park
tenant_id: TODO
business_id: TODO
```

## Risks

- Orange Park internal `tenant_id` and `business_id` are still placeholders until the production business row exists.
- Promotions and availability can become stale if treated as static docs.
- The assistant must not promise live availability unless a future approved integration supplies it.
- Client documents may contain sensitive operational data; confirm whether this folder is allowed to be tracked before adding real client content.
- Secrets must not be copied from local `.env` files or external systems into documentation.

## Open Questions

- What exact `businesses.external_id` will be used in production: `orange-park` or another integration-specific value?
- Are Orange Park source documents allowed in git, or should this workspace hold only templates/index files while source docs live in private storage?
- Which language should be canonical for source material: Russian, English, German, or bilingual?
- Which Bitrix24 fields are needed for future mapping, without storing webhook URLs or credentials?

## Explicit Non-Goals

- No backend runtime behavior change.
- No n8n workflow change.
- No Mini App change.
- No ingestion script or API.
- No new architecture.
- No global shared folder for client-specific knowledge.
- No client facts in `PromptTemplate`.
- No secrets in documentation.
