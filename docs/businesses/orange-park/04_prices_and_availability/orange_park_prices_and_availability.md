# Orange Park — Prices And Availability Draft

Source materials:

- `docs/businesses/orange-park/00_intake/orange-park-client-source.pdf`
- `docs/businesses/orange-park/01_business_profile_facts/orange_park_facts.md`
- `docs/businesses/orange-park/02_ai_behavior_and_sales_materials/orange_park_sales_materials.md`

Purpose: pre-ingestion extraction of price, discount, availability, financing, and inventory-related claims for manager review.

Status: time-sensitive and manager-confirmed only. Do not use as production assistant context until manager review and backend ingestion are explicitly approved.

## Critical warning

All prices, discounts, availability, financing conditions, credit terms, vouchers, construction/readiness status, and commercial premises inventory in this file are unstable.

The AI assistant must not present this data as current fact. It may only mention that such programs or options are described in source materials and offer manager confirmation.

## Pricing claims found in source

These values are extracted from source material and require fresh manager confirmation:

- Stated starting price: from 22,100 грн/м2.
- Pricing table from source:
  - 1-room apartments, 35-41 м2: 56,000-62,000 грн/м2.
  - 2-room apartments, 56-64 м2: 53,000-56,000 грн/м2.
  - 3-room two-level apartments, 95 м2: 39,983-40,843 грн/м2.
  - 4-room two-level apartments, 84-110 м2: 39,000-41,000 грн/м2.
- Example 2-room apartment: 59.3 м2.
- Example 2-room apartment total price claim from PrivatBank example: 3.1 млн грн.

## Discount and promotion claims found in source

These are time-sensitive and must not be presented as active without manager confirmation:

- 2% discount for full payment.
- 10% discount for 100% payment.
- 10% discount on 3-room apartments under єОселя.
- 0% installment for 12 months on selected 2-room apartments.
- Promotion text: "Залишилось лише 3 квартири" for a selected 2-room apartment offer.
- Promotion text: "Залишилось лише 4 квартири в будинку" for a 3-room apartment discount campaign.
- Claim that buildings are already commissioned and buyers can start renovation immediately after deal registration.

## Apartment availability claims found in source

These are unstable and require manager confirmation:

- Apartment types mentioned:
  - 1-room apartments;
  - 2-room apartments;
  - 3-room apartments;
  - 4-room apartments;
  - two-level apartments;
  - patio apartments.
- Size ranges mentioned:
  - 1-room: 35-41 м2;
  - 2-room: 56-64 м2;
  - 3-room two-level: 95 м2 in one table;
  - 4-room two-level: 84-110 м2 in one table;
  - two-level apartments also described as 84-118 м2 in narrative copy.
- Example available unit described in source:
  - ready 2-room apartment;
  - 59.3 м2;
  - installment up to 12 months at 0%;
  - first payment 50%;
  - only 3 apartments on different floors claimed.
- Example 2-room layout details:
  - kitchen with loggia: 13 м2;
  - bedroom: 12.5 м2;
  - separate room with loggia: 17 м2 + 3.7 м2;
  - hallway: 7.1 м2;
  - separate bathroom: 4 м2 + 2 м2.

## Construction and readiness claims found in source

These require manager confirmation before production use:

- 3 buildings actively under construction.
- 19 buildings built.
- 16 buildings planned.
- Selected promotion claim: buildings already commissioned.
- Selected promotion claim: renovation can start immediately after deal registration.

## Installment terms found in source

These are extracted from source material and must be confirmed per apartment:

- Full payment:
  - one source line says 2% discount from total amount;
  - another source line says 10% discount for 100% payment.
- 1-room apartments:
  - first payment from 50%;
  - remaining amount split into equal parts;
  - price increases by 15% annual.
- 2-room apartments:
  - first payment from 50%;
  - remaining amount split into equal parts;
  - price increases by 15% annual;
  - first 6 months without interest, according to one source line.
