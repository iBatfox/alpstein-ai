@alpstein-backend-engineer

Implement T10 only.

Goal:
Wire POST /api/v1/webhook/message orchestration using existing services and schemas.

Use existing components:
- NormalizedWebhookMessageRequest from T9
- BusinessService.get_by_external_id from T7
- CustomerService.get_or_create_customer from T8
- ConversationService.get_or_create_open_conversation from T8/T8.1
- MessageService.save_incoming_customer_message from T5

Requirements:
- create route POST /api/v1/webhook/message
- validate request with NormalizedWebhookMessageRequest
- resolve business by request.business_id as external_id
- resolve tenant_id from business.tenant_id
- get or create customer
- get or create reusable conversation
- save incoming customer message
- update conversation.last_message_at when message is saved/reused as appropriate
- return success/data envelope
- include:
  - conversation.id
  - conversation.status
  - message.id
  - message.is_duplicate
  - reply_to_customer can be a temporary mock/stub text
  - lead_created=false
  - notify_owner=false

Rules:
- no AI provider call
- no lead creation
- no n8n changes
- no migrations
- no new architecture
- route must stay thin; orchestration may use a small service/helper if already consistent with backend architecture
- do not duplicate business/customer/conversation/message lookup logic inside route if services already exist

Tests:
- valid payload returns success=true
- business not found maps to error envelope with BUSINESS_NOT_FOUND
- duplicate message returns is_duplicate=true
- customer is created when missing
- reusable conversation is reused
- closed/archived conversation is not reused
- no AI/lead/notification side effects

After implementation:
- run tests
- update completed.md
- update current-state.md
- update next-steps.md
- stop for review