# Orange Park Full Configuration Trace

Read-only trace captured on 2026-06-12.

Scope:

```text
docs/businesses/orange-park/
↓
backend/app/seed/orange_park_configuration.py
↓
PostgreSQL
↓
TenantBusinessProfile
TenantAIProfile
TenantKnowledgeSource
TenantChannelSettings
↓
AI Configuration Service
Knowledge Retrieval Service
Prompt Builder Service
AI Gateway Service
```

Validation conditions:

- No seed was run.
- No PostgreSQL write was issued. All DB inspection used `BEGIN TRANSACTION READ ONLY` and `ROLLBACK`.
- No backend, n8n, source document, configuration, or runtime file was changed.
- No commit or push was performed.
- The worktree already contained uncommitted Orange Park changes before this report was created. This report traces that working-tree state and the independently active DB state.

# 1. Source documents

## 1.1 Inventory

| Path | Purpose | Contact collection logic | Language rules | Manager handoff rules |
|---|---|---:|---:|---:|
| `docs/businesses/orange-park/01_business_profile_facts/.gitkeep` | Empty-directory placeholder. | No | No | No |
| `docs/businesses/orange-park/01_business_profile_facts/orange_park_facts.md` | Stable/checkable business facts extracted from the client PDF, plus unstable-data warnings. | Yes. Lines 308-317 say to collect contact details for unstable requests. No exact contact form. | No customer-language selection rules. Source content is mostly Russian with Ukrainian names. | Yes. Lines 254-278 and 308-317 require manager confirmation/handoff for unstable data. |
| `docs/businesses/orange-park/02_ai_behavior_and_sales_materials/.gitkeep` | Empty-directory placeholder. | No | No | No |
| `docs/businesses/orange-park/02_ai_behavior_and_sales_materials/orange_park_sales_materials.md` | Sales positioning, response style, qualification, contact collection, and CTA/handoff guidance. | Yes. Current working tree uses native Telegram contact sharing; key lines 157-162 and 169-177. | Yes. Ukrainian default and latest-message language rules are present in the behavior sections. | Yes. Dedicated manager-handoff triggers and exact handoff wording. |
| `docs/businesses/orange-park/03_faq/.gitkeep` | Empty-directory placeholder. | No | No | No |
| `docs/businesses/orange-park/03_faq/orange_park_faq.md` | Client-facing FAQ draft and FAQ-level AI usage rules. | Yes. Lines 26-29 require native Telegram contact before handoff. | Yes. Lines 16-19 define Ukrainian default, latest-message mirroring, English restrictions, and no language mixing. | Yes. Lines 24-31 and section `Manager handoff` at lines 205-221. |
| `docs/businesses/orange-park/04_prices_and_availability/.gitkeep` | Empty-directory placeholder. | No | No | No |
| `docs/businesses/orange-park/04_prices_and_availability/orange_park_prices_and_availability.md` | Time-sensitive prices, inventory, promotions, financing claims, conflicts, and manager-review checklist. | Yes. Line 24 says to collect name, phone, desired property, budget, payment route, and preferred channel. Line 185 still suggests typing an “удобный номер телефона”. | Only lead-field language classification at line 245; no response-language policy. | Yes. Most exact/current commercial data requires manager confirmation. |
| `docs/businesses/orange-park/05_policies_and_rules/.gitkeep` | Empty-directory placeholder. | No | No | No |
| `docs/businesses/orange-park/05_policies_and_rules/orange_park_ai_policies.md` | Telegram MVP policy boundary and authoritative behavior constraints. | Yes. Current working tree requires native Telegram contact sharing and rejects the old manual form. | Yes. Dedicated `Language rules` section. | Yes. Exact triggers, prerequisites, and post-contact closing. |
| `docs/businesses/orange-park/06_promotions/.gitkeep` | Placeholder; there is no promotion source document. | No | No | No |
| `docs/businesses/orange-park/07_conversation_examples/.gitkeep` | Empty-directory placeholder. | No | No | No |
| `docs/businesses/orange-park/07_conversation_examples/orange_park_conversation_style_guide.md` | Derived conversation behavior, qualification, safe examples, and transcript exclusions. | Yes. Current working tree uses native Telegram contact sharing; lines 93-109 and examples at 229-249. | Yes. Lines 73-88 define greeting and latest-message language behavior. | Yes. Handoff triggers, exact button wording, and exact closing. |
| `docs/businesses/orange-park/07_conversation_examples/orange_park_manager_chats_transcript.md` | Raw, redacted manager-chat transcription used only to derive style/qualification patterns. | Yes, descriptively. Lines 1028-1041 list data a bot could collect, including phone/Telegram username. | No normative language policy. It contains naturally mixed Ukrainian/Russian conversations. | Yes, descriptively. Lines 1017-1055 summarize manager escalation patterns and prohibited bot confirmations. |

## 1.2 Current source hashes

These use the seed's exact hashing method (`read_text(...).strip()` followed by SHA-256):

| File | SHA-256 |
|---|---|
| `01_business_profile_facts/orange_park_facts.md` | `19b4cdb3318c7afe645dfa8af2570b72fc673c9c9957fefb87c719d9227c8f77` |
| `02_ai_behavior_and_sales_materials/orange_park_sales_materials.md` | `7a8affbdfceb5f3b0983346cbd02fcac9230357792e0d23c628c4c30d897ee06` |
| `03_faq/orange_park_faq.md` | `beeefbc4a65ce9bca39c7e7bb10fd0c05b7aa948dbc3391c091398fed07371eb` |
| `04_prices_and_availability/orange_park_prices_and_availability.md` | `43650604e3fb5d65d767588c70802fcf8d304f8c98ad48ed261b43ed5dabd16c` |
| `05_policies_and_rules/orange_park_ai_policies.md` | `9fe41dd4fb0f88a41d08d75de4d3263db7023cb2937b756e6651934cbc6386d6` |
| `07_conversation_examples/orange_park_conversation_style_guide.md` | `910cce18e98c46a033784191775bddee71e8f7b886df22554264422bfca754a9` |
| `07_conversation_examples/orange_park_manager_chats_transcript.md` | `a4936ae64cfbfb3d8e0af3ed3a46306a9933d06c89af309dd6091a6c86475003` |

