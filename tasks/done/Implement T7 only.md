@alpstein-backend-engineer

Implement T7 only.

Goal:
Add BusinessService.get_by_external_id to resolve normalized webhook business_id into a Business row.

Requirements:
- create backend/app/services/business_service.py
- add async get_by_external_id(session, external_id) -> Business
- lookup by Business.external_id
- return Business when found
- raise BusinessNotFoundError when missing
- add minimal BusinessNotFoundError in backend/app/exceptions.py
- no API route
- no webhook orchestration
- no customer/conversation/message logic
- no AI logic
- no n8n changes
- no migration

Tests:
- returns business by external_id
- raises BusinessNotFoundError when not found
- query filters by external_id
- no tenant_id parameter required because external_id is globally unique in current schema

After implementation:
- run tests
- update completed.md
- update current-state.md if relevant
- create docs/project-status/next-steps.md if missing and add the next logical task
- stop for review