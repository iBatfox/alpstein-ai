@alpstein-backend-engineer

Implement T9 only.

Goal:
Add normalized webhook Pydantic schemas for POST /api/v1/webhook/message.

Requirements:
- create schemas for normalized webhook request only
- include business_id, channel, customer, message
- customer fields:
  - phone
  - name
  - email
  - external_customer_id
- message fields:
  - text
  - external_message_id
  - timestamp
  - raw_payload
- validate channel against allowed values:
  whatsapp, telegram, instagram, website_chat, test
- require:
  - business_id
  - channel
  - message.text
  - at least one customer identifier: phone or external_customer_id
- keep schema aligned with specs/api/webhooks.md
- no route orchestration
- no MessageService call
- no BusinessService call
- no CustomerService call
- no ConversationService call
- no AI logic
- no DB access
- no n8n changes

Tests:
- valid normalized payload passes
- missing business_id fails
- invalid channel fails
- missing message.text fails
- missing both customer.phone and customer.external_customer_id fails
- optional fields can be null/missing
- raw_payload accepted as dict

After implementation:
- run tests
- update completed.md
- update current-state.md if relevant
- update next-steps.md if relevant
- stop for review