## 1.3 Seed inclusion boundary

`orange_park_configuration.py:177-186` loads exactly six documents:

```text
facts
sales_materials
ai_policies
faq
prices_availability
conversation_style
```

Not loaded by the seed:

- `06_promotions/` because it contains no source document.
- `orange_park_manager_chats_transcript.md`; the style guide is loaded instead.
- `.gitkeep` placeholders.
- The intake PDF directly.

# 2. Seed mapping

Source: `backend/app/seed/orange_park_configuration.py`.

## 2.1 Identity and scope

Lines 21-28:

```text
tenant.slug = orange-park
tenant.name = Orange Park
business.external_id = orange-park
business.name = Orange Park / ЖК Orange Park
business.business_type = real_estate
business.language = uk
business.timezone = Europe/Kyiv
channel = telegram
```

The seed reads documents before row creation/update (`lines 90-166`) and scopes profile/settings/knowledge lookups with both `tenant_id` and `business_id`.

## 2.2 TenantBusinessProfile exact mapping

Seed lines 269-352:

| DB field | Seed source/value |
|---|---|
| `id` | New UUID only when row does not exist. |
| `tenant_id` | Orange Park tenant ID. |
| `business_id` | Orange Park business ID. |
| `business_description` | `_business_description(facts)` (`lines 810-884`): a generated behavior preamble followed by the entire current `orange_park_facts.md` text. |
| `services` | `_orange_park_services()` (`lines 887-930`): residential apartment types, commercial-premises flag, White Box items, and manager-confirmation categories. |
| `pricing` | Policy forbidding live/current price or discount claims plus pointer to the pricing knowledge row. |
| `working_hours` | `None`. |
| `target_audience` | `Apartment buyers, families, investors, and commercial premises buyers interested in Orange Park.` |
| `business_limitations` | Generated long-form behavior policy. Current seed text requires native Telegram contact sharing, no manual phone form, missing-name-only follow-up, and no external CRM lead mention. |
| `city` | `Kriukivshchyna` |
| `region` | `Kyiv Oblast` |
| `country` | `Ukraine` |
| `metadata` | Seed/category/stage/business external ID plus `orange_park_facts.md` path and SHA-256. |

Important duplication: contact, language, repetition, and handoff behavior is embedded in both `business_description` and `business_limitations`, although this table is nominally the business-facts layer.

## 2.3 TenantAIProfile exact mapping

Seed lines 355-504:

| DB field | Seed source/value |
|---|---|
| `profile_name` | `Orange Park Telegram MVP` |
| `tone` | `professional, consultative, friendly` |
| `response_style` | `docs first; 1-3 short; handoff only unstable; one question; no loops` |
| `language` | `uk` |
| `ask_for_name` | `true` |
| `ask_for_phone` | `true` |
| `ask_for_email` | `false` |
| `handoff_enabled` | `true` |
| `handoff_keywords` | менеджер, консультация/консультація, цена/ціна, наличие/наявність, скидка/знижка, єоселя, кредит, рассрочка/розтермінування, перегляд, відеоогляд/видеообзор, бронь/бронювання. |
| `forbidden_promises` | Exact price/availability/booking/discount/financing/legal/payment constraints plus repetition/contact-flow constraints. |
| `fallback_response` | `Уточніть, будь ласка, що саме вас цікавить: квартира, комерційне приміщення чи умови придбання?` |
| `metadata` | Source hashes for sales materials, AI policies, and conversation style; `telegram_only_mvp=true`; `lead_creation_enabled=false`; complete `behavior_rules` array. |

Current seed `metadata.behavior_rules` has 46 rules. It replaces the prior manual phone/name form with native Telegram contact-button rules.

## 2.4 TenantKnowledgeSource exact mapping

Seed lines 122-166 and 562-613:

| `source_type` | `title` | Content mapping | Tags |
|---|---|---|---|
| `faq` | `Orange Park FAQ` | Entire current `orange_park_faq.md`. | `faq`, `orange_park`, `telegram_mvp` |
| `pricing` | `Orange Park Prices And Availability - Manager Confirmed Only` | Entire current `orange_park_prices_and_availability.md`. | `pricing`, `availability`, `requires_manager_confirmation`, `time_sensitive`, `orange_park`, `telegram_mvp` |
| `conversation_style` | `Orange Park Conversation Style Guide` | Generated runtime summary (`lines 616-689`) + separator + entire current style guide. | `conversation_style`, `ai_behavior`, `qualification`, `manager_handoff`, `orange_park`, `telegram_mvp`, `not_factual_knowledge` |

Every row gets `is_active=true` and metadata with source path/hash, source type, manager-confirmation flag, and time-sensitive flag.

There is no separate knowledge row for:

- facts;
- sales materials;
- AI policies;
- promotions;
- raw manager transcript.

Facts are embedded in `TenantBusinessProfile.business_description`. Sales materials and policies contribute only via AI-profile metadata/source lineage. The style guide is duplicated into both AI-profile lineage and a knowledge row.

## 2.5 TenantChannelSettings exact mapping

Seed lines 507-559:

