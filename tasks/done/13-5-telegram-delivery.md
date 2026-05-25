Complete final T13.5 Telegram delivery verification.

Context:
T13.5 workflow branch logic is already verified.
Backend :8010 is fixed and returns 200.
Post-Respond topology is confirmed: nodes after Respond Customer Reply do execute.
Remaining blocker: Telegram runtime config is missing.

Scope:
- n8n runtime config
- Telegram credential binding
- final urgent-message test
- docs/status update
- no backend changes
- no DB changes
- no workflow redesign
- no retries/T13.6
- no secrets committed or printed

Workflow path to verify:

Test Webhook / Telegram input
→ Normalize Incoming
→ POST Backend
→ Shape Customer Reply
→ Respond Customer Reply
→ IF Notify Owner
→ Shape Owner Notification
→ Telegram Owner Notify

Tasks:

1. Configure Telegram runtime:
   - add TELEGRAM_CHAT_ID to n8n runtime env
   - create or bind real telegramApi credential in n8n UI
   - ensure Telegram Owner Notify uses the real credential
   - restart/recreate n8n container only if needed for env reload
   - do not print bot token, chat id, or secrets

2. Run final urgent test through n8n webhook.

Use a fresh external_message_id.

Customer text example:
URGENT: need an appointment ASAP

Expected backend / workflow behavior:
- HTTP 200
- success: true
- reply_to_customer present
- backend data.notify_owner === true
- IF Notify Owner evaluates true
- Shape Owner Notification executes successfully
- Telegram Owner Notify executes successfully
- owner receives Telegram message

3. Verify execution graph:
- POST Backend green
- Shape Customer Reply green
- Respond Customer Reply green
- IF Notify Owner green / true branch
- Shape Owner Notification green
- Telegram Owner Notify green

4. Re-run duplicate test with same external_message_id.

Expected:
- HTTP 200
- success: true
- message.is_duplicate === true
- IF Notify Owner false or skipped
- Telegram Owner Notify does not execute again

5. Update docs/status:
- docs/ops/n8n-workflow1-test-webhook.md
- tasks/done/T13.5-owner-notification-branch.md
- docs/project-status/next-steps.md
- docs/project-status/completed.md if needed

Return:
- final runtime summary
- urgent test HTTP status
- Telegram delivery result
- duplicate suppression result
- execution IDs if available
- whether T13.5 runtime/Gate 2 passed
- whether live Telegram customer flow may start

Important:
Do not start T13.6.
Do not touch backend.
Do not expose bot token, chat id, backend token, DB URL, or passwords.