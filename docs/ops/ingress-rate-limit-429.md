# Ingress rate limit 429 — n8n / ops notes

## Rollout gate (mandatory)

**Keep `ALPSTEIN_AI_RATE_LIMIT_ENABLED=false` until PostgreSQL concurrency validation is complete.**

E3.5 ships with the flag default off. Do **not** enable in staging or production until task [`T-e3.5d-postgres-concurrency-validation.md`](../../tasks/todo/T-e3.5d-postgres-concurrency-validation.md) passes (two concurrent DB sessions, limit=1, one accept / one reject, bucket count=1, one violation row).

Migrations (`0017`/`0018`) may be applied while the flag stays off — tables are inert when enforcement is disabled.

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
