@alpstein-backend-engineer

Implement T4 only.

Goal:
Add MessageService.find_by_external_id to find existing messages by external_message_id before duplicate insert.

Requirements:
- create minimal MessageService if it does not exist
- add async find_by_external_id(session, tenant_id, business_id, external_message_id)
- always filter by tenant_id and business_id
- return existing Message or None
- if external_message_id is None, return None
- no insert logic
- no API route
- no webhook integration
- no AI logic
- no DB migration

Tests:
- finds existing message by tenant_id + business_id + external_message_id
- returns None when external_message_id is missing
- returns None for same external_message_id but different tenant_id
- returns None for same external_message_id but different business_id

After implementation:
- run tests
- update completed.md
- update current-state.md if relevant
- stop for review