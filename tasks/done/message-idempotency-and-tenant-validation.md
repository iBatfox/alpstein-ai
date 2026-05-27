# Message Idempotency and Tenant Validation

## Status

todo

## Source

Reviewer notes for messages persistence slice.

## Goal

Define and implement message duplicate prevention and tenant/business/conversation consistency validation.

## Scope

- external_message_id idempotency strategy
- duplicate webhook retry prevention
- tenant_id / business_id / conversation_id consistency validation
- service-layer validation before message insert

## Out of scope

- Redis
- queues
- distributed locking
- n8n changes
- AI changes

## Proposed ownership

- Planning: alpstein-task-planner
- Implementation: alpstein-backend-engineer
- DB constraint review: alpstein-database-architect
- Final review: alpstein-reviewer

## Open questions

- Should uniqueness be business-scoped or tenant-scoped?
- Should DB unique constraint be added now or after service-layer implementation?

## Recommended first step

Use alpstein-task-planner to split this into small implementation tasks.