```json
{
  "channel": "telegram",
  "response_style": "concise",
  "max_response_length": 900,
  "allow_emojis": false,
  "allow_links": false,
  "metadata": {
    "stage": "telegram_only_mvp",
    "credential_storage": "external_runtime_only",
    "default_start_language": "uk",
    "start_greeting": "Добрий день! 👋\n\nЯ AI-асистент ЖК Orange Park.\n\nМожу допомогти з інформацією про комплекс, квартири, комерційні приміщення та умови придбання, а також передати ваш запит менеджеру.\n\nЩо вас цікавить?\n🏡 Квартира\n🏢 Комерційне приміщення\n💳 Умови покупки / розтермінування"
  }
}
```

# 3. Active DB state

Read-only query scope:

```text
tenant_id   = 7b09f9ce-a1c6-4189-9ace-73e4e8176a3e
tenant.slug = orange-park
business_id = d14a1161-292c-4f1d-b0b2-2034f3e2e30d
business.external_id = orange-park
```

Row counts:

```text
tenant_business_profiles: 1
tenant_ai_profiles: 1
tenant_knowledge_sources: 3
tenant_channel_settings: 1
```

## 3.1 TenantBusinessProfile

```yaml
id: f80b34e6-9e09-4e1f-a6b8-42ac70fdcd15
tenant_id: 7b09f9ce-a1c6-4189-9ace-73e4e8176a3e
business_id: d14a1161-292c-4f1d-b0b2-2034f3e2e30d
created_at: 2026-06-10 11:10:28.091
updated_at: 2026-06-11 22:16:40.971907
city: Kriukivshchyna
region: Kyiv Oblast
country: Ukraine
working_hours: null
target_audience: Apartment buyers, families, investors, and commercial premises buyers interested in Orange Park.
pricing:
  policy: Use stable documented pricing rules and purchase-program facts first. Do not provide live prices or active discounts; manager confirmation is required for exact/current amounts.
  source: See TenantKnowledgeSource pricing row for time-sensitive extracted claims.
services:
  residential_apartments:
    types: [1-room, 2-room, 3-room, 4-room, two-level, patio apartments]
    availability_policy: manager_confirmation_required
  commercial_premises:
    available_in_source_materials: true
    availability_policy: manager_confirmation_required
  white_box_completion:
    included_in_source_materials: true
    details: [floor screed, plastered walls, energy-efficient windows, entrance doors, individual heating, gas boiler, meters]
  manager_consultation:
    required_for: [price, availability, discount, installment, єОселя, PrivatBank credit, housing voucher, commercial premises, booking, legal details]
metadata:
  seed: orange_park_configuration
  stage: telegram_only_mvp
  category: tenant_business_profile
  business_external_id: orange-park
  source_document:
    path: docs/businesses/orange-park/01_business_profile_facts/orange_park_facts.md
    sha256: 19b4cdb3318c7afe645dfa8af2570b72fc673c9c9957fefb87c719d9227c8f77
```

`business_description` contains:

1. An older generated Orange Park behavior preamble.
2. The full factual document snapshot beginning `# Orange Park — Factual Business Data`.

The active generated preamble contains the old manual flow:

```text
- If the customer agrees to handoff but has not sent a phone number, ask for the phone number; do not say the request was passed yet.
- Never say request passed to manager before phone, first name, and last name are collected. If phone is missing, ask only for phone. If phone is provided but name is missing, ask only for first and last name.
- Short handoff intent ... reply only: "Добре. Напишіть, будь ласка, номер телефону — менеджер зв’яжеться з вами."
- Contact requests ... reply only: "Залиште, будь ласка, ваш номер телефону — менеджер зв’яжеться з вами напряму."
- Russian contact form: "Пожалуйста, оставьте данные в таком формате:\n\nИмя:\nФамилия:\nТелефон:"
- Ukrainian contact form: "Будь ласка, залиште дані у такому форматі:\n\nІм'я:\nПрізвище:\nТелефон:"
- If the customer already sent a phone number in clearly Russian context, reply: "Спасибо, номер получил. Напишите, пожалуйста, имя и фамилию."
- If the customer already sent a phone number in Ukrainian/default context, reply: "Дякую, номер отримав. Напишіть, будь ласка, ім'я та прізвище."
- If customer says they are waiting for manager call, reply only: "Дякую. Запит передано менеджеру. Очікуйте дзвінок."
- After phone is collected, close with concise wording like: "Дякую. Запит передано менеджеру. Очікуйте дзвінок."
```

The full embedded facts snapshot remains in this DB cell. Its recorded source hash (`19b4...`) matches the current facts file under the seed's hashing method. The generated behavior preamble around those facts is older than the current seed.

`business_limitations` is also the older manual flow. Exact contact-related tail:

```text
Do not say the request was passed or thank for a phone number before the customer actually provides a phone number. If customer says they are waiting for the manager call, reply only: Дякую. Запит передано менеджеру. Очікуйте дзвінок. If customer agrees to handoff with short intent like давай, з'єднуй, так, ок, or добре, ask only for phone. If customer asks for phone/contact details and no official Orange Park contact is present in the current business context, ask the customer to leave their phone; do not invent contacts. Never repeat the same refusal or manager-confirmation loop twice. Orange Park Telegram stage 1 collects structured contact data before manager handoff: first_name, last_name, phone, Telegram id or username when available, and interest summary. If phone is already provided, ask only for missing first and last name. Do not create or mention external CRM leads.
```

## 3.2 TenantAIProfile