- Two-level apartments:
  - option A: first payment from 10%, remaining amount split into equal parts, price increases by 15% annual, if apartment area is up to 90 м2;
  - option B: first payment from 30%, remaining amount split into equal parts, price increases by 15% annual, if apartment area is up to 90 м2.
- Selected 2-room promotion:
  - installment up to 12 months at 0%;
  - first payment 50%.

## Additional payment claims found in source

These require current legal/manager confirmation:

- Notary services: 2,500 грн.
- Alternative registration through CNAP: 0.1 subsistence minimum.
- PrivatBank commission: 1%, minimum 15 грн, maximum 500 грн.

## єОселя claims found in source

These are time-sensitive and require manager confirmation:

- єОселя for privileged categories: 3%.
- єОселя: 7%.
- 10% discount on 3-room apartments under єОселя.
- Suggested lead question: whether customer wants manager to check if єОселя is available for them.
- AI must not determine customer eligibility or promise approval.

## PrivatBank credit claims found in source

These are time-sensitive and require manager confirmation:

- Program name/positioning: `Житло в кредит` from PrivatBank as an alternative to єОселя.
- Credit amount: up to 5,000,000 грн.
- Term: up to 20 years.
- First payment: from 30%.
- Rate: 17.5% in the first year.
- Preliminary decision: in 2 minutes.
- Example:
  - 2-room apartment for 3.1 млн грн;
  - 1 млн грн first payment;
  - remaining amount paid by bank.
- AI must not promise bank approval, final terms, or exact payment.

## Housing voucher claims found in source

These are time-sensitive and require manager confirmation:

- Housing vouchers up to 2,000,000 грн.
- AI must not promise voucher eligibility, voucher amount, or purchase acceptance.

## Commercial premises claims found in source

These are extracted for manager confirmation:

- Commercial premises are offered in ЖК Orange Park at Крюковщина, вул. Одеська, 23.
- Positioned for business, rent, and investment.
- Facade premises in an active residential complex.
- Audience/traffic claims:
  - more than 2,000 resident families;
  - up to 10,000 potential traffic around;
  - 20+ businesses have chosen the location.
- Technical/property claims:
  - large facade windows;
  - 7 кВт electric capacity with possibility to increase;
  - direct electricity supply contracts;
  - 3 m ceilings;
  - convenient entrances and access for customers;
  - large parking zone.
- Commercial inventory, price, area, readiness, and terms are not stable in the prepared docs and require manager confirmation.

## Unclear/conflicting source data

- Distance to метро Теремки appears as 6.5 км and 7 км.
- Full-payment discount appears as 2% and 10%.
- Elevator brand conflict is outside pricing but relevant for manager review: Schindler vs Ozbesler.
- Two-level apartment area appears as 84-110 м2 and 84-118 м2.
- 3-room/4-room two-level area and pricing table may not match current availability.
- Two-level installment conditions list both 10% and 30% first payment and repeat "if area up to 90 м2"; this needs clarification.
- "Price from 22,100 грн/м2" conflicts with later table values starting much higher; likely stale or context-specific.
- Construction status and "buildings commissioned" claims may refer to different buildings or dates.
- "Only 3 apartments left" and "only 4 apartments left" are campaign-specific and likely stale.

## Manager confirmation checklist

Before production use, confirm:

- Current price per m2 by apartment type.
- Current total prices by apartment/building/floor.
- Current available apartments.
- Current available commercial premises.
- Current discount for full payment.
- Current active promotions and end dates.
- Current installment terms by apartment type.
- Whether 0% installment is active and for which units.
- Current єОселя 3% and 7% terms.
- Current PrivatBank credit terms.
- Current housing voucher terms and accepted categories.
- Current additional payments: notary, CNAP, bank commission, taxes/fees.
- Current construction/readiness status by building.
- Which buildings are commissioned.
- Whether buyer can start renovation immediately after deal registration.
- Current commercial premises price, area, electrical capacity, and readiness.
- Whether traffic, resident-family, and "20+ businesses" claims are approved for sales use.
- Official manager-approved wording for handoff, lead capture, and disclaimers.
