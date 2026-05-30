# T-IG-OUTBOUND-REPLY — Instagram outbound reply via Meta Send API

## Goal

When AI produces `reply_to_customer` for Instagram, n8n calls backend
`POST /api/v1/channels/instagram/send-message` → `InstagramClient.send_message()` → Meta Send API.

## Scope

- Backend: `send_message()`, outbound endpoint, kill switch, logs, tests
- n8n: unified workflow Instagram reply branch (no second workflow)
- ERPNext: ensure `instagram_username` / `instagram_display_name` visible on Lead form

## Rules

- n8n must not call Meta directly
- **Use existing workflow only:** `alpstein-customer-ingress` ID `aYrRmAGKhP4TJbG9` — no second workflow
- Instagram outbound branch is parallel from `POST Backend` inside unified workflow
- `ALPSTEIN_INSTAGRAM_OUTBOUND_ENABLED=false` by default
- Do not change Telegram branch or ERPNext dedupe logic
- Do not re-enable Website Chat

## Tests

- `pytest tests/test_instagram_client.py tests/test_instagram_outbound*.py`

## Out of scope

- Commits (human review first)
- Website Chat
