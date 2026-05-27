# T14-OC-2 — Backend `operator_business_context`

**Status:** Done (review pending deploy)

## Scope

- Webhook Pydantic field + normalization (max 8192)
- Wire: `WebhookMessageService` → `AiReplyOrchestrationCoordinator` → `AiReplyOrchestrationService` → `PromptBuilderService`
- Append `OPERATOR BUSINESS NOTES` after DB profile in `tenant_business_context`
- Tests: `tests/test_operator_business_context.py`, `tests/test_webhook_schemas.py`
- Docs: `docs/architecture/operator-business-context-n8n.md`, spec status updates

## Out of scope

- DB migration, n8n workflow, persisting operator text on `messages`

## Next

**T14-OC-3** — n8n Add Business Context Set node (may start after backend deploy).
