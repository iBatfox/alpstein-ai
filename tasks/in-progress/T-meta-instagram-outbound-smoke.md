# T-meta-instagram-outbound-smoke — Instagram outbound test reply script

## Goal

Add a safe standalone Instagram outbound text-message smoke test for a real sender id observed from webhook logs.

## Scope

- Add `send_text_message(recipient_id: str, text: str)` to the Instagram client.
- Use `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_USER_ID`.
- Send via Instagram Messaging API `POST https://graph.instagram.com/{api_version}/{ig_user_id}/messages`.
- Add standalone script `scripts/test_instagram_send_message.py` with:
  - `--recipient-id`
  - `--text`
- Add focused mocked tests for request shape and error handling.

## Rules

- Do not wire this into webhook handling.
- Do not add auto-reply behavior.
- Do not use GPT or n8n.
- Test only with a real `sender_id` from a webhook.
- Do not log or print access tokens.
- No commits.
- No pushes.

## Out of Scope

- Webhook-triggered Instagram replies.
- AI-generated replies.
- n8n workflow changes.
