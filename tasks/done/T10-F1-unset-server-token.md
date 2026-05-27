@alpstein-backend-engineer

Implement T10-F1 test hardening only.

Scope:
- tests only unless a real bug is exposed
- no production logic changes unless needed
- no AI changes
- no webhook orchestration changes
- no n8n changes

Add test:
- when N8N_BACKEND_API_TOKEN is unset/empty on server:
  - POST /api/v1/webhook/message returns 403
  - error.code = "FORBIDDEN"
  - WebhookMessageService.process_incoming_message is not called
  - no DB commit happens
  - response does not expose any token value

Optional:
- empty client header is rejected as missing/invalid token

After implementation:
- run auth tests
- update completed.md only if needed
- stop for review