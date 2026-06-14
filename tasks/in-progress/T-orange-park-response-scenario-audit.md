# T-orange-park-response-scenario-audit

> Historical audit only. Superseded by Orange Park Dialog Engine v3.

## Status

Audit only. No backend, n8n, Bitrix, configuration, migration, commit, or push
changes are part of this task.

Audit date: 2026-06-13.

Runtime checked during the audit:

- compose backend: healthy;
- database migration: `0027 (head)`;
- Orange Park flow: `orange_park_telegram_mvp`;
- flow metadata: `lead_creation_enabled=false`,
  `crm.bitrix.enabled=true`;
- backend Bitrix webhook setting: configured;
- n8n workflow source:
  `n8n/workflows/orange-park-telegram-mvp.json`.

The report describes the current working tree and active compose configuration.
Several Orange Park runtime changes are not committed yet.

## Executive Summary

Orange Park currently has five response mechanisms:

1. deterministic `/start`;
2. deterministic consultant replies for only two exact intent families;
3. deterministic apartment-area fallback inferred from recent text;
4. deterministic contact/price/availability handoff;
5. general AI orchestration for everything else.

The flow is not yet a coherent state machine. Contact state is mostly inferred
from the current text, apartment-area state is inferred from the last six
messages, and most manager-handoff intents remain AI-dependent. The broad
shortcut `Так` / `давай` / `ок` / `добре` requests contact even without an
active contact state.

The most important runtime risk is Bitrix failure. Native contact processing
calls Bitrix before saving and returning the confirmation reply. A Bitrix
timeout/API error raises out of the webhook, so the user may receive no
confirmation even though the Telegram contact was already persisted.

## Separate Schematic: Where The Bot Calls Now

```text
Telegram user
  |
  v
Orange Park Telegram bot
  |
  v
n8n: Telegram Trigger
  |
  v
n8n: Normalize Telegram Message
  - text -> message.text
  - native contact -> customer.contact_shared=true
  - contact text placeholder -> [telegram_contact_shared]
  - business_id=orange-park, channel=telegram
  |
  v
n8n: POST /api/v1/webhook/message
  |
  v
Backend WebhookMessageService
  |
  +--> BusinessService / FlowService
  |      -> PostgreSQL: Orange Park tenant + business + flow
  |
  +--> CustomerService / ConversationService / MessageService
  |      -> PostgreSQL: customer, conversation, inbound message
  |
  +--> duplicate?
  |      -> return previous AI reply or generic acknowledgment
  |      -> no new AI, PromptRun, lead, or Bitrix call
  |
  +--> native Telegram contact?
  |      |
  |      +--> flow Bitrix enabled and webhook configured
  |      |      -> LeadService: create/update Alpstein lead
  |      |      -> MessageService: load recent history
  |      |      -> Bitrix24:
  |      |           1. crm.duplicate.findbycomm by phone
  |      |           2a. crm.lead.update, or
  |      |           2b. crm.lead.add
  |      |      -> deterministic confirmation
  |      |
  |      +--> Bitrix disabled/unconfigured
  |             -> deterministic confirmation
  |
  +--> response priority inside _resolve_reply_to_customer:
         1. /start
         2. exact purchase-terms / one-room consultant reply
         3. short numeric area with inferred area context
         4. manual phone / budget / price / availability /
            contact-handoff markers
         5. AI orchestration
              -> AiConfigurationService -> PostgreSQL profiles/settings/template
              -> KnowledgeRetrievalService -> PostgreSQL knowledge rows
              -> MessageService -> PostgreSQL recent history
              -> PromptBuilderService
              -> AI Gateway -> OpenAI
              -> PromptRunService -> PostgreSQL prompt_runs
              -> save outgoing AI message
              -> if AI wording asks for phone/contact:
                   add Telegram contact-button metadata
  |
  v
Backend JSON:
  data.reply_to_customer
  data.metadata.telegram_contact_request (only when detected)
  |
  v
n8n: Shape Telegram Reply
  - reads reply text
  - reads metadata.telegram_contact_request.needed
  - adds request_contact keyboard when true
  |
  v
n8n: Telegram Send Message
  |
  v
Telegram user
```