```yaml
id: 4ff482a0-d2eb-4748-9800-b0e4af82d525
tenant_id: 7b09f9ce-a1c6-4189-9ace-73e4e8176a3e
business_id: d14a1161-292c-4f1d-b0b2-2034f3e2e30d
created_at: 2026-06-10 11:10:28.091
updated_at: 2026-06-11 22:16:40.971907
profile_name: Orange Park Telegram MVP
tone: professional, consultative, friendly
response_style: docs first; 1-3 short; handoff only unstable; one question; no loops
language: uk
ask_for_name: true
ask_for_phone: true
ask_for_email: false
handoff_enabled: true
fallback_response: "Уточніть, будь ласка, що саме вас цікавить: квартира, комерційне приміщення чи умови придбання?"
handoff_keywords:
  - менеджер
  - консультация
  - консультація
  - цена
  - ціна
  - наличие
  - наявність
  - скидка
  - знижка
  - єоселя
  - кредит
  - рассрочка
  - розтермінування
  - перегляд
  - відеоогляд
  - видеообзор
  - бронь
  - бронювання
forbidden_promises:
  - exact price
  - apartment availability
  - reservation or booking
  - active discount
  - credit approval
  - єОселя approval
  - housing voucher approval
  - legal guarantees
  - live pricing
  - live availability
  - external CRM lead creation
  - payment instructions
  - bank or card details
  - tax, notary, registration, or service-fee amounts
  - repeating address or location after it was already answered
  - restating location when customer gives budget, area, payment, or handoff criteria
  - verbose manager handoff wording
  - open-ended closing after phone is collected
  - saying request was passed before phone number is collected
  - thanking for a phone number before the customer provides one
  - open-ended extra sentence when customer is waiting for manager call
  - long explanation after short handoff intent like давай or з'єднуй
  - repeating the same manager-confirmation or refusal block twice
  - inventing Orange Park phone, manager contact, or contact details
  - giving manager phone when official contact is absent from business context
  - English reply after Ukrainian or Russian phone number turn
  - saying manager request was passed before first name, last name, and phone are collected
  - external CRM lead creation or external CRM mention in Orange Park Telegram stage 1
```

Active `metadata.behavior_rules`, complete and untruncated:

1. `Ukrainian /start and first greeting by default.`
2. `Default language is Ukrainian for Orange Park.`
3. `Always reply in the language of the customer's latest message; conversation history must not override latest-message language.`
4. `Never switch to Russian because of conversation history.`
5. `If the customer asks 'Чому ти на російській?', apologize briefly in Ukrainian and continue in Ukrainian.`
6. `Mirror Russian only when the customer's latest message is clearly Russian.`
7. `Mirror English only when the customer's latest message is clearly English.`
8. `Never output English unless customer writes English.`
9. `Never mix languages or use hybrid words.`
10. `Use documentation first: Business Context Source Of Truth, then Tenant Knowledge Sources.`
11. `If stable documentation contains the answer, answer from documentation before manager handoff.`
12. `Do not say manager will confirm when stable documentation already answers the question.`
13. `Stable documented topics include project description, location, transport, apartment types, White Box completion, infrastructure, territory and security, construction technology, commercial premises, existence of purchase programs, and general purchase process.`
14. `Use manager handoff only for exact price, exact availability, discounts, booking, active installment conditions, current financing terms, legal guarantees, or other time-sensitive data.`
15. `Answer pattern: answer from documentation, ask one qualification question, then use manager handoff only if unstable information is requested.`
16. `Answer the immediate question first, then ask one useful qualification question.`
17. `Keep Telegram replies concise: 1-3 short sentences.`
18. `Behave like a helpful consultant first, not a lead form.`
19. `Trust first, qualification second, manager handoff third.`
20. `Do not ask for a phone number at the beginning of the conversation.`
21. `For general Orange Park questions, answer from available business context and do not ask for phone.`
22. `General questions about the project, location, infrastructure, territory, security, apartment types, White Box, commercial premises, or purchase process must be answered first without asking for phone.`
23. `When customer asks for price, explain that current exact price is manager-confirmed, give safe general context if available, and ask for contact only after answering.`
24. `Collect phone only when customer asks for price, availability, discount, booking, viewing, financing, єОселя, credit, manager consultation, or after basic needs are understood and handoff clearly adds value.`
25. `Do not repeatedly ask for phone if the customer ignores the request; continue helping and ask one useful qualification question.`
26. `Use conversation history to avoid repeating facts.`
27. `If address or location was already answered, do not repeat it when customer gives budget, area, payment, or handoff criteria.`
28. `If customer gives new buying criteria, respond only to those criteria.`
29. `Do not say request was passed and do not thank for phone before customer provides a phone number.`
30. `Never say request passed to manager before phone, first name, and last name are collected.`
31. `If phone is missing, ask only for phone.`
32. `If phone is provided but name is missing, ask only for first and last name.`
33. `After phone, first name, and last name are collected, reply shortly: Дякую. Запит передано менеджеру. Очікуйте дзвінок.`
34. `If customer says they are waiting for manager call, reply only: Дякую. Запит передано менеджеру. Очікуйте дзвінок.`
35. `Do not overuse manager-confirmation wording.`
36. `After phone is collected, use concise closing: Дякую. Запит передано менеджеру. Очікуйте дзвінок.`
37. `Short handoff intent such as давай, з'єднуй, так, ок, or добре means: ask only for phone if phone is not collected.`
38. `Contact requests such as номер телефону, дай контакти, дай дані, номер, or телефон менеджера mean: if no official contact exists in current business context, reply exactly: Залиште, будь ласка, ваш номер телефону — менеджер зв’яжеться з вами напряму.`
39. `Never invent Orange Park phone numbers or manager contacts.`
40. `Never repeat the same refusal or manager-confirmation loop twice.`
41. `Orange Park Telegram stage 1 contact form in Russian: Пожалуйста, оставьте данные в таком формате:\n\nИмя:\nФамилия:\nТелефон:`
42. `Orange Park Telegram stage 1 contact form in Ukrainian: Будь ласка, залиште дані у такому форматі:\n\nІм'я:\nПрізвище:\nТелефон:`
43. `If phone is already provided in clearly Russian context, reply: Спасибо, номер получил. Напишите, пожалуйста, имя и фамилию.`
44. `If phone is already provided in Ukrainian/default context, reply: Дякую, номер отримав. Напишіть, будь ласка, ім'я та прізвище.`
45. `Minimum Orange Park stage 1 lead fields: first_name, last_name, phone, telegram_id or telegram_username when available, and interest summary.`
46. `Do not say the manager request was passed until first name, last name, and phone are collected.`
47. `Do not create or mention external CRM leads in Orange Park Telegram stage 1.`

