# Orange Park Pre-Ingestion Documentation Workspace

## Purpose

This folder is the isolated pre-ingestion documentation workspace for Orange Park / ЖК Orange Park.

Use it to collect, review, and normalize client-provided business materials before any approved ingestion into Alpstein AI production data stores.

## Important Warnings

- This is pre-ingestion documentation only.
- Runtime source of truth remains PostgreSQL.
- Do not treat files in this folder as live assistant context until a separate approved ingestion task writes scoped records to the existing backend tables.
- Production isolation must remain `tenant_id + business_id`.
- Runtime business identity enters through `businesses.external_id`.

## Placeholder Identifiers

```text
business_external_id: orange-park
display_name: Orange Park / ЖК Orange Park
tenant_id: TODO
business_id: TODO
```

## Backend Cell Mapping

### TenantBusinessProfile

Store stable factual business data here after ingestion:

- business description;
- project/location facts;
- services;
- stable pricing summary;
- working hours;
- city, region, country;
- business limitations.

Recommended source folders:

- `01_business_profile_facts/`
- stable summaries from `04_prices_and_availability/`
- stable limitations from `05_policies_and_rules/`

### TenantAIProfile

Store assistant behavior and sales style here after ingestion:

- tone;
- language;
- response style;
- lead qualification questions;
- handoff rules;
- forbidden promises;
- fallback behavior.

Recommended source folders:

- `02_ai_behavior_and_sales_materials/`
- selected patterns from `07_conversation_examples/`

### Channel Settings

Store per-channel reply behavior here after ingestion:

- Telegram-specific response length;
- emoji/link rules;
- channel-specific formatting constraints;
- channel-specific reply style.

Recommended source folder:

- `09_telegram_bot/`

Do not store Telegram bot tokens in this folder.

### TenantKnowledgeSource

Store retrievable business knowledge here after ingestion:

- FAQ;
- detailed pricing;
- policies;
- rules;
- promotions;
- static availability notes;
- service details;
- sales reference material.

Recommended source folders:

- `03_faq/`
- `04_prices_and_availability/`
- `05_policies_and_rules/`
- `06_promotions/`
- longer reference material from `02_ai_behavior_and_sales_materials/`

### PromptTemplate

Do not store Orange Park-specific facts in `PromptTemplate`.

`PromptTemplate` is platform-owned and must remain generic. It controls Alpstein AI system behavior, safety rules, task instructions, and prompt structure.

## Secret Handling Rules

- No secrets in this folder.
- No Telegram bot token.
- No Bitrix24 webhook URL.
- No API keys.
- No passwords.
- No database URLs.
- No private n8n credentials.

Secrets must remain in environment variables or existing secret management only.
