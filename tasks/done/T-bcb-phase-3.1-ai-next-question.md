@alpstein-ai-integration-engineer
@alpstein-backend-engineer

Implement Phase 3.1: Business Context Builder AI next-question generation.

Goal:
Add AI generation only for the next assistant question inside Business Context Builder.

Scope:
- AI service + prompt service
- wire into save_user_message with static fallback
- BCB_AI_ENABLED feature flag
- tests; no final context AI; no production assistant writes

Status: completed (awaiting review)