Active AI-profile source hashes are stale relative to the current working tree:

| Source | Active DB hash | Current file hash |
|---|---|---|
| Sales materials | `550be2d9e2a07d5820bcf30d9651a73cc5155fedf0be90588eade39214dba2be` | `7a8affbdfceb5f3b0983346cbd02fcac9230357792e0d23c628c4c30d897ee06` |
| AI policies | `e8d1e72d40b54cb87b23f670ebebde649d3d78c6e49b8eb666f57bd5b1c35637` | `9fe41dd4fb0f88a41d08d75de4d3263db7023cb2937b756e6651934cbc6386d6` |
| Conversation style | `6e39e873eaf4ba0b481b62aa28498da4a6dca77d58db79657f65f27bcec1d642` | `910cce18e98c46a033784191775bddee71e8f7b886df22554264422bfca754a9` |

## 3.3 TenantKnowledgeSource

All active rows:

| ID | `source_type` | `title` | Active | Content chars | Created | Updated | Recorded source SHA-256 |
|---|---|---|---:|---:|---|---|---|
| `9c53e80b-a04d-4855-b6a3-cb16f32583df` | `faq` | `Orange Park FAQ` | true | 10,311 | 2026-06-10 11:10:28.091 | 2026-06-11 21:32:37.400478 | `4bdf190c8bdb1198308276db36c1cd77409ba49be536bcd73e350795353e0871` |
| `dae6868f-2524-4efd-b2cc-98652ff02618` | `pricing` | `Orange Park Prices And Availability - Manager Confirmed Only` | true | 11,900 | 2026-06-10 11:10:28.091 | 2026-06-10 11:10:28.091 | `43650604e3fb5d65d767588c70802fcf8d304f8c98ad48ed261b43ed5dabd16c` |
| `0d797892-8246-4835-8409-6cf673ee8453` | `conversation_style` | `Orange Park Conversation Style Guide` | true | 25,971 | 2026-06-10 13:14:49.367711 | 2026-06-11 22:16:40.971907 | `736f4b7aab3d49265640b9dbd60941b5695b403318f9dcdcb04cb2541b3ef4ff` |

Tags:

```text
faq:
  [faq, orange_park, telegram_mvp]

pricing:
  [pricing, availability, requires_manager_confirmation, time_sensitive, orange_park, telegram_mvp]

conversation_style:
  [conversation_style, ai_behavior, qualification, manager_handoff, orange_park, telegram_mvp, not_factual_knowledge]
```

Hash comparison:

- `faq` differs from the current FAQ.
- `pricing` matches the current prices/availability document.
- `conversation_style` metadata hashes the generated runtime document rather than the raw style-guide file. The active generated hash is `736f...`; the current generated runtime hash would be `0c5c193926edb064b53b53f4b2f880f5f6c114cdf69964a0fbb00162f5db5367`, so it differs.

The active `conversation_style` content includes the generated old runtime summary and the old style-guide snapshot, so obsolete manual forms appear twice in that single DB cell.

## 3.4 TenantChannelSettings

```yaml
id: 27536a03-2d83-47dc-9c15-0a91f89f7fbc
tenant_id: 7b09f9ce-a1c6-4189-9ace-73e4e8176a3e
business_id: d14a1161-292c-4f1d-b0b2-2034f3e2e30d
channel: telegram
response_style: concise
max_response_length: 900
allow_emojis: false
allow_links: false
created_at: 2026-06-10 11:10:28.091
updated_at: 2026-06-11 21:32:37.400478
metadata:
  stage: telegram_only_mvp
  credential_storage: external_runtime_only
  default_start_language: uk
  start_greeting: |
    Добрий день! 👋

    Я AI-асистент ЖК Orange Park.

    Можу допомогти з інформацією про комплекс, квартири, комерційні приміщення та умови придбання, а також передати ваш запит менеджеру.

    Що вас цікавить?
    🏡 Квартира
    🏢 Комерційне приміщення
    💳 Умови покупки / розтермінування
```

# 4. Conflict detection

Search scope:

- Current Orange Park documents.
- Current Orange Park seed.
- Active Orange Park rows in the four requested tables.
- Runtime backend and n8n files where the searched transport tokens occur.

## 4.1 Exact phrases absent from current documents/seed but present in active DB

### `Напишіть, будь ласка, номер телефону`

| Layer | Location | Exact text |
|---|---|---|
| DB | `tenant_business_profiles.business_description`, DB cell line 20 | `- Short handoff intent such as "давай", "з'єднуй", "так", "ок", or "добре" means: if no phone was collected, reply only: "Добре. Напишіть, будь ласка, номер телефону — менеджер зв’яжеться з вами."` |
| DB | `tenant_knowledge_sources`, `conversation_style` content lines 42 and 199 | `- Treat short handoff intent ... If no phone was collected, reply only: "Добре. Напишіть, будь ласка, номер телефону — менеджер зв’яжеться з вами."` |
| DB | Same row, content line 79 | `- "Зрозуміло: ... Напишіть, будь ласка, номер телефону - передам запит."` |
| DB | Same row, content line 80 | `- "Добре. Напишіть, будь ласка, номер телефону — менеджер зв’яжеться з вами."` |
| DB | Same row, content line 328 | `"Зрозуміло: ... Напишіть, будь ласка, номер телефону - передам запит."` |

