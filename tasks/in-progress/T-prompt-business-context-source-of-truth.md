# T-prompt-business-context-source-of-truth

## Goal

Make business facts, contacts, links, working hours, and services come only from the current tenant/business context in prompt assembly.

## Scope

- Audit where `platform_system` and business context sections are assembled.
- Keep platform system generic and free from business-specific facts.
- Add a separate `business_context_source_of_truth` prompt section for current tenant/operator business context.
- Add prompt rules that conversation history and customer memory cannot override current business facts.
- Add prompt source diagnostics for source-of-truth loading/hash and marker checks.
- Add/update focused prompt and orchestration tests.
- Run relevant backend tests and backend healthcheck after rebuild.

## Out of Scope

- No n8n delivery changes.
- No Telegram or Instagram send changes.
- No AI delivery/runtime workflow redesign.
- No lead merge or workflow changes.
- No commit without human review.

## Tests

- Platform system contains no `linkedin.com/in/ibatfox`, `admin@alpstein-ai.ch`, or `instagram.com`.
- Business context is inserted in a separate `business_context_source_of_truth` section.
- Stale history/platform LinkedIn cannot override current business context Instagram.
- Existing prompt/orchestration/langfuse tests still pass.
