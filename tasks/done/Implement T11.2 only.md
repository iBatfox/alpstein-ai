@alpstein-backend-engineer

Implement T11.2 only.

Goal:
Add tenant-scoped AI configuration persistence services/helpers using the existing AsyncSession service pattern.

Requirements:

Create minimal read-focused services/helpers for:
- TenantAiProfile
- TenantBusinessProfile
- TenantChannelSetting
- TenantKnowledgeSource
- PromptTemplate

Behavior:
- all tenant-owned queries must filter by tenant_id and business_id
- knowledge loader returns only is_active=true
- channel settings resolved by tenant_id + business_id + channel
- prompt template lookup by template_key
- return None when optional config missing
- no generic repository layer
- no base CRUD abstraction
- use same service style as T4–T10

Rules:
- no Prompt Builder yet
- no AI orchestration
- no OpenAI calls
- no prompt execution
- no caching
- no route changes
- no migrations
- no seed data

Tests:
- tenant isolation enforced in queries
- inactive knowledge excluded
- prompt template lookup works
- optional configs can return None
- no global queries without tenant_id/business_id

After implementation:
- run tests
- update completed.md
- update current-state.md
- update next-steps.md
- stop for review