Current document/seed matches: none.

### `Будь ласка, залиште дані у такому форматі`

| Layer | Location | Exact text |
|---|---|---|
| DB | `tenant_ai_profiles.metadata.behavior_rules[42]` | `Orange Park Telegram stage 1 contact form in Ukrainian: Будь ласка, залиште дані у такому форматі:\n\nІм'я:\nПрізвище:\nТелефон:` |
| DB | `tenant_business_profiles.business_description`, DB cell line 24 | `- Ukrainian contact form: "Будь ласка, залиште дані у такому форматі:\n\nІм'я:\nПрізвище:\nТелефон:"` |
| DB | `tenant_knowledge_sources`, `conversation_style` content lines 54, 87, 203, 338 | The same Ukrainian manual-form heading, once/twice in generated runtime content and once/twice in the stored style-guide snapshot. |

Current document/seed matches: none.

### `Ім'я:`, `Прізвище:`, `Телефон:`

These are components of the same active manual forms.

| Layer | Location | Exact text |
|---|---|---|
| DB | `tenant_ai_profiles.metadata.behavior_rules[41]` | `Пожалуйста, оставьте данные в таком формате:\n\nИмя:\nФамилия:\nТелефон:` |
| DB | `tenant_ai_profiles.metadata.behavior_rules[42]` | `Будь ласка, залиште дані у такому форматі:\n\nІм'я:\nПрізвище:\nТелефон:` |
| DB | `tenant_business_profiles.business_description`, lines 23-24 | The Russian and Ukrainian manual forms above. |
| DB | `tenant_knowledge_sources`, `conversation_style` content lines 53-58, 86-91, 202-203, 336-342 | Repeated Russian/Ukrainian manual form fields in runtime summary and style-guide snapshot. |

Current document/seed matches for these exact labels: none.

### `If phone is missing`

| Layer | Location | Exact text |
|---|---|---|
| DB | `tenant_ai_profiles.metadata.behavior_rules[31]` | `If phone is missing, ask only for phone.` |
| DB | `tenant_business_profiles.business_description`, line 19 | `... If phone is missing, ask only for phone. If phone is provided but name is missing, ask only for first and last name.` |
| DB | `tenant_knowledge_sources`, `conversation_style` content lines 46 and 196 | `- If phone is missing, ask only for phone.` |

Current document/seed matches: none.

### `If phone is already provided`

| Layer | Location | Exact text |
|---|---|---|
| DB | `tenant_ai_profiles.metadata.behavior_rules[43]` | `If phone is already provided in clearly Russian context, reply: Спасибо, номер получил. Напишите, пожалуйста, имя и фамилию.` |
| DB | `tenant_ai_profiles.metadata.behavior_rules[44]` | `If phone is already provided in Ukrainian/default context, reply: Дякую, номер отримав. Напишіть, будь ласка, ім'я та прізвище.` |
| DB | `tenant_business_profiles.business_description`, line 22 | `... If phone is already provided, ask only for missing first and last name.` |
| DB | `tenant_business_profiles.business_limitations`, single text line | `... If phone is already provided, ask only for missing first and last name.` |

Current document/seed matches: none.

### `ask only for phone`

| Layer | Location | Exact text |
|---|---|---|
| DB | `tenant_ai_profiles.metadata.behavior_rules[31]` | `If phone is missing, ask only for phone.` |
| DB | `tenant_ai_profiles.metadata.behavior_rules[37]` | `Short handoff intent ... means: ask only for phone if phone is not collected.` |
| DB | `tenant_business_profiles.business_description`, line 19 | `... If phone is missing, ask only for phone. ...` |
| DB | `tenant_business_profiles.business_limitations` | `... ask only for phone. ...` |
| DB | `tenant_knowledge_sources`, `conversation_style` content lines 46 and 196 | `- If phone is missing, ask only for phone.` |

Current document/seed matches: none.

### `ask only for first and last name`

| Layer | Location | Exact text |
|---|---|---|
| DB | `tenant_ai_profiles.metadata.behavior_rules[32]` | `If phone is provided but name is missing, ask only for first and last name.` |
| DB | `tenant_business_profiles.business_description`, line 19 | `... If phone is provided but name is missing, ask only for first and last name.` |
| DB | `tenant_knowledge_sources`, `conversation_style` content lines 47 and 197 | `- If phone is provided but name is missing, ask only for first and last name.` |

Current document/seed matches: none.

## 4.2 Native Telegram contact phrase

Searched phrase: `Поділитися номером`.

Current source/seed matches:

| Layer | Exact location(s) | Exact text |
|---|---|---|
| Document | `orange_park_sales_materials.md:157,161,162,177` | `Для зв'язку з менеджером, будь ласка, натисніть кнопку «📱 Поділитися номером».` |
| Document | `orange_park_faq.md:28` | Same exact CTA. |
| Document | `orange_park_ai_policies.md:85,86,145` | Same exact CTA. |
| Document | `orange_park_conversation_style_guide.md:102,103,128,160,229,233,241,261,265` | Same CTA, standalone or appended to a safe response. |
| Seed | `orange_park_configuration.py:470,478,658,659,684,685,859,864` | Same CTA in AI-profile metadata, runtime knowledge summary, examples, and business-profile preamble. |
| Backend runtime | `backend/app/services/webhook_message_service.py:103,2623` | CTA constant and metadata `button_text: "📱 Поділитися номером"`. |
| n8n transport | `n8n/workflows/orange-park-telegram-mvp.json:81,110` | Telegram keyboard button text `📱 Поділитися номером`. |

