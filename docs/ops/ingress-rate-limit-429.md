# Ingress rate limit 429 — n8n / ops notes

## Rollout gate (mandatory)

**E3.5d PostgreSQL concurrency validation is complete** ([`e3-5d-postgres-concurrency-validation.md`](../../docs/audits/e3-5d-postgres-concurrency-validation.md)).

You may enable `ALPSTEIN_AI_RATE_LIMIT_ENABLED=true` in **staging** for soak testing. Keep **production** off until staging review passes.

`ALPSTEIN_AI_SPAM_PROTECTION_ENABLED` remains `false` until E3.6 staging validation completes.

---

When `ALPSTEIN_AI_RATE_LIMIT_ENABLED=true`, the backend may reject normalized webhook ingress with:

```http
HTTP/1.1 429 Too Many Requests
```

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Ingress rate limit exceeded",
    "metadata": {
      "scope_type": "conversation",
      "scope_key": "...",
      "adapter": "telegram",
      "retry_after_seconds": 42,
      "window_seconds": 60,
      "limit": 30,
      "current_count": 30
    }
  }
}
```

## Operator guidance

- **Do not** retry immediately in a tight loop — that amplifies load.
- Use `error.metadata.retry_after_seconds` (or default **60s** window) as minimum wait before retry.
- Exponential backoff is recommended for provider-driven retries (e.g. Telegram redelivery): wait `retry_after_seconds`, then 2×, cap at a few minutes.
- **Idempotent duplicates** (same `external_message_id`) return **200** and do **not** consume rate limit budget — safe to replay after backoff.
- **503** `ADAPTER_INGRESS_CONTAINED` (E3.4) is a different signal — longer backoff or pause ingress for that adapter until health recovers.

## n8n workflow (no MVP change required)

Existing workflows can treat 429 like other non-2xx backend responses. Optional hardening (operator-owned):

1. On HTTP 429, read `retry_after_seconds` from response JSON.
2. Wait at least that many seconds before calling `POST /api/v1/webhook/message` again for the same customer message.
3. Log violation scope (`scope_type`, `adapter`) for ops; do not log full message text in external systems.

No n8n workflow file changes are required for MVP; backend enforcement is sufficient.
