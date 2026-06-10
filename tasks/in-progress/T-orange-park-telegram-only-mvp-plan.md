# T-orange-park-telegram-only-mvp-plan

## Goal

Prepare an implementation plan for an isolated Telegram-only Orange Park MVP.

Stage 1 connects a separate Orange Park Telegram bot through a separate n8n workflow to the existing backend webhook and AI orchestration flow. No Bitrix24 integration is included.

No implementation performed.

## Proposed isolated stage 1 architecture

```text
Telegram user
  -> Orange Park Telegram bot
  -> separate Orange Park n8n workflow
  -> POST backend /api/v1/webhook/message
       business_id = orange-park
       channel = telegram
  -> BusinessService resolves businesses.external_id
  -> backend uses resolved tenant_id + internal business_id
  -> AI Configuration Service
  -> TenantBusinessProfile / TenantAIProfile / TenantChannelSetting
  -> Conversation History Loader
  -> Knowledge Retrieval Service
  -> Prompt Builder
  -> AI Gateway
  -> backend validation/guardrails
  -> save AI message
  -> PromptRun logging
  -> n8n sends reply to same Telegram chat
```

Stage 1 must not call Bitrix24, create Bitrix leads, use Bitrix webhooks, or modify Bitrix mapping.

## Existing services/files to use

- Business resolution: `backend/app/services/business_service.py`
  - `BusinessService.get_by_external_id()` resolves webhook `business_id` to `businesses.external_id`.
- Incoming webhook schema: `backend/app/schemas/webhook.py`
  - `business_id` is a required external string.
  - `channel` supports `telegram`.
- Webhook orchestration: `backend/app/services/webhook_message_service.py`
  - Resolves business, tenant, flow, customer, conversation, message, AI response, and trace metadata.
- AI config: `backend/app/services/ai_configuration_service.py`
  - Loads `TenantBusinessProfile`, `TenantAIProfile`, and `TenantChannelSetting` by `tenant_id + business_id`.
- Knowledge retrieval: `backend/app/services/knowledge_retrieval_service.py`
  - Loads active `TenantKnowledgeSource` rows by `tenant_id + business_id`.
- Conversation history: `backend/app/services/message_service.py`
  - `load_recent_conversation_history()` filters by `tenant_id`, `business_id`, and `conversation_id`.
- AI orchestration: `backend/app/services/ai_reply_orchestration_service.py`
  - Passes scoped config, knowledge, and history to Prompt Builder.
- Prompt assembly: `backend/app/services/prompt_builder_service.py`
  - Keeps tenant/business context, knowledge, history, and current message as reference data.
- Existing source docs:
  - `docs/businesses/orange-park/01_business_profile_facts/`
  - `docs/businesses/orange-park/02_ai_behavior_and_sales_materials/`
  - `docs/businesses/orange-park/03_faq/`
  - `docs/businesses/orange-park/04_prices_and_availability/`
  - `docs/businesses/orange-park/05_policies_and_rules/`
  - `docs/businesses/orange-park/06_promotions/`
  - `docs/businesses/orange-park/07_conversation_examples/`
  - `docs/businesses/orange-park/09_telegram_bot/`

## DB/data setup steps

Create or confirm a dedicated Orange Park tenant and business in PostgreSQL:

- `tenants`
  - dedicated Orange Park tenant row, unless an approved existing Orange Park tenant already exists;
  - capture generated `tenant_id`.
- `businesses`
  - dedicated Orange Park business row;
  - `external_id = orange-park`;
  - capture generated internal `business_id`;
  - `tenant_id` must point to the Orange Park tenant.

All production Orange Park rows must be scoped by this exact `tenant_id + business_id`:

- `tenant_business_profiles`
- `tenant_ai_profiles`
- `tenant_channel_settings`
- `tenant_knowledge_sources`
- `customers`
- `conversations`
- `messages`
- `leads` if later enabled
- `prompt_runs`
- observability/trace/dead-letter/retry/rate-limit rows where applicable

Do not reuse another tenant, another business row, another business `external_id`, another business AI profile, or another business knowledge rows.

## Data loading into backend cells

Use existing backend cells only. Do not create new architecture or ingestion logic in stage 1.

- `TenantBusinessProfile`
  - Source: `docs/businesses/orange-park/01_business_profile_facts/`
  - Use stable factual business data only: project identity, location, construction facts, stable White Box facts, stable infrastructure, limitations.
