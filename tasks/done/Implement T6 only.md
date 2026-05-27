@alpstein-migration-engineer

Implement T6 only.

Goal:
Add database-level protection against concurrent duplicate incoming messages.

Requirements:
- add partial unique index on messages(business_id, external_message_id)
- condition: external_message_id IS NOT NULL
- update Message model __table_args__
- update migration/model tests
- keep existing non-unique indexes only if still needed by specs
- no service changes
- no API changes
- no webhook changes
- no AI or lead logic

Rules:
- use Alembic standard revision generation
- migration must be reversible
- do not drop data
- do not create unrelated indexes or constraints
- explain migration impact

After implementation:
- run tests
- update completed.md
- update current-state.md if relevant
- stop for review