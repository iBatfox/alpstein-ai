# T-orange-park-telegram-contact-request

## Goal

Add Telegram native contact-sharing flow for Orange Park lead capture.

## Scope

- Orange Park Telegram n8n workflow only.
- Backend normalized webhook handling for Telegram contact data.
- Contact capture metadata and CRM/Bitrix gating for Orange Park stage 2.
- Focused tests for contact request, contact parsing, no manual phone requirement, and CRM lead gating.

## Requirements

- Show Telegram native `request_contact` button when backend response metadata indicates contact collection is needed.
- Normalize Telegram contact payload fields before sending to backend:
  - `contact.phone_number`
  - `contact.first_name`
  - `contact.last_name`
  - Telegram user id
  - Telegram username when available
- Store contact data for `business_id=orange-park` and `channel=telegram`.
- After contact is received, do not create a Bitrix lead unless CRM/Bitrix integration is enabled for the flow.
- If Bitrix is disabled, store contact data in message/conversation metadata only.
- Reply after contact receipt:
  `Дякую, номер отримали. Менеджер зв'яжеться з вами найближчим часом.`
- Do not expose Telegram tokens.
- Do not modify other workflows or affect other businesses.
- Keep n8n as transport/integration and backend as business logic.

## Validation

- n8n workflow JSON is valid.
- Backend tests pass.
- Contact button can be live-tested in Telegram.
- `lead_created` behavior matches flow CRM config.
