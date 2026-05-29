# Ingress spam protection — n8n / ops notes

## Rollout gate (mandatory)

**Keep `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED=false` until:**

1. E3.6 implementation tests are green
2. E3.5d PostgreSQL concurrency validation is green ([`T-e3.5d-postgres-concurrency-validation.md`](../../tasks/todo/T-e3.5d-postgres-concurrency-validation.md))
3. E3.6 staging validation is completed

Migrations (`0019`–`0021`) may be applied while the flag stays off — tables are inert when enforcement is disabled.

---

## Initial production posture

With `ALPSTEIN_AI_SPAM_PRODUCTION_SAFE_MODE=true` (default):

- Only **`mark_suspicious`** decisions are applied
- **`throttle`**, **`temporary_block`**, and **`ignore`** are downgraded to `mark_suspicious`
- Ingress is **not blocked** for spam signals until staging validates blocking actions with production safe mode off

Do **not** disable production safe mode in production until staging sign-off.

---

## Payload fingerprint (privacy)

The `payload_repeat` rule detects repeated normalized message content using a **SHA-256 hex digest**:

- Input: whitespace-normalized message text (trim + collapse internal spaces)
- Stored: hash in bucket `scope_key` and optional `payload_hash_prefix` in decision metadata
- **Never stored:** raw message text, prompts, secrets, API tokens, or raw provider payloads

Operators troubleshooting repeat-spam signals should use `rule_id`, `observed_count`, `threshold`, and hash prefix — not message content from spam tables.

---

## Webhook error responses

When `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED=true`, non-duplicate ingress may return:

### 429 SPAM_THROTTLED

```json
{
  "success": false,
  "error": {
    "code": "SPAM_THROTTLED",
    "message": "Ingress throttled by spam protection",
    "metadata": {
      "rule_id": "payload_repeat",
      "decision": "throttle"
    }
  }
}
```

### 403 SPAM_CONTAINED

```json
{
  "success": false,
  "error": {
    "code": "SPAM_CONTAINED",
    "message": "Ingress blocked by spam containment",
    "metadata": {
      "rule_id": "replay_storm",
      "decision": "temporary_block"
    }
  }
}
```

Metadata contains safe operational fields only — no message text.

---

## Operator guidance

- **Do not** retry immediately in a tight loop on 429/403 spam responses
- Idempotent duplicates (same `external_message_id`) return **200** and skip spam evaluation
- E3.5 `RATE_LIMIT_EXCEEDED` (429) and E3.6 spam responses are different signals — both require backoff
- Containment is **TTL-based and reversible** — no permanent bans, no tenant-wide auto-blocks
- List active containment: `GET /api/v1/observability/spam-containments?tenant_id=...&business_id=...&active_only=true`
- Audit decisions: `GET /api/v1/observability/spam-decisions?tenant_id=...&business_id=...`

---

## Ingress order

```text
duplicate detection → E3.5 rate limit → E3.6 spam → E3.4 gate → AI orchestration
```

---

## n8n workflow (no MVP change required)

Existing workflows can treat 429/403 like other non-2xx backend responses. Optional hardening (operator-owned):

1. On `SPAM_THROTTLED` or `SPAM_CONTAINED`, log `rule_id` from metadata
2. Apply exponential backoff before retrying the same customer message
3. Do not log full message text in external systems when debugging spam signals

No n8n workflow file changes are required for MVP; backend enforcement is sufficient.
