# T-meta-instagram-debug-logs — Instagram Meta webhook diagnostic logs

## Goal

Make parsed Instagram webhook payload details visible in Docker logs for debugging `POST /webhooks/meta`.

## Scope

- Add an explicit safe `logger.info` message after Meta webhook payload parsing and safe `log_context` creation.
- Include:
  - `object`
  - `entry_count`
  - `message_ids`
  - `instagram_inbound` count
  - for each Instagram inbound message:
    - `sender_id`
    - `message_id`
    - `message_text` truncated to 200 characters
- Keep the existing response unchanged: `{"status": "received"}`.
- Temporary debug: when `field == "messages"` and no Instagram inbound message is parsed,
  log the full redacted `changes[].value` payload to inspect Meta's message shape.
- Parse real Instagram `changes[].value.message.text` payloads even when `message.mid`
  / `message.id` is absent, using deterministic fallback id
  `instagram:{sender_id}:{timestamp}`.
- Parse real legacy Instagram `entry[].messaging[]` payloads with sender, recipient,
  timestamp, `message.mid` / `message.id`, and `message.text`.
- Add or adjust focused tests.
- Rebuild backend and recreate only `alpstein_backend`.
- Verify with a safe Meta Instagram `messages` test payload and Docker logs.

## Rules

- Do not log tokens, headers, app secret, access token, or raw provider payloads.
- Temporary full-value logging must redact secret-looking keys recursively.
- No n8n, AI, database, or product behavior changes.
- No commits.
- No pushes.

## Out of Scope

- Instagram normalization into the business webhook flow.
- Meta signature validation.
- Outbound Instagram replies.