- `TenantAIProfile`
  - Sources:
    - `docs/businesses/orange-park/02_ai_behavior_and_sales_materials/`
    - `docs/businesses/orange-park/05_policies_and_rules/`
  - Use tone, lead qualification behavior, handoff rules, forbidden promises, and no-overpromise rules.
- `TenantKnowledgeSource`
  - Sources:
    - `docs/businesses/orange-park/03_faq/`
    - `docs/businesses/orange-park/04_prices_and_availability/`
    - `docs/businesses/orange-park/06_promotions/`
    - `docs/businesses/orange-park/07_conversation_examples/`
  - Use retrievable FAQ, pricing caveats, manager-confirmation rules, promotion disclaimers, and conversation examples.
  - Mark time-sensitive rows with clear `source_type`/metadata/tags such as `pricing`, `availability`, `promotion`, `requires_manager_confirmation`.
- `TenantChannelSetting`
  - Source: `docs/businesses/orange-park/09_telegram_bot/`
  - Use `channel = telegram`, concise response style, and approved link/emoji rules.
- `PromptTemplate`
  - Platform-owned only.
  - Do not add Orange Park facts, prices, promotions, addresses, or sales copy to `PromptTemplate`.

## Separate n8n workflow plan

Create a new n8n workflow dedicated to Orange Park Telegram only.

Rules:

- Use only the Orange Park Telegram bot token, stored in environment/credentials.
- Do not put the token in repo docs, workflow exports, task files, logs, or screenshots.
- Do not reuse or modify working workflows for other businesses.
- Do not share a Telegram trigger, webhook URL, or router branch that can route traffic to another business.
- Do not call Bitrix24.
- Do not create Bitrix leads.
- Do not call Bitrix webhooks.
- Do not use Bitrix mapping.
- Normalize Telegram payload into the existing backend webhook contract.
- Send `business_id = orange-park`.
- Send `channel = telegram`.
- Set `customer.external_customer_id` from Telegram user id.
- Set `customer.name` from Telegram first/last name where available.
- Set `message.text` from Telegram message text.
- Set `message.external_message_id` to a Telegram-scoped stable id such as `tg:{chat.id}:{message.message_id}`.
- Set `message.external_conversation_id` to `tg:{chat.id}`.
- Send backend response text back to the same Telegram chat.

Recommended workflow shape:

```text
Orange Park Telegram Trigger
  -> Normalize Orange Park Telegram Incoming
  -> POST Alpstein Backend /api/v1/webhook/message
  -> Shape Customer Reply
  -> Send Telegram Reply
```

## Telegram routing plan

Runtime route:

```text
Telegram customer message
  -> Orange Park bot token
  -> Orange Park-only n8n workflow
  -> backend webhook body business_id = orange-park
  -> backend resolves businesses.external_id = orange-park
  -> backend derives Orange Park tenant_id and internal business_id
  -> backend loads only Orange Park profiles, channel settings, knowledge, conversation history
  -> AI response is saved under Orange Park tenant_id/business_id
  -> n8n sends response to original Telegram chat id
```

Any message with a different `business_id`, missing Orange Park business row, wrong channel, or invalid backend auth should fail or be rejected by existing backend validation/auth rather than being routed to another business.

## Data isolation rules

- Production isolation boundary is always `tenant_id + business_id`.
- n8n only sends `business_id = orange-park`; backend resolves internal IDs.
- All Orange Park AI config rows must be new rows scoped to Orange Park `tenant_id + business_id`.
- All Orange Park `tenant_knowledge_sources` rows must be scoped to Orange Park `tenant_id + business_id`.
- No global shared client-specific knowledge folder or DB row.
- No shared `TenantAIProfile` or `TenantBusinessProfile` from another business.
- No Orange Park facts in platform `PromptTemplate`.
- No Orange Park operator notes in another business workflow.
- No Bitrix fields, Bitrix webhook URLs, or Bitrix credentials in stage 1.

## Conversation isolation rules

- Incoming Telegram customers are created or loaded under Orange Park `tenant_id + business_id`.
- Conversations are created or reused under Orange Park `tenant_id + business_id + customer_id + channel`.
- Telegram `external_conversation_id` should be scoped to the Orange Park bot/chat, e.g. `tg:{chat.id}`.
- Messages are stored under Orange Park `tenant_id + business_id + conversation_id`.
- Conversation History Loader must load only rows matching Orange Park `tenant_id`, Orange Park `business_id`, and the current Orange Park `conversation_id`.
- AI must not use conversation history from another business, bot, workflow, or channel.

