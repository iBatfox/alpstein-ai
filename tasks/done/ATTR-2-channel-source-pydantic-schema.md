# ATTR-2 — Channel source attribution Pydantic schema

**Status:** Done (review pending)

## Scope

- `WebhookSource`, `WebhookAttribution`, `WebhookMessageClient` on `NormalizedWebhookMessageRequest`
- `message.external_conversation_id` with channel prefix validation
- `extra="ignore"` on webhook request models
- Secret-like string rejection on attribution fields
- Tests + spec/docs status update

## Out of scope

- DB migration / persistence (ATTR-3)
- Prompt Builder (ATTR-4)
- n8n adapters (ATTR-6)
- Lead attribution (ATTR-5)

## Validation highlights

| Rule | Behavior |
|------|----------|
| All new fields | Optional |
| `external_conversation_id` | Requires `tg:` / `wa:` / `web:` / `ig:` / `fb:` / `email:` / `sms:` / `voice:` / `api:` prefix |
| `external_message_id` | Unchanged (no new prefix requirement) |
| Max lengths | Per ATTR-2 task spec |
| Secrets in strings | Rejected (Bearer, sk-, api_key=, etc.) |

## Next

**ATTR-3** — persist attribution subset to conversation/message metadata.