## Current Priority Order

The actual current order is:

```text
tenant/business/flow resolution
-> persist inbound message
-> duplicate short circuit
-> rate/spam/containment checks
-> optional Alpstein lead and Bitrix contact sync
-> /start
-> exact consultant handlers
-> inferred area reply
-> contact/price/availability handlers
-> AI
-> AI-text contact metadata post-processing
-> n8n Telegram response shaping
```

Bitrix is called before response resolution. This matters for failure behavior.

## Part 1: Current Runtime Scenario Map

Legend:

- `AI`: AI Gateway call.
- `PR`: new `PromptRun`.
- `Button`: Telegram contact-button metadata.
- `Bitrix`: external Bitrix24 call.
- `Tests`: direct focused coverage, not merely generic service coverage.

| # | Scenario | Trigger and handler | AI / PR | Button | Bitrix | Current response pattern | Risks and test coverage |
|---|---|---|---|---|---|---|---|
| 1 | `/start` | Exact `/start` or `/start ...`; `_resolve_orange_park_start_reply()` | No / No | No | No | Fixed Ukrainian welcome with apartment, commercial, purchase choices | Archives all previous messages in the same conversation from prompt history. Covered by `test_orange_park_telegram_start_always_ukrainian_and_skips_ai`. |
| 2 | Normal AI-routed message | No earlier deterministic guard; `_resolve_reply_to_customer()` -> coordinator -> orchestration | Yes / Yes | Only if final AI text matches phone/contact phrases | No | AI answer from business profile, retrieved knowledge, history, latest message | Output and button behavior are probabilistic. Covered generally by orchestration tests; no scenario-specific live assertions for most Orange Park topics. |
| 3 | Contact/handoff intent | Current text contains broad handoff/contact markers or short `Так/давай/ок/добре`; `_orange_park_contact_collection_reply_and_metadata()` | No / No | Yes | No | Exact Ukrainian native-contact instruction | `Так` can trigger contact on the first turn because history is ignored. Russian/English request still gets Ukrainian. Covered by handoff and button metadata tests. |
| 4 | Telegram contact payload | `customer.contact_shared=true` plus phone; metadata created before reply | No / No | No | Yes in active runtime | Fixed `Дякуємо. Запит передано менеджеру. Очікуйте дзвінок.` | Missing surname is ignored despite policy text saying ask only for missing names. Bitrix failure aborts reply. Covered for disabled and enabled Bitrix, first-name-only behavior, and workflow normalization. |
| 5 | Manual phone number | Regex finds 8+ digit phone in message text | No / No | Yes | No | Exact native-contact instruction; typed phone marked ignored | Correct for button-only policy, but cannot use typed phone as fallback. Covered directly. |
| 6 | Short numeric apartment area | Message is 1-3 digit area, `1..300`, and recent six-message history appears to expect/discuss area | No / No | No | No | `<35`: explain minimum 35; `35..41`: one-room fit; `>41`: suggest larger format | State is inferred from text, not stored slot state; stale area mention may activate it. Covered for 25/35/40/60 and no-context fallback. |
| 7 | Purchase terms question | Contains exact substring `умови покупки` or `умови придбання` | No / No | No | No | Fixed list of payment paths, manager caveat, one qualification question | Narrow matching: `Розтермінування`, `єОселя`, Russian wording go to AI. Fixed reply always Ukrainian. Covered for exact Ukrainian phrase only. |
| 8 | One-room apartment interest | Contains `цікавить 1-кімнатна`, `цікавить однокімнатна`, or Russian `интересует 1-комнатная` | No / No | No | No | Fixed 35-41 m2, White Box/infrastructure, living vs investment question | Russian trigger receives Ukrainian reply. Other forms such as `Хочу однокімнатну` go to AI. Covered for one Ukrainian form. |
| 9 | Price question | Current-options markers include `ціна`, `ціни`, `вартість`, `скільки кошту` | No / No | Yes | No | Generic “current options within budget” manager confirmation plus button | Wording is budget-specific even for plain price questions. Russian `цена/стоимость` is not deterministic and goes to AI. Covered indirectly through marker helper, but not direct `Яка ціна?` service test. |
| 10 | Availability question | Markers `що є в наявності`, `актуальні варіанти`, etc. | No / No | Yes | No | Same budget-oriented manager reply plus button | Gives no docs-first stable context and asks contact immediately. Covered for `Що є в наявності?`. |
| 11 | Viewing/video viewing | No deterministic viewing handler; AI policy/knowledge classify it as manager handoff | Yes / Yes | Conditional on exact AI wording | No until contact shared | AI should answer first, qualify format, then request manager contact if useful | Button can be absent if AI says “manager” without a recognized phone phrase. No focused end-to-end test. |
| 12 | Commercial premises | General questions go to AI; price/availability wording may be intercepted by generic current-options guard | Usually Yes / Yes | Usually No; Yes for intercepted unstable wording or AI contact phrase | No until contact shared | AI uses business profile/FAQ; should ask type, area, budget | No dedicated deterministic path or focused response test. Generic `ціна` may lose commercial context. |
| 13 | Infrastructure/location/transport | AI path and retrieval | Yes / Yes | No unless AI asks contact | No | Docs-first answer plus one qualification question expected from policy | Retrieval is document-prefix based and may truncate the relevant section. No direct Orange Park runtime tests for location, transport, White Box, shelter, parking. |
| 14 | Fallback/unclear message | AI first; if AI fails/empty, `AiReplyFallbackService` uses tenant fallback | Yes / Yes | No | No | `Уточніть... квартира, комерційне приміщення чи умови придбання?` on AI failure | AI failure creates PromptRun, but fallback metadata does not request handoff/contact. No Orange Park-specific fallback integration test. |
| 15 | Duplicate Bitrix lead update | A new Telegram contact message with a phone already found by Bitrix `crm.duplicate.findbycomm` | No / No | No | Yes: search then update | Same fixed confirmation; response reports `lead_updated=true` | Same Telegram event ID is instead a webhook duplicate and skips Bitrix entirely. Bitrix update service test exists; full webhook update path is not directly asserted. |
| 16 | Bitrix failure | Timeout, network, HTTP, malformed JSON, Bitrix API error during contact sync | No / No | No | Attempted and failed | No backend success reply; exception propagates and trace is failed | Critical demo risk. n8n POST has no continue-on-fail/error branch, so Telegram fallback shaping may not run. No webhook resilience test. |
| 17 | Stale history/metadata after `/start` | `/start` marks all prior messages `excluded_from_prompt_history=true`; future history loader skips them | No AI on `/start`; later turns use AI as needed | Per later turn | Per later contact | New welcome, then future turns should see only post-start history | Existing conversation and old metadata remain stored. Current guards mostly inspect loaded history; old contact metadata is version-gated only when read from the current message. Covered for archive SQL and old metadata version rejection. |

