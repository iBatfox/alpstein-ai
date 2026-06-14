# T-orange-park-contact-flow-and-metadata-diagnostics

> Historical record only. Superseded by Orange Park Dialog Engine v3.

## Status

Diagnostic and scoped implementation complete. Awaiting review.

## Scope

- Business: `businesses.external_id = orange-park`
- Channel: `telegram`
- Flow: `orange_park_telegram_mvp`
- No Bitrix webhook secret changes
- No secret values inspected, printed, or stored
- Other businesses and channels are out of scope

## Actual Message Flow

### 1. Customer asks for a manager or contact

1. The active n8n workflow `orange-park-telegram-mvp` receives a private Telegram
   message.
2. `Normalize Telegram Message` sends:
   - `business_id = orange-park`
   - `channel = telegram`
   - Telegram user and chat identifiers
   - text or `[telegram_contact_shared]`
   - optional Telegram contact fields
3. `POST /api/v1/webhook/message` resolves the Orange Park business, active flow,
   Telegram customer, and reusable conversation.
4. `WebhookMessageService` saves the inbound message.
5. `_resolve_orange_park_contact_collection_reply()` runs before the AI layer.
6. Direct handoff/contact keywords such as `менеджер`, `контакт`, `телефон`,
   `давай`, or `так` create inbound `message.metadata.orange_park_contact_collection`
   with `telegram_contact_request = true`.
7. The backend response maps that state to
   `data.metadata.telegram_contact_request.needed = true`.
8. The active n8n workflow reads that nested field and sends a Telegram reply
   keyboard with `request_contact = true`.

### 2. Assistant asks for a phone

There are two paths:

- Deterministic backend contact path: metadata is set and the button is sent in
  the same response.
- AI-generated path: the assistant may ask for a phone/contact in reply text, but
  no code currently derives transport metadata from that AI reply. The response
  therefore contains text only and n8n sends no contact button. A later customer
  reply such as `Давай` matches the deterministic trigger and only then produces
  the button metadata.

This is the cause of the delayed contact button.

### 3. Customer shares Telegram contact

1. Telegram sends `message.contact`.
2. n8n maps:
   - `contact.first_name`, falling back to `message.from.first_name`
   - `contact.last_name`, falling back to `message.from.last_name`
   - `contact.phone_number`
   - Telegram user id and username
   - `customer.contact_shared = true`
3. n8n sends `[telegram_contact_shared]` as normalized message text.
4. The backend saves the inbound message.
5. `_orange_park_shared_contact_metadata()` stores the contact in the current
   inbound message metadata.

### 4. Backend creates or updates Bitrix lead

1. The flow metadata enables Bitrix with
   `flow.metadata.crm.bitrix.enabled = true`.
2. `_orange_park_bitrix_contact_for_sync()` currently requires both phone and
   `first_name`.
3. `OrangeParkBitrixService` normalizes the phone.
4. It calls Bitrix duplicate search by phone.
5. It updates the first matching lead or creates a new lead.
6. The Bitrix lead id, action, and timestamp are written back to the current
   inbound message metadata.
7. Phone-based Bitrix duplicate search prevents a second Bitrix lead for the same
   normalized phone.

### 5. Assistant confirms handoff

After contact capture, `_orange_park_reply_after_shared_contact()` chooses the
reply from `missing_fields`.

- No missing name fields: exact success reply.
- Missing first name: asks for first name.
- Missing last name: asks for last name.
- Both missing: asks for both.

This runs even after Bitrix synchronization succeeded. Therefore a contact with
only `first_name` creates or updates the Bitrix lead and then incorrectly asks
for a last name.

## State And Metadata Sources

### Contact request state

Stored on the current inbound `messages.metadata` row:

```text
orange_park_contact_collection.telegram_contact_request = true
orange_park_contact_collection.intent
orange_park_contact_collection.missing_fields = ["telegram_contact"]
```

It is returned to n8n as response metadata by
`_response_metadata_from_message()`.

There is no contact request state in `conversations`, `customers`, or n8n static
workflow data.

### Contact received state

Stored on the Telegram contact inbound `messages.metadata` row:

```text
orange_park_contact_collection.contact_received = true
orange_park_contact_collection.phone
orange_park_contact_collection.first_name
orange_park_contact_collection.last_name
orange_park_contact_collection.telegram_id
orange_park_contact_collection.telegram_username
orange_park_contact_collection.external_crm_stage
orange_park_contact_collection.bitrix_lead_id
orange_park_contact_collection.action
orange_park_contact_collection.timestamp
```