Active DB matches: none. This phrase is absent from all four active Orange Park configuration table rows.

## 4.3 `request_contact`

| Layer | Exact location | Exact text |
|---|---|---|
| n8n transport | `n8n/workflows/orange-park-telegram-mvp.json:81` embedded Code node | `request_contact: true` |
| n8n transport | `n8n/workflows/orange-park-telegram-mvp.json:112` Telegram reply markup | `"request_contact": true` |

No current document, seed, backend configuration-table mapping, or active DB row contains `request_contact`.

## 4.4 New manager closing

Searched phrase: `Дякуємо. Запит передано менеджеру.`

Current source/seed/runtime matches:

| Layer | Exact location(s) | Exact text |
|---|---|---|
| Document | `orange_park_sales_materials.md:160,169,177` | `Дякуємо. Запит передано менеджеру. Очікуйте дзвінок.` |
| Document | `orange_park_ai_policies.md:84,92,147` | Same exact text. |
| Document | `orange_park_conversation_style_guide.md:101,109,245,249` | Same exact text. |
| Seed | `orange_park_configuration.py:317,473,474,476,665,668,687,688,879,882` | Same exact text in business profile, AI metadata, and knowledge runtime summary. |
| Backend runtime | `backend/app/services/webhook_message_service.py:106` | Same exact text. |

Active DB matches: none. Active DB uses `Дякую. Запит передано менеджеру. Очікуйте дзвінок.` instead.

# 5. Duplicate and contradictory rules

This section records conflicts only; it does not propose implementation.

## 5.1 Duplicated rules

1. Contact/handoff behavior is duplicated across:
   - sales materials;
   - FAQ usage rules;
   - AI policies;
   - conversation style guide;
   - generated `TenantBusinessProfile.business_description`;
   - `TenantBusinessProfile.business_limitations`;
   - `TenantAIProfile.metadata.behavior_rules`;
   - generated `conversation_style` knowledge runtime summary;
   - the appended style-guide snapshot in the same knowledge row.

2. Language behavior is duplicated in:
   - FAQ;
   - AI policies;
   - style guide;
   - business-description preamble;
   - AI-profile metadata.

3. The exact post-contact closing is duplicated multiple times within individual source files and again in multiple seed targets.

4. The active `conversation_style` DB row duplicates its old contact rules internally because it contains both a generated runtime summary and a full old style-guide snapshot.

5. Facts are present in the source document and copied in full into `TenantBusinessProfile.business_description`.

## 5.2 Conflicting rules

1. Current documents/seed require the native Telegram contact button. Active DB requires manual typed phone/name collection.

2. Current documents/seed say a manually typed phone must still be followed by the native Telegram contact button. Active DB says a typed phone counts as collected and then asks for missing name/surname.

3. Current documents/seed closing is:

   ```text
   Дякуємо. Запит передано менеджеру. Очікуйте дзвінок.
   ```

   Active DB closing is:

   ```text
   Дякую. Запит передано менеджеру. Очікуйте дзвінок.
   ```

4. Current policy says “If Telegram contact is missing, ask only to press the native Telegram contact button.” Active DB says “If phone is missing, ask only for phone.”

5. `orange_park_prices_and_availability.md:24,185` still instructs collection of a phone/contact and includes a response asking for an “удобный номер телефона”. That document is unchanged and remains inconsistent with the current native-button-only policy. It is active as the `pricing` knowledge row, although retrieval may or may not select the conflicting passage.

6. `orange_park_faq.md:211-217` says ordinary handoff data includes name and phone and says “Оставьте контакты”, while its AI usage rules at lines 26-29 specify the native Telegram contact button. The high-level and FAQ-answer wording are not identical.

7. `allow_emojis=false` in channel settings conflicts with the configured start greeting and contact button, both of which contain emoji.

8. `allow_links=false` is a channel rule, while general source material discusses contact links and website-like data. No official Orange Park link is currently mapped into the business profile.

## 5.3 Obsolete rules

Based on the current working-tree documents and seed, these active DB rules are obsolete:

- old Ukrainian and Russian manual contact forms;
- `If phone is missing, ask only for phone`;
- treating manually typed phone as collected;
- `Дякую...` singular closing;
- “ask only for phone” short-handoff response;
- old “leave your phone” official-contact fallback.

The obsolete text remains active in all of:

- `tenant_business_profiles.business_description`;
- `tenant_business_profiles.business_limitations`;
- `tenant_ai_profiles.metadata.behavior_rules`;
- `tenant_ai_profiles.forbidden_promises` wording;
- `tenant_knowledge_sources` conversation-style content.

## 5.4 Override and reachability behavior

1. Platform sections override tenant sections by prompt order:

   ```text
   platform_system
   task_instructions
   business_context_source_of_truth
   tenant_business_context
   tenant_behavior
   channel_rules
   knowledge
   conversation_history
   current_customer_message
   ```

2. Business-profile contact rules reach the prompt in `business_context_source_of_truth` because Prompt Builder emits `business_description` and `business_limitations`.

3. `TenantAIProfile.metadata.behavior_rules` is loaded by AI Configuration Service but is not emitted by `_build_tenant_behavior()` (`prompt_builder_service.py:475-491`). Therefore, the 47 behavior rules listed above do not directly enter the `tenant_behavior` prompt section.

4. `TenantAIProfile.fallback_response` is loaded into the DTO but is also not emitted by `_build_tenant_behavior()`.

5. `TenantChannelSetting.metadata.start_greeting` and `default_start_language` are loaded into DTO metadata but are not emitted by `_build_channel_rules()` (`lines 494-507`). Greeting behavior comes through the separate Greeting Policy path when resolved.