## Response Metadata And Transport Behavior

Backend emits the Telegram button only when current inbound message metadata has:

```json
{
  "orange_park_contact_collection": {
    "contact_flow_version": "orange_park_v2",
    "telegram_contact_request": true
  }
}
```

It maps this to:

```json
{
  "metadata": {
    "telegram_contact_request": {
      "needed": true,
      "button_text": "📱 Поділитися номером"
    }
  }
}
```

n8n reads only `metadata.telegram_contact_request.needed`. It does not use the
other backend aliases. The send node uses a fixed keyboard/button label rather
than `button_text` returned by backend.

## AI Path Details

For an AI-routed message:

1. `AiConfigurationService` loads tenant/business profile, AI profile, Telegram
   channel settings, and platform template.
2. `KnowledgeRetrievalService` loads all active Orange Park knowledge rows,
   ranks entire documents by simple token substring count, and takes at most
   five snippets of 1,000 characters each / 4,000 total.
3. `MessageService` loads the last 20 messages and excludes messages marked by
   `/start`.
4. `GreetingPolicyService` chooses first/follow-up/soft-return and reply language.
5. `PromptBuilderService` assembles platform, business facts, behavior, channel,
   knowledge, history, and latest message.
6. `AI Gateway` calls OpenAI.
7. `PromptRunService` creates one PromptRun for success or provider failure.
8. Backend saves the outgoing AI/fallback message.
9. Orange Park post-processing scans the final AI text for phone/contact wording
   and may attach contact-button metadata.

