@alpstein-backend-engineer

Implement T8.1 only.

Goal:
Align ConversationService conversation reuse logic with updated flow specifications.

Requirements:
- update ConversationService.get_or_create_open_conversation
- reusable statuses:
  - open
  - waiting_for_customer
  - waiting_for_owner
- non-reusable:
  - closed
  - archived
- if multiple reusable conversations exist:
  - prefer latest last_message_at
  - fallback latest created_at
- keep create behavior unchanged:
  - new conversation status="open"

Rules:
- no API route changes
- no webhook orchestration
- no AI logic
- no lead logic
- no migrations
- no repository layer

Tests:
- reusable statuses are reused
- closed conversation not reused
- archived conversation not reused
- latest reusable conversation selected
- new conversation still created when none reusable exist

After implementation:
- run tests
- update completed.md
- update current-state.md if relevant
- update next-steps.md if relevant
- stop for review