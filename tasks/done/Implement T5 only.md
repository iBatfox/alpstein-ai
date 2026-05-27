@alpstein-backend-engineer

Implement T5 only.

Goal:
Add MessageService.save_incoming_customer_message for safe incoming customer message persistence with tenant validation and idempotency.

Requirements:
- use validate_tenant_context from T3
- use find_by_external_id from T4 before insert
- if external_message_id is None or empty string, skip dedup lookup
- if duplicate found, return existing message with is_duplicate=True
- if no duplicate, create incoming customer Message
- set sender_type="customer"
- set direction according to current Message model/spec
- set channel from conversation/channel input
- set message_text from input
- set message_type="text"
- include external_message_id and raw_payload if provided
- no API route
- no webhook integration
- no AI logic
- no lead logic
- no migration

Tests:
- happy path inserts one message
- duplicate external_message_id returns existing message and does not insert
- external_message_id None skips dedup lookup and inserts
- external_message_id empty string skips dedup lookup and inserts
- tenant mismatch raises TenantContextError
- business/conversation/customer mismatch raises TenantContextError

After implementation:
- run tests
- update completed.md
- update current-state.md if relevant
- stop for review