Orange Park deliberately drops `operator_business_context` before prompt
assembly, so the stale n8n overlay does not affect AI replies.

## Part 2: Conflicts

### Deterministic Backend vs AI Responses

- Only purchase-terms and one-room interest have deterministic helpful answers.
  Semantically adjacent wording can produce a different AI path and response.
- Price/availability are deterministic immediate handoffs; viewing, financing,
  legal, and booking are AI handoffs. Similar critical intents therefore have
  different reliability.
- Deterministic replies are saved as `sender_type=ai`, even though no AI or
  PromptRun exists. This is useful for customer history but weakens audit
  semantics.
- Contact-button metadata inferred from generated AI text couples transport
  behavior to model wording.

### AI Policies vs Hardcoded Replies

- Policy says reply in the latest-message language. Hardcoded replies are
  Ukrainian, including Russian one-room and handoff triggers.
- Policy says help before requesting contact and avoid premature contact.
  Hardcoded `Так`, `ок`, `добре`, and all price/availability markers request
  contact immediately.
- Policy says ask only for missing name fields after contact. Runtime currently
  confirms immediately and does not ask for a missing surname.
- Policy says purchase financing terms require manager handoff. The exact
  purchase-terms hardcoded reply does not include a contact button.

### TenantAIProfile vs Prompt Builder

- The full policy document is injected through
  `metadata.behavior_instructions`, alongside structured behavior fields.
  This creates duplicate policy representations.
- `response_style` says `docs first`, while customer-facing policy forbids
  mentioning docs/materials. The intended concept is correct but wording in
  configuration invites leakage.
- Prompt Builder treats tenant behavior as reference data rather than system
  authority, so model compliance with exact button wording is not guaranteed.
- `handoff_keywords` do not route backend behavior. They only reach the model.

### Contact State Metadata vs Conversation History

- No persistent `contact_requested` slot is read on the next turn.
- `_orange_park_contact_collection_reply_and_metadata()` discards history.
- Short acknowledgements are treated as handoff triggers globally, not only
  after the bot offered manager contact.
- Apartment-area state is inferred from natural-language history instead of
  explicit metadata/state.
- `budget_expected` and `purchase_path_expected` do not exist in runtime.

### n8n Metadata vs Backend Metadata

- Backend emits several aliases, but n8n reads only one nested field.
- n8n ignores backend `telegram_button_text` and uses a fixed label.
- n8n still sends an obsolete `operator_business_context` claiming “No
  Bitrix24”; backend silently strips it for Orange Park.
- The HTTP node has no explicit error branch/continue-on-fail. Backend 5xx can
  stop before the Ukrainian fallback in `Shape Telegram Reply`.

### Old Operator Overlay vs New DB Configuration

- DB profile/AI policy/knowledge are the active source of truth.
- n8n still carries a stale static overlay with old product behavior.
- Orange Park-specific backend code drops the overlay entirely, while other
  businesses still append operator notes in Prompt Builder.
- This is safe today but creates misleading operational configuration.

### Docs-First vs Manager-Handoff

- Price and availability skip all stable explanatory context and immediately
  request contact.
- Viewing and financing rely on AI to balance answer-first and handoff.
- The same marker `ціна` catches residential and commercial questions without
  preserving subject context.
- Knowledge retrieval uses document-prefix snippets, so “docs-first” does not
  guarantee that the relevant FAQ section reaches the prompt.

### Ukrainian Default vs Language Mirroring

- `/start` correctly forces Ukrainian.
- AI path detects the latest message language, defaulting to Ukrainian.
- Deterministic Orange Park paths do not use language detection.
- A Russian handoff or one-room request therefore receives Ukrainian; this
  conflicts with the written policy.

### Bitrix Lead Creation vs Telegram-Only MVP Texts

- Active runtime has Bitrix enabled, while the seeded AI policy still says “No
  Bitrix24 or external CRM behavior.”
- n8n overlay also says “No Bitrix24,” although backend ignores it.
- Contact sync also creates/updates an Alpstein lead when Bitrix is enabled,
  despite flow metadata `lead_creation_enabled=false`, because contact sync is
  an explicit exception.
