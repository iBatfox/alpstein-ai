# T10-F1 — Webhook API token auth (done)

**Status:** Complete. **187** pytest green.

## Summary

- `POST /api/v1/webhook/message` requires header `X-Alpstein-Webhook-Token` matching env `N8N_BACKEND_API_TOKEN`.
- Auth runs via FastAPI `dependencies=[Depends(require_webhook_token)]` before route handler / `WebhookMessageService`.
- Missing/invalid client token → HTTP 401, `error.code=UNAUTHORIZED`.
- Server token unset → HTTP 403, `error.code=FORBIDDEN`.
- `GET /api/v1/health` unchanged (no auth).
- Tokens never logged or echoed in errors.

## Files

- `backend/app/api/webhook_auth.py`
- `backend/app/api/routes/webhook.py`
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/tests/test_webhook_token_auth.py`
- `backend/tests/test_webhook_message_route.py` (auth headers fixture)
- `.env.example`

---

@alpstein-backend-engineer

Implement T10-F1 only.

Goal:
Protect POST /api/v1/webhook/message with API token authentication for n8n → backend.

Scope:
- webhook API token auth only
- no AI logic changes
- no webhook orchestration changes
- no n8n workflow changes
- no DB/migrations
- no lead/notification logic

Requirements:
- add API token check for POST /api/v1/webhook/message
- use header-based auth, for example:
  X-Alpstein-Webhook-Token
- read expected token from environment/settings:
  N8N_BACKEND_API_TOKEN
- if token is missing or invalid:
  - return HTTP 401 or 403 according to existing API spec
  - return standard error envelope:
    success=false
    error.code="UNAUTHORIZED" or "FORBIDDEN"
    error.message=...
- do not log the token
- do not expose expected token in errors
- keep route thin
- auth must happen before WebhookMessageService processing
- health endpoint remains unauthenticated
- update .env.example with empty placeholder only

Tests:
- missing token rejects request
- invalid token rejects request
- valid token allows webhook processing
- token is not included in response/log-style error message
- health endpoint still works without token
- WebhookMessageService is not called when auth fails

After implementation:
- create/move task file according to AGENTS.md lifecycle rules
- run tests
- update completed.md
- update current-state.md
- update next-steps.md
- stop for review