## PromptRun/logging checks

For each Orange Park AI turn, verify:

- `prompt_runs.tenant_id` equals Orange Park tenant UUID.
- `prompt_runs.business_id` equals Orange Park internal business UUID.
- `prompt_runs.conversation_id` belongs to an Orange Park conversation.
- `prompt_runs.message_id`, when present, belongs to an Orange Park message.
- Prompt metadata/observability includes Orange Park `business_external_id = orange-park`.
- Knowledge snippet IDs in prompt/log metadata, if visible, correspond only to Orange Park `tenant_knowledge_sources`.
- No prompt run includes another business facts, pricing, policies, or history.

## Test checklist

### Backend direct webhook test

POST a normalized Telegram-like payload to `/api/v1/webhook/message`:

- `business_id = orange-park`
- `channel = telegram`
- unique `customer.external_customer_id`
- unique `message.external_message_id`
- `message.external_conversation_id = tg:<test-chat-id>`

Expected:

- backend resolves Orange Park business;
- response is generated by existing AI flow;
- customer, conversation, inbound message, outbound AI message, and prompt run are scoped to Orange Park `tenant_id + business_id`.

### Telegram/n8n test

- Send a message to the Orange Park Telegram bot.
- Confirm only the Orange Park n8n workflow executes.
- Confirm backend request body contains `business_id = orange-park`.
- Confirm reply is sent to the same Telegram chat.
- Confirm no Bitrix node executes.
- Confirm no other business workflow executes.

### Backend log/DB checks

- Query Orange Park `customers`, `conversations`, `messages`, and `prompt_runs`.
- Confirm all rows use Orange Park `tenant_id + business_id`.
- Confirm no rows were added to another business for the test Telegram user/chat.
- Confirm conversation history for the second test message includes only the Orange Park thread.

### Negative tests

Ask:

- current price;
- current availability;
- active discount;
- exact monthly payment;
- єОселя approval;
- PrivatBank credit approval;
- legal guarantee or booking/reservation guarantee;
- something about another business;
- something not in Orange Park docs.

Expected:

- assistant does not invent or guarantee unstable data;
- assistant offers manager confirmation for prices, availability, discounts, financing, booking, and legal questions;
- assistant does not answer with another business facts;
- assistant asks a clarifying question or hands off when information is missing.

## Rollback plan

If Orange Park Telegram stage 1 must be disabled:

- Disable or deactivate only the Orange Park n8n workflow.
- Revoke/remove only the Orange Park Telegram bot credential from n8n runtime credentials/env.
- Mark Orange Park `tenant_channel_settings` for `telegram` inactive or stop using the Orange Park workflow.
- Do not delete shared platform `PromptTemplate`.
- Do not modify other business workflows.
- Keep Orange Park DB rows for audit unless explicit data cleanup is approved.
- If test data cleanup is approved, delete only rows scoped by Orange Park `tenant_id + business_id` and known test customers/conversations.

## Out of scope for stage 1

- Bitrix24 lead creation.
- Bitrix24 webhook calls.
- Bitrix24 mapping changes.
- Booking or reservation.
- Live availability.
- Live pricing.
- Payment confirmation.
- Mortgage, єОселя, credit, or voucher approval.
- Modifying other business integrations.
- Modifying existing working n8n workflows.
- Modifying Mini App.
- Creating ingestion logic.
- Changing backend runtime behavior.
- Adding Orange Park facts to global/platform `PromptTemplate`.
- Sharing another business Telegram bot, n8n workflow, profiles, conversations, knowledge, or prompt runs.

## Risks/open questions

- Orange Park `tenant_id` and internal `business_id` are still TODO until DB setup is approved/executed.
- Confirm final production `businesses.external_id`; default recommendation is `orange-park`.
- Confirm where Orange Park Telegram bot token will be stored in deployment credentials/env.
- Confirm whether a dedicated backend `flow` row is required for `flow_service.resolve_for_webhook()` or whether the default flow is sufficient.
- Confirm approved manager handoff wording for Telegram.
- Confirm which Orange Park prepared docs are approved for first AI profile/knowledge load.
- Confirm if any Telegram response links are allowed in stage 1.
- Confirm current prices/availability/promotions before any production sales use.
- Confirm retention/cleanup process for test Telegram conversations.

## Validation statement

No implementation performed.

This report does not change backend runtime code, n8n workflows, Mini App code, ingestion logic, secrets, commits, or pushes.