- Webhook response `lead_created/lead_updated` is overwritten from the Bitrix
  action, while `lead` still refers to the Alpstein lead. The fields represent
  two systems at once.

## Additional Risks

1. Bitrix is a synchronous dependency in the customer-response critical path.
2. Contact is accepted even when Telegram contact `user_id` does not match the
   sender; n8n captures both IDs but backend does not validate ownership.
3. A native contact with phone but no first name still proceeds using username
   or `"Telegram contact"`.
4. Plain `25` without area context goes to AI, which may interpret it
   unpredictably.
5. Exact contact-button wording is duplicated in backend, n8n, policy, tests,
   and seed/channel metadata.
6. The legacy flow path lacks the new deterministic consultant handler and
   native-contact/Bitrix behavior parity.
7. Bitrix tests cover successful create/update and missing configuration, but
   not timeout/API-error behavior at webhook level.

## Part 3: Proposed Stable Conversation Logic

### Priority 0: Platform Safety And Tenant Isolation

- Resolve `business_id=orange-park` to one tenant/business/flow.
- Validate every DB read/write by `tenant_id + business_id + flow_id` where
  applicable.
- Reject unsupported channel/business combinations.
- Persist inbound message and enforce idempotency before side effects.
- Never use n8n operator text as Orange Park source of truth.

### Priority 1: Telegram System Commands

`/start`:

- deterministic Ukrainian welcome;
- reset explicit conversation slot state;
- exclude prior history from future prompt input;
- no AI, PromptRun, lead, Bitrix, or contact button.

### Priority 2: Telegram Contact Payload

- Validate native contact, phone, sender/contact ownership when Telegram
  provides `contact.user_id`.
- Persist contact immediately.
- Return customer confirmation independently of CRM availability.
- Attempt Bitrix create/update in a failure-contained integration step.
- Never ask for surname merely because Telegram omitted it.
- Do not call AI or create PromptRun.

### Priority 3: Explicit Active Slots

Store and read explicit state rather than infer it from arbitrary text:

- `contact_requested`;
- `apartment_area_expected`;
- `budget_expected`;
- `purchase_path_expected`.

Rules:

- `Так/ок/добре` only advances an existing slot.
- Numeric input is interpreted as area only when
  `apartment_area_expected=true`.
- Clear/reset a slot after successful consumption or `/start`.
- Never keep multiple ambiguous expected slots active.

### Priority 4: Critical Handoff Triggers

Deterministically classify:

- exact/current price;
- exact/current availability;
- booking/reservation;
- exact viewing of a specific unit;
- legal/payment/bank/tax/notary details;
- financing approval or exact monthly payment;
- commissioning/readiness/keys dates;
- current shelter readiness.

Response contract:

1. short helpful boundary or known stable context;
2. one qualification question if information is missing;
3. contact button only when manager action is now useful.

Do not make button display depend on AI wording.

### Priority 5: Docs-First Informational Answers

AI or deterministic grounded answers may cover:

- project and location;
- transport;
- White Box;
- infrastructure;
- stable security facts;
- apartment types and documented area ranges;
- general purchase options;
- general commercial-premises characteristics.

Standards:

- answer the question first;
- no internal source wording;
- one useful qualification question at most;
- no contact request unless the next step needs current manager data.

### Priority 6: Sales Consultant Qualification

Collect progressively, not as a form:

- room count / property type;
- living vs investment;
- desired area;
- budget;
- purchase path;
- viewing vs video viewing.

Ask one question per turn and reuse already known answers.

### Priority 7: Contact Request

Request native contact only when:

- customer explicitly asks for a manager;
- current data must be checked;
- a specific viewing/video viewing should be arranged;
- qualification is sufficient for a useful manager callback.

Persist `contact_requested=true`. Do not repeatedly ask after contact is shared.

### Priority 8: Fallback

For unclear input:

- Ukrainian by default;
- offer the three supported categories;
- do not claim manager handoff;
- no button unless an active contact slot exists.

## Proposed State Sketch

