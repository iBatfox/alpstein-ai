# Orange Park Sales Scenarios

## Dialog Engine v3 state contract

Every state belongs to `dialog_engine_version=orange_park_v3`. Consume the
current `stage` before applying root intent routing. Do not infer active state
from stale conversation history.

```text
START
  -> about_project
  -> apartment_sales
  -> commercial_sales
  -> purchase_terms
  -> manager_contact
  -> unknown
```

Persist these explicit fields:

```text
dialog_engine_version
intent
stage
property_type
apartment_type
commercial_type
purpose
area_interest
budget_interest
purchase_path
contact_requested
contact_received
```

Only fill a field from the current customer reply when that field is expected
by the active stage or when the reply contains an explicit value. Preserve all
other valid fields while advancing the stage.

## Scenario map

| Intent | Initial stage | Expected replies | State to store | Next stage | Response pattern | Manager offer |
| --- | --- | --- | --- | --- | --- | --- |
| `about_project` | `qualification` | living, investment, apartment interest | `purpose`, then `property_type` | `apartment_type` or relevant root scenario | Stable project fact, one relevant advantage, one qualification question | Only for current facts, viewing, or direct request |
| `apartment_sales` | `apartment_type` | apartment type, area, purpose, purchase path | `property_type=apartment`, `apartment_type`, `area_interest`, `purpose`, `purchase_path` | `apartment_area` -> `apartment_purpose` -> `purchase_path` -> `manager_offer` | Confirm each consumed value and ask one next question | After useful qualification or when live price, availability, calculation, or viewing is needed |
| `commercial_sales` | `commercial_business_type` | business/use type, format or area, purpose | `property_type=commercial`, `commercial_type`, `area_interest`, `purpose` | `commercial_format` -> `commercial_purpose` -> `manager_offer` | Confirm business context and ask one next question | After useful qualification or for live premises, price, technical fit, or viewing |
| `purchase_terms` | `purchase_path` | full payment, installment, єОселя, bank financing, voucher | `purchase_path` | `manager_offer` | General explanation only, then ask whether a current calculation is needed | Offer after the path is known; request contact only after agreement |
| `manager_contact` | `awaiting_contact` | native contact share | `contact_requested=true`, then `contact_received=true` | `completed` | Ask for native Telegram contact, then confirm handoff | Immediate only under the contact rules below |
| `unknown` | `idle` | unsupported or ambiguous text | no inferred sales fields | stay `idle` or route from a new explicit intent | Ask which root topic is relevant | Do not offer from an idle short confirmation |

## Apartment state consumption

### Apartment type

- `1 кімнатна`, `1-кімнатна`, `однокімнатна`:
  `apartment_type=1-room`.
- `2 кімнатна`, `2-кімнатна`, `двокімнатна`:
  `apartment_type=2-room`.
- `3 кімнатна`, `3-кімнатна`, `трикімнатна`:
  `apartment_type=3-room`.
- `4 кімнатна`, `4-кімнатна`, `чотирикімнатна`:
  `apartment_type=4-room`.

After consuming the apartment type, keep `intent=apartment_sales`,
`property_type=apartment`, and advance to `stage=apartment_area`.

### Purpose

- `для проживання`, `для себе`, `жити`: `purpose=living`.
- `для інвестиції`, `інвестиція`, `під оренду`:
  `purpose=investment`.

A purpose reply consumes `qualification` or `apartment_purpose`; it must not
reset the dialog to `unknown/idle`. If apartment type is still missing, ask for
it. If type and purpose are known, continue to purchase-path qualification.

### Area

When `stage=apartment_area` and the customer provides a number, store it as
`area_interest`. Compare it only with approved non-live reference ranges. Do
not claim that a matching apartment is currently available.

For a 2-room apartment, the non-live reference range is `56-64 м²`. Confirm the
requested area as an interest and state that current availability requires
manager confirmation.

When apartment type and purpose are known, ask:

`Який спосіб придбання розглядаєте: повна оплата, розтермінування чи фінансування?`

Do not offer a manager merely because an apartment type, purpose, or area was
provided. Continue qualification unless the customer requests current price,
availability, a calculation, a viewing, or direct manager contact.

## Commercial state consumption

1. Store the business/use type as `commercial_type`.
2. Store an explicitly requested format or area as `area_interest`.
3. Store own business, rental, or investment intent as `purpose`.
4. After useful qualification, offer a manager for current premises, price,
   technical fit, or viewing.

Do not claim live premises or price and do not request contact before it is
useful.

## Manager contact rules

Set `contact_requested=true`, move to `stage=awaiting_contact`, and show the
native Telegram contact button only when:

- the customer directly asks for a manager, callback, or contact;
- the customer agrees while `stage=manager_offer` is active;
- exact price, current availability, a current calculation, or a viewing is
  needed;
- sales qualification has enough context for a useful handoff.

After a valid contact payload, set `contact_received=true`, move to
`stage=completed`, and confirm that the request was sent.

Do not trigger the contact button from idle replies such as `так`, `ок`,
`давай`, or `+`. They may accept a handoff only when `contact_requested=true`
or `stage=manager_offer` is active.

## Unknown and short-confirmation fallback

If there is no active state and the customer sends a short confirmation, do not
request contact. Reply:

`Підкажіть, будь ласка, що саме вас цікавить: квартира, комерційне приміщення чи умови придбання?`

Numeric messages fill only an explicitly active numeric slot. Unsupported text
must not create apartment, commercial, purchase, or contact state by inference.

## Platform observability boundary

The platform trace lifecycle for every business and channel is:

```text
request
  -> trace start
  -> dialog engine / AI
  -> response
  -> trace finish
```

The end-to-end platform message trace must cover every inbound message and
outbound response, including deterministic Dialog Engine replies, AI Gateway
replies, Telegram contact flow, and Bitrix success or failure. This lifecycle
applies to Telegram, Instagram, WhatsApp, website chat, and future channels.
Dialog Engine routing must not bypass the platform message-trace lifecycle.

Langfuse is the platform trace sink for these paths in every environment.
Configured public and secret keys are the required external-service
credentials; environment and feature-flag values must not disable tracing when
credentials are present. `PromptRun` and Langfuse are separate concerns:
`PromptRun` is created for AI execution, while deterministic replies must not
restore or fabricate a `PromptRun` merely to obtain tracing.