### Name and phone sources

1. Telegram `message.contact` in n8n.
2. Telegram `message.from` fallback in n8n for first and last name.
3. Normalized `request.customer` fields in the backend.
4. `customers.name` and `customers.phone` are filled only when missing.
5. The current inbound message metadata is the source used by the Orange Park
   Bitrix adapter.

The backend does not read contact fields from conversation metadata. The
`conversations` table has no metadata column.

### Other metadata sources

- `message.metadata`: runtime contact request, contact received, CRM result, and
  `/start` exclusion flags.
- `message.raw_payload`: normalized/sanitized Telegram payload retained for
  audit; not used as prompt history.
- `conversation.metadata`: none; the table has no metadata field.
- `customer metadata`: none; the customer table has explicit name/phone fields
  and no metadata field.
- `flow.metadata`: integration enablement and flow-level feature flags.
- AI profile metadata: current behavior instructions loaded into the prompt.
- channel setting metadata: start greeting and Telegram channel defaults.
- prompt history: recent `messages.message_text` only; rows with
  `excluded_from_prompt_history = true` are omitted.
- n8n payload: includes a stale operator overlay that still says `No Bitrix24`.
- Telegram contact payload: native first name, optional last name, phone, and
  optional contact user id.

## Root Causes

### Last name requested after contact

`_orange_park_shared_contact_metadata()` records missing `last_name`, and
`_orange_park_reply_after_shared_contact()` treats that as blocking. This
conflicts with the current requirement and with Bitrix standard lead fields,
where last name is optional.

### Contact button delayed

Button metadata is created only from inbound keyword/phone matching. AI output is
not inspected for an Orange Park contact request, so an AI reply can ask for a
phone without setting transport metadata.

### Passive consultant behavior

The seeded Orange Park policy is consultant-first, but the two requested sales
intents depend on probabilistic AI output. There is no deterministic Orange
Park response guard ensuring a docs-first answer, relevant advantages, and one
qualification question for `Умови покупки` and `Цікавить 1-кімнатна`.

### Old prompt/history and metadata

- `/start` already marks all earlier messages in the same scoped conversation
  with `excluded_from_prompt_history = true`.
- `MessageService.load_recent_conversation_history()` excludes those rows.
- Runtime contact logic reads only the current inbound message metadata, not old
  contact metadata from prior rows.
- Persisted old contact metadata remains in the database for audit.
- Contact metadata has no version, so old and current rows are structurally
  indistinguishable.
- The active n8n payload still injects `No Bitrix24` in
  `operator_business_context`. Recent stored prompts confirm this obsolete text
  is still included.

## Database Inspection

Inspection was tenant/business scoped and redacted.

- Active Orange Park flow has Bitrix enabled.
- 368 Orange Park Telegram messages were present.
- 33 messages contained Orange Park contact metadata.
- 27 messages contained `/start` reset metadata.
- 206 messages were excluded from prompt history.
- The main active Telegram conversation contained 170 messages.
- Recent contact rows showed missing-last-name state even when CRM stage was
  `synced`.
- 123 Orange Park prompt runs were present.
- 18 prompt runs contained the stale n8n `No Bitrix24` overlay, including the
  newest inspected runs.
- Active knowledge rows were FAQ, pricing/availability, and conversation style.

No secret values were queried or printed.

## n8n Verification

The active workflow is `orange-park-telegram-mvp`.

It currently:

- accepts native Telegram contacts;
- reads `data.metadata.telegram_contact_request.needed`;
- sends `request_contact = true`;
- uses button text `📱 Поділитися номером`.

The requested flat response contract is not currently read:

```text
contact_request_required
contact_request_channel
telegram_reply_markup_type
telegram_button_text
```

No n8n change is required if the backend returns both the requested flat fields
and the existing nested compatibility field. The existing active workflow will
continue to send the button immediately.

## Fields To Clear Or Ignore

Do not delete historical audit data.

Ignore for current contact decisions:

- Orange Park contact metadata without
  `contact_flow_version = orange_park_v2`.
- Any pre-`/start` message marked `excluded_from_prompt_history = true`.
- Contact request metadata on older messages in the conversation.
- The Orange Park n8n `operator_business_context` overlay, because current
  business configuration and knowledge are authoritative and the overlay is
  stale.