```text
idle
  |
  +-- apartment interest --> apartment_area_expected
  |                            |
  |                            +-- area --> purpose/budget qualification
  |
  +-- purchase options --> purchase_path_expected
  |                         |
  |                         +-- path --> grounded answer / qualification
  |
  +-- exact/current data --> qualification or contact_requested
  |
  +-- explicit manager --> contact_requested
                              |
                              +-- native contact --> contact_received
                                                       |
                                                       +-- confirm user
                                                       +-- Bitrix sync separately

/start from any state --> idle + history reset
```

## Part 4: Desired Response Standards

- Ukrainian is the default; `/start` is always Ukrainian.
- Mirror a clearly Russian or English latest message for normal replies.
- Never mention materials, docs, files, database, context, prompt, RAG,
  retrieval, or knowledge base.
- Give the helpful answer before qualification or handoff.
- Ask no more than one qualification question per turn.
- Do not request contact at the beginning without a concrete reason.
- Current/exact data requires manager confirmation and a deterministic contact
  button when callback action is useful.
- After native Telegram contact, do not ask for surname; acknowledge immediately.
- CRM failure must not suppress the customer acknowledgment.
- Do not repeat the contact request after contact has been received.
- `/start` must prevent old history and old slot state from affecting later
  turns.
- Deterministic and AI paths must follow the same language and style rules.

## Part 5: Test Matrix

This matrix defines desired stable behavior, not necessarily current behavior.

| # | Customer message | Prior state | Expected path | Expected response pattern | Mode | Button | Bitrix | PR |
|---|---|---|---|---|---|---|---|---|
| 1 | `/start` | stale conversation | system command/reset | Ukrainian welcome, three categories | Deterministic | No | No | No |
| 2 | `Цікавить квартира` | idle | qualification | Ask room count or area, no contact | AI/grounded policy | No | No | Yes |
| 3 | `Цікавить 1-кімнатна` | idle | apartment facts | 35-41 m2, one purpose question | Deterministic | No | No | No |
| 4 | `Мене цікавить до 35 квадратів` | idle | apartment qualification | Clarify acceptable area/purpose; set area slot only if needed | AI/grounded policy | No | No | Yes |
| 5 | `25` | `apartment_area_expected` | consume area slot | Explain minimum 35 m2, offer next useful option | Deterministic | No | No | No |
| 6 | `25` | idle | unclear numeric | Ask what 25 refers to | Deterministic fallback | No | No | No |
| 7 | `Яка ціна?` | apartment type known | critical current price | Explain dependency, manager confirmation, contact request | Deterministic | Yes | No | No |
| 8 | `Що є в наявності?` | room/area known | critical availability | Confirm manager checks matching options | Deterministic | Yes | No | No |
| 9 | `Які умови покупки?` | idle | general purchase info | List paths, ask one purchase-path question | Deterministic/grounded | No | No | No |
| 10 | `Розтермінування` | `purchase_path_expected` | financing path | General availability + current terms need confirmation | Deterministic/grounded | No initially | No | No |
| 11 | `єОселя` | `purchase_path_expected` | financing path | General availability, no approval promise, one eligibility question | Deterministic/grounded | No initially | No | No |
| 12 | `Який буде точний платіж на місяць?` | financing interest known | critical exact financing | Manager calculation + contact | Deterministic | Yes | No | No |
| 13 | `Хочу перегляд` | property interest known | viewing qualification | Ask onsite date or target format; contact when actionable | Deterministic/AI | Conditional | No | Conditional |
| 14 | `Хочу відеоогляд` | property interest known | video viewing | Explain manager can arrange for available unit; ask format | Deterministic/AI | Conditional | No | Conditional |
| 15 | `Комерційне приміщення` | idle | commercial qualification | Ask business type or desired area/budget | AI/grounded policy | No | No | Yes |
| 16 | `Яка ціна комерційного приміщення?` | commercial interest | critical price | Preserve commercial context, manager confirmation | Deterministic | Yes | No | No |
| 17 | `Де знаходиться?` | idle | docs-first location | Odeska 23, Kriukivshchyna, about 5 km from Kyiv | AI/grounded policy | No | No | Yes |
| 18 | `Як доїхати?` | idle | docs-first transport | Routes 723/427/306 and OrangePark stop, caveat only if needed | AI/grounded policy | No | No | Yes |
| 19 | `Що таке White Box?` | idle | docs-first White Box | Explain included base finish naturally | AI/grounded policy | No | No | Yes |
| 20 | `Чи є укриття?` | idle | stable + current boundary | Source says shelter exists; current readiness requires confirmation | AI/grounded policy | No unless readiness requested | No | Yes |
| 21 | `Чи є парковка?` | idle | docs-first parking | Ground parking around perimeter; current spaces need confirmation | AI/grounded policy | No | No | Yes |
| 22 | `Хочу щоб менеджер зв'язався` | idle | explicit handoff | Native-contact instruction | Deterministic | Yes | No | No |
| 23 | `+380671112233` | `contact_requested` | manual phone rejection | Ask to use Telegram contact button | Deterministic | Yes | No | No |
| 24 | native Telegram contact payload | `contact_requested` | contact received | Immediate acknowledgment, no surname question | Deterministic | No | Create/update | No |
| 25 | native contact, same phone, new message id | contact already received | duplicate CRM identity | Immediate acknowledgment | Deterministic | No | Update existing | No |
| 26 | same Telegram event id replay | any | webhook duplicate | Return original reply, no new side effects | Deterministic replay | Original metadata if available | No | No |
| 27 | native contact while Bitrix times out | `contact_requested` | contact + contained integration failure | Still acknowledge; record sync failure for retry/ops | Deterministic | No | Failed attempt | No |
| 28 | `Не зрозумів` | idle | unclear fallback | Offer apartment/commercial/purchase categories | Deterministic fallback | No | No | No |
| 29 | `Де знаходиться?` after `/start` | old pre-start Russian/contact history | clean post-reset AI path | Ukrainian location answer; no old contact loop | AI/grounded policy | No | No | Yes |
| 30 | `Да` | idle, no active slot | ordinary unclear/confirmation | Must not request contact without active state | Deterministic fallback/AI | No | No | Conditional |

