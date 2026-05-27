@alpstein-api-designer

Update specs only.

Goal:
Clarify conversation reuse behavior before T10 webhook orchestration.

Requirements:
- update specs/flows/incoming-message-flow.md
- optionally update specs/database/entities.md if needed
- define reusable conversation statuses:
  - open
  - waiting_for_customer
  - waiting_for_owner
- define non-reusable statuses:
  - closed
  - archived
- do not change backend code
- do not change tests
- do not change migrations
- do not implement T10

Reason:
T8 currently reuses only status="open", but incoming-message-flow should clearly define product behavior before route orchestration.

After update:
- summarize spec changes
- stop for review