No customer or conversation metadata cleanup is required because those metadata
stores do not exist.

## Exact Files And Services

- `n8n/workflows/orange-park-telegram-mvp.json`
- `backend/app/schemas/webhook.py`
- `backend/app/api/routes/webhook.py`
- `backend/app/services/webhook_message_service.py`
- `backend/app/services/message_service.py`
- `backend/app/services/customer_service.py`
- `backend/app/services/conversation_service.py`
- `backend/app/services/ai_reply_orchestration_service.py`
- `backend/app/services/prompt_builder_service.py`
- `backend/app/services/orange_park_bitrix_service.py`
- `backend/app/seed/orange_park_configuration.py`
- `backend/app/models/message.py`
- `backend/app/models/customer.py`
- `backend/app/models/conversation.py`
- `backend/app/models/flow.py`
- `backend/tests/test_webhook_message_service.py`
- `backend/tests/test_orange_park_bitrix_service.py`

## Proposed Minimal Fix

1. Add `contact_flow_version = orange_park_v2` to new Orange Park contact and
   `/start` metadata and ignore unversioned/older contact metadata for runtime
   response decisions.
2. Return the requested flat contact-button response metadata plus the existing
   nested compatibility metadata.
3. When an Orange Park Telegram AI reply asks for phone/contact, mark the current
   inbound message as requiring the Telegram contact button before returning the
   response.
4. Allow Bitrix sync with phone only by deriving a safe name in this order:
   provided first name, Telegram username, provided display name where available,
   then `Telegram contact`.
5. Treat last name as optional and return the exact manager-handoff confirmation
   after successful create/update.
6. Add deterministic docs-first Orange Park replies for the two requested sales
   intents, each with relevant documented advantages and one qualification
   question.
7. Ignore the stale Orange Park n8n operator overlay in backend prompt assembly.
8. Keep all guards scoped to Orange Park plus Telegram and add regression tests
   proving other businesses are unchanged.

## Out Of Scope

- Changing the Bitrix webhook secret
- Deleting historical messages or prompt runs
- General prompt architecture changes
- Other businesses or channels
- Unrelated n8n workflow changes
- Commit or push

## Implementation Result

- Added `contact_flow_version = orange_park_v2` to current Orange Park contact
  and `/start` metadata.
- Old unversioned contact metadata is ignored for runtime response decisions.
- Added the requested flat Telegram contact metadata:
  - `contact_request_required`
  - `contact_request_channel`
  - `telegram_reply_markup_type`
  - `telegram_button_text`
- Kept the existing nested `telegram_contact_request` field for the active n8n
  workflow.
- Added Orange Park-only detection when an AI reply asks for a phone/contact, so
  the current response immediately includes contact-button metadata.
- Made last name optional after native Telegram contact capture.
- Added safe Bitrix first-name fallback:
  - Telegram first name
  - Telegram username
  - `Telegram contact`
- Added docs-backed consultant responses for:
  - `Умови покупки`
  - `Цікавить 1-кімнатна`
- Ignored the stale Orange Park n8n operator overlay at the backend AI-call
  boundary.
- No n8n workflow change was required.

## Validation Result

- `tests/test_webhook_message_service.py`: 38 passed.
- discovered Bitrix tests: 7 passed.
- full backend suite: 799 passed, 4 skipped.
- Python compile check: passed.
- `git diff --check`: passed.

## Live Smoke Result

The backend container was rebuilt and restarted without recreating Postgres.

1. `/start`: Ukrainian reset greeting returned.
2. `Умови покупки`: docs-first financing answer plus one qualification question.
3. `Цікавить 1-кімнатна`: 35-41 m², White Box, territory/infrastructure, and one
   qualification question.
4. `Хочу щоб менеджер зв'язався`: response included
   `contact_request_required = true` and
   `telegram_reply_markup_type = request_contact` immediately.
5. Native contact with first name and no last name:
   - exact final handoff reply returned;
   - no last-name question;
   - Bitrix action was `update`;
   - existing Bitrix lead id was `39001`;
   - `lead_created = false`;
   - `lead_updated = true`;
   - `notify_owner = false`.

The active n8n workflow was separately verified to read the retained nested
compatibility metadata and send `request_contact = true`. Telegram delivery was
not triggered from a real customer account during this backend smoke.
> Historical record only. Superseded by Orange Park Dialog Engine v3. Legacy
> metadata and workflow text below are retained only as diagnostic history.
