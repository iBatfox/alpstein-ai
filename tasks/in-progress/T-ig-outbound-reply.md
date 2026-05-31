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
- `pytest tests/test_instagram_webhook_outbound_reingress.py` (duplicate re-ingress + dedup)

## Done (2026-05-31, pending review)

- Backend: `instagram_outbound_allowed` on webhook response; `instagram_outbound_sends` dedup table (migration `0022`)
- n8n skeleton: `IF Instagram Should Send Reply` uses `instagram_outbound_allowed` (not `is_duplicate`)
- versionId: `f2.5-instagram-duplicate-outbound-v1` in builder (import to runtime required)

## AI alignment (2026-05-31, pending review)

**Root cause of generic Instagram reply:** duplicate re-ingress after Meta persist set `is_duplicate=true`; old `_ai_duplicate_for_incoming_replay` used `find_last_outgoing_ai_message()` (any prior turn) → AI skipped → `_duplicate_reply_to_customer()` returned stale text or `DUPLICATE_SAFE_ACKNOWLEDGMENT`.

**Fix:**
- `MessageService.find_outgoing_ai_for_inbound()` — per-inbound outbound via `message_traces`
- Instagram duplicate re-ingress runs AI once unless outbound already linked to **this** inbound id
- `mark_completed` on message trace when AI runs on duplicate re-ingress
- Logs: `webhook_ai_reingress_decision`, `ai_reply_generation_started`

**Tests:**
- `tests/test_instagram_ai_reingress.py`
- `tests/test_channel_ai_prompt_parity.py`
- `scripts/n8n/test_instagram_reply_context.py`

**Deploy:** backend image rebuilt/restarted (`alpstein_backend`).

## Out of scope

- Commits (human review first)
- Website Chat
