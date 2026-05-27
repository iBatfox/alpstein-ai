@alpstein-migration-engineer

Implement T11.3 only.

Goal:
Add deterministic development seed data for AI configuration foundation tables.

Requirements:
- seed only development/demo data
- no production bootstrap logic
- use existing AsyncSession / SQLAlchemy patterns
- seed:
  - one demo tenant
  - one demo business
  - one tenant_business_profile
  - one tenant_ai_profile
  - one tenant_channel_setting
  - one or more tenant_knowledge_sources
  - minimal prompt_templates
- keep data deterministic and re-runnable
- avoid duplicate inserts on repeated execution
- no random/generated data
- no AI execution
- no Prompt Builder
- no Gateway
- no OpenAI calls
- no repositories
- no migrations in this task unless strictly required for seed support

Rules:
- seed must not contain secrets/API keys
- prompt templates must remain platform-scoped
- knowledge content should stay MVP-small and human-readable
- do not modify webhook orchestration

Tests:
- seed can run repeatedly without duplicate rows
- prompt templates are unique by template_key
- tenant-owned rows stay tenant-scoped

After implementation:
- run tests
- update completed.md
- update current-state.md
- update next-steps.md
- stop for review