## Existing Test Coverage Summary

Strong focused coverage:

- `/start` Ukrainian response, no AI, history exclusion;
- exact purchase-terms and one-room helper replies;
- budget/current-options contact button;
- handoff markers and manual phone;
- short numeric area with and without context;
- native contact normalization and acknowledgment;
- contact metadata version guard;
- AI-text contact-request metadata;
- Bitrix create/update service behavior;
- Bitrix-enabled contact webhook success;
- missing Bitrix configuration;
- ordinary messages do not call Bitrix;
- n8n request-contact keyboard.

Missing or weak coverage:

- location, transport, White Box, shelter, parking, commercial premises;
- viewing/video viewing;
- standalone `Розтермінування` and `єОселя`;
- Russian/English language parity across deterministic paths;
- `Так/ок/добре` without active contact state;
- explicit persistent slot transitions;
- Bitrix timeout/API failure at webhook level;
- n8n error delivery when backend returns 5xx;
- full webhook Bitrix update response;
- contact ownership (`contact.user_id == sender id`);
- post-`/start` next-turn prompt contents;
- button removal/no-loop behavior after contact.

## Part 6: Recommendations

### Must Fix Before Client Demo

1. Contain Bitrix failures so native contact always receives the acknowledgment.
2. Replace global short acknowledgements as contact triggers with an explicit
   `contact_requested` state.
3. Add deterministic routing for all critical handoff intents, including
   viewing, booking, financing, legal/payment, and current readiness.
4. Make button metadata a routing decision, not an AI-text scan.
5. Align runtime policy/docs with active Bitrix integration and remove the stale
   n8n “No Bitrix24” overlay.
6. Add n8n backend-error handling that still sends a safe Ukrainian reply.
7. Add focused demo tests for the required 25+ prompts, especially the currently
   AI-only informational paths.

### Should Fix After Demo

1. Introduce explicit Orange Park slot/state metadata for area, budget, purchase
   path, and contact request.
2. Apply one shared language policy to deterministic and AI paths.
3. Preserve subject context in critical handoffs, especially commercial vs
   residential price/availability.
4. Validate Telegram contact ownership when `contact.user_id` is present.
5. Separate Alpstein lead result from Bitrix sync result in the webhook response.
6. Improve retrieval from whole-document prefix snippets to section-level
   chunks without changing the AI layer boundary.
7. Add a full webhook test for Bitrix update and repeated native contact.

### Later Architecture Cleanup

1. Move Orange Park intent classification and state transitions out of the
   oversized webhook service into a tenant-scoped backend policy service.
2. Distinguish deterministic outgoing messages from provider-generated messages
   in audit metadata while keeping them customer-visible assistant messages.
3. Remove legacy flow behavior once the migration compatibility window closes.
4. Centralize Telegram contact-button wording in one backend response contract.
5. Decouple CRM delivery from synchronous customer reply, using an approved
   retry/outbox mechanism when architecture scope allows it.

## Recommended Next Implementation Tasks

Small, reviewable order:

1. `T-orange-park-bitrix-failure-containment`
2. `T-orange-park-explicit-contact-state`
3. `T-orange-park-critical-handoff-router`
4. `T-orange-park-n8n-error-reply`
5. `T-orange-park-response-matrix-tests`
6. `T-orange-park-language-parity`
7. `T-orange-park-slot-state-model`

## Files Audited

- `backend/app/services/webhook_message_service.py`
- `backend/app/services/ai_reply_orchestration_service.py`
- `backend/app/services/ai_reply_orchestration_coordinator.py`
- `backend/app/services/prompt_builder_service.py`
- `backend/app/services/customer_language_detection.py`
- `backend/app/services/greeting_policy_service.py`
- `backend/app/services/knowledge_retrieval_service.py`
- `backend/app/services/message_service.py`
- `backend/app/services/orange_park_bitrix_service.py`
- `backend/app/seed/orange_park_configuration.py`
- `backend/alembic/versions/0027_enable_orange_park_bitrix_leads.py`
- `docs/businesses/orange-park/01_business_profile_facts/orange_park_facts.md`
- `docs/businesses/orange-park/03_faq/orange_park_faq.md`
- `docs/businesses/orange-park/05_policies_and_rules/orange_park_ai_policies.md`
- `docs/businesses/orange-park/07_conversation_examples/orange_park_conversation_style_guide.md`
- `n8n/workflows/orange-park-telegram-mvp.json`
- Orange Park-related backend and workflow tests.

## Git Status At Audit Start

The worktree was already dirty before this report. Existing modified/untracked
Orange Park implementation files were treated as the current runtime and were
not reverted. This audit adds only:

```text
tasks/in-progress/T-orange-park-response-scenario-audit.md
```

No commit or push was performed.

## Verification

Focused current-tree tests:

```text
53 passed, 1 warning
```

Command:

```text
cd backend
.venv/bin/pytest \
  tests/test_webhook_message_service.py \
  tests/test_orange_park_telegram_workflow.py \
  tests/test_orange_park_bitrix_service.py \
  tests/test_orange_park_configuration_seed.py
```

`git diff --check` for this report passed.

Final `git status --short --branch`:

```text
## stabilization/runtime-baseline...origin/stabilization/runtime-baseline
 M backend/app/core/config.py
 M backend/app/services/webhook_message_service.py
 M backend/tests/test_e2_observability_continuity.py
 M backend/tests/test_webhook_message_service.py
 M docker-compose.yml
 M docs/businesses/orange-park/05_policies_and_rules/orange_park_ai_policies.md
 M docs/businesses/orange-park/07_conversation_examples/orange_park_conversation_style_guide.md
?? backend/alembic/versions/0027_enable_orange_park_bitrix_leads.py
?? backend/app/services/orange_park_bitrix_service.py
?? backend/tests/test_orange_park_bitrix_service.py
?? docs/interview/
?? tasks/done/T-bcb-separate-ba-telegram-bot-plan.md
?? tasks/in-progress/T-orange-park-bitrix-contact-lead.md
?? tasks/in-progress/T-orange-park-contact-flow-and-metadata-diagnostics.md
?? tasks/in-progress/T-orange-park-customer-facing-wording.md
?? tasks/in-progress/T-orange-park-response-scenario-audit.md
```
> Historical audit only. Superseded by Orange Park Dialog Engine v3. The
> response mechanisms documented below are no longer active.