6. Knowledge is query-ranked and bounded to at most five snippets, 1,000 characters each, 4,000 characters total. A full knowledge row is never injected wholesale by Knowledge Retrieval Service.

7. Knowledge is ranked by simple token substring score over title + content. Equal scores fall back to `created_at`. Therefore, which conflicting knowledge text reaches AI depends on the current customer query and row order.

8. Prompt Builder variable-budget trimming order is:

   ```text
   knowledge
   conversation_history
   channel_rules
   tenant_business_context
   business_context_source_of_truth
   tenant_behavior
   ```

   This means duplicated business-profile behavior can survive after knowledge containing another version is trimmed.

9. The current backend service contains deterministic contact-flow constants and metadata outside the four configuration tables. These can control transport behavior independently of what the AI configuration says.

# 6. Final dependency graph

## 6.1 Stable business facts

```text
orange_park_facts.md
↓ _business_description(facts)
tenant_business_profiles.business_description
↓ AiConfigurationService._map_business_profile()
TenantBusinessContextConfig.business_description
↓ PromptBuilder._build_tenant_business_context()
business_context_source_of_truth
↓ AI Gateway OpenAI request mapping
AI
```

The complete facts file is embedded after a generated behavior preamble. The active DB contains an older facts snapshot/hash.

## 6.2 Services, audience, location, and limitations

```text
seed constants + orange_park_facts.md-derived policy
↓ _ensure_business_profile()
tenant_business_profiles.services/pricing/target_audience/
business_limitations/city/region/country
↓ AiConfigurationService
TenantBusinessContextConfig
↓ Prompt Builder
business_context_source_of_truth
↓ AI
```

`working_hours` is null and therefore omitted.

## 6.3 Tone and coarse AI flags

```text
seed constants
↓ _ensure_ai_profile()
tenant_ai_profiles.tone/response_style/language/
ask_for_name/ask_for_phone/ask_for_email/handoff_enabled/
handoff_keywords/forbidden_promises
↓ AiConfigurationService._map_ai_profile()
TenantBehaviorConfig
↓ PromptBuilder._build_tenant_behavior()
tenant_behavior
↓ AI
```

`fallback_response` and `metadata.behavior_rules` stop at the DTO and are not rendered into this section.

## 6.4 Detailed language rules

```text
sales materials + AI policies + style guide
↓ seed metadata.behavior_rules
tenant_ai_profiles.metadata
↓ AiConfigurationService loads and scrubs metadata
TenantBehaviorConfig.metadata
↓ Prompt Builder does not emit metadata
not directly present in tenant_behavior
```

Parallel active route:

```text
facts-derived generated behavior preamble
↓ tenant_business_profiles.business_description
↓ business_context_source_of_truth
↓ AI
```

Greeting-language route:

```text
TenantAIProfile.language = uk
↓ GreetingPolicyService default_language_code
↓ build_greeting_instruction_block()
task_instructions
↓ AI
```

## 6.5 Contact collection and manager handoff

Configuration route:

```text
sales materials / FAQ / AI policies / style guide
↓ current seed generated text and metadata
TenantBusinessProfile + TenantAIProfile + conversation_style knowledge
↓ Prompt Builder business context / behavior / retrieved knowledge
↓ AI
```

Active persisted route currently differs:

```text
older source/seed snapshot
↓ active DB manual phone/name rules
↓ business_context_source_of_truth + possible knowledge snippet
↓ AI
```

Deterministic backend/transport route:

```text
backend webhook contact-state logic
↓ response metadata.telegram_contact_request
↓ n8n Code node
↓ Telegram reply_markup
↓ request_contact: true
```

The `request_contact` transport flag does not originate from the four configuration tables.

## 6.6 FAQ

```text
orange_park_faq.md
↓ seed content copy
tenant_knowledge_sources
  source_type = faq
  title = Orange Park FAQ
↓ KnowledgeRetrievalService token ranking + truncation
knowledge
↓ AI
```

## 6.7 Prices and availability

```text
orange_park_prices_and_availability.md
↓ seed content copy
tenant_knowledge_sources
  source_type = pricing
  title = Orange Park Prices And Availability - Manager Confirmed Only
↓ KnowledgeRetrievalService
knowledge
↓ AI
```

The profile-level pricing policy also reaches `business_context_source_of_truth`, so manager-confirmation policy exists in two prompt sections.

## 6.8 Conversation style examples

```text
orange_park_conversation_style_guide.md
↓ _conversation_style_runtime_document()
generated runtime summary + full style guide
↓ tenant_knowledge_sources
  source_type = conversation_style
  title = Orange Park Conversation Style Guide
↓ KnowledgeRetrievalService
knowledge
↓ AI
```

The raw manager transcript does not enter the seed or DB.

## 6.9 Channel rules

```text
seed constants
↓ tenant_channel_settings telegram row
response_style/max_response_length/allow_emojis/allow_links
↓ AiConfigurationService._map_channel_setting()
TenantChannelRulesConfig
↓ PromptBuilder._build_channel_rules()
channel_rules
↓ AI
```

Channel metadata is not rendered by `_build_channel_rules()`.

## 6.10 End-to-end runtime

```text
PostgreSQL tenant configuration
  ├─ TenantBusinessProfile
  ├─ TenantAIProfile
  └─ TenantChannelSetting
        ↓
AiConfigurationService
        │
TenantKnowledgeSource
        ↓
KnowledgeRetrievalService
        │
Conversation history + current message + greeting policy
        ↓
PromptBuilderService
        ↓
AssembledPrompt
        ↓
AiGatewayService
        ↓
OpenAI
        ↓
AI reply
```

Final observation: the current repository source/seed state and active PostgreSQL state are different configuration versions. No action was taken to reconcile them.
