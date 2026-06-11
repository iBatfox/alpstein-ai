# T-orange-park-contact-form-behavior

## Goal

Make Orange Park Telegram MVP collect structured contact data in the customer's language when the customer asks to be contacted or sends a phone number.

## Scope

- Update Orange Park behavior documentation.
- Update Orange Park seed configuration so contact-form rules are loaded into AI profile and knowledge source rows.
- Add a narrow Orange Park Telegram webhook guard for stage-1 contact collection where needed.
- Keep current Orange Park MVP lead creation disabled.
- Add focused tests.

## Requirements

- Mirror Ukrainian or Russian based on customer context.
- Never switch to English unless the customer writes English.
- If the customer asks for contact or manager handoff, ask for:
  - first name;
  - last name;
  - phone.
- If a phone number is already provided, acknowledge it and ask only for missing first and last name.
- Do not say the request was passed to the manager until minimum fields are collected.
- Minimum stage-1 lead fields are first name, last name, phone, Telegram id/username when available, and interest summary from the conversation.
- Do not create Bitrix leads in stage 1.
- Keep webhook `lead_created=false` for Orange Park Telegram MVP.
- Store structured intent in message metadata when supported by the current schema.

## Out Of Scope

- No Bitrix integration.
- No n8n changes.
- No Mini App changes.
- No migrations.
- No commit or push until review.

## Validation

- Targeted backend tests.
- Orange Park seed dry-run.
- Orange Park normal seed.
- Orange Park webhook phone-number smoke test.
