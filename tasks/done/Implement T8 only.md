@alpstein-backend-engineer

Implement T8 only.

Goal:
Add CustomerService and ConversationService helpers required before webhook orchestration.

Requirements:

CustomerService:
- get_or_create_customer(...)
- resolve customer by:
  - tenant_id
  - business_id
  - phone OR external_customer_id
- create customer when missing
- avoid duplicate customer creation
- support nullable name/email

ConversationService:
- get_or_create_open_conversation(...)
- find active/open conversation for:
  - tenant_id
  - business_id
  - customer_id
  - channel
- create conversation when none exists
- default status="open"

Rules:
- always tenant-scoped
- no API routes
- no webhook orchestration
- no AI logic
- no lead logic
- no notification logic
- no migrations unless absolutely required by current schema mismatch
- keep services minimal
- no repository layer

Tests:
- customer found by phone
- customer found by external_customer_id
- customer created when missing
- no duplicate customer creation
- open conversation reused
- new conversation created when missing
- closed conversation not reused

After implementation:
- run tests
- update completed.md
- update current-state.md
- update next-steps.md
- stop for review