# Message debugging runbook (E2.0)

**Status:** design / ops reference  
**Date:** 2026-05-28  
**Runtime:** [`runtime-map.md`](runtime-map.md) — **15679** n8n, **8000** backend, **15433** postgres; **`docker compose` v2 only**

**Architecture:** [`unified-conversation-observability.md`](../architecture/unified-conversation-observability.md)

---

## 1. When to use this runbook

A customer message on **Telegram** or **Website Chat** failed, returned wrong content, duplicated, or never received a reply after E1.9 unified ingress.

**You need one identifier:** `correlation_id` (UUID). Get it from:

- Website widget JSON response field `correlation_id`
- n8n execution data (Normalize / POST Backend node output)
- Backend webhook JSON response
- Langfuse trace metadata (dev)

---

## 2. Debug order (always top → bottom)

```text
1. correlation_id known?
2. n8n execution (alpstein-customer-ingress)
3. POST Backend HTTP status + body
4. Backend logs / health
5. PostgreSQL rows (messages, prompt_runs; message_traces when E2.4+)
6. Channel delivery node (Telegram Send / Website Respond)
7. Owner notify branch (if urgent — separate from customer reply)
```

---

## 3. Telegram failed message

### 3.1 First checks (2 min)

| Check | Command / location | Pass |
|-------|-------------------|------|
| Workflow active | n8n UI → `alpstein-customer-ingress` (`aYrRmAGKhP4TJbG9`) | Active |
| Correct business | Env `ALPSTEIN_TELEGRAM_BUSINESS_ID` = `alpstein_ai_demo_001` (or intended) | Matches DB |
| n8n reachable | `curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:15679/healthz` | 200 |
| Backend ready | `docker exec alpstein_n8n_compose wget -qO- http://backend:8000/api/v1/health/ready` | 200 |
| Token | `N8N_BACKEND_API_TOKEN` aligned n8n ↔ backend | No 401 |

### 3.2 n8n execution

1. Open execution by time or search `correlation_id` in node output.
2. **Normalize Telegram Incoming** — verify `business_id`, `channel=telegram`, `message.external_message_id` like `tg:{chat}:{msg}`.
3. **Add Business Context** — `operator_business_context` present (runtime rules only).
4. **POST Backend** — expect HTTP 200, body `success: true`, `correlation_id` echoed.

| Failure | Likely cause |
|---------|----------------|
| Normalize returns empty | Non-private chat, bot message, empty text |
| POST 401 | Token mismatch |
| POST 404 business | Wrong `business_id` / business not seeded |
| POST 422 | Validation — missing `message.text` or customer id |

### 3.3 Database (scoped queries)

Replace `:correlation_id` with UUID. **No secrets in tickets.**

```sql
-- prompt_runs metadata (today's primary audit link)
SELECT id, conversation_id, message_id, model, latency_ms, error,
       metadata->>'correlation_id' AS correlation_id,
       metadata->>'n8n_execution_id' AS n8n_execution_id,
       created_at
FROM prompt_runs
WHERE metadata->>'correlation_id' = ':correlation_id';

-- messages in same conversation (if conversation_id known from above)
SELECT m.id, m.sender_type, m.direction, m.created_at,
       LEFT(m.message_text, 80) AS preview
FROM messages m
WHERE m.conversation_id = :conversation_id
ORDER BY m.created_at;
```

**Future (E2.4):** `SELECT * FROM message_traces WHERE correlation_id = '…';`

### 3.4 Delivery

- **Telegram Send Message** node — credential = customer bot (`alpsteinai_0001bot`).
- Errors like `chat not found` → wrong `telegram_chat_id` or user never started bot.

### 3.5 Common Telegram pitfalls

| Symptom | Check |
|---------|-------|
| Barbershop tone on Alpstein bot | Wrong `business_id` → wrong `tenant_business_profiles` |
| Russian ignored | `operator_business_context` + AI profile `language` + polluted **history** |
| Duplicate replies | `external_message_id` / idempotency — same `tg:…` key |
| Wrong thread | **Known gap:** conversation lookup by customer+channel only until E2.2 |

---

## 4. Website Chat failed message

### 4.1 First checks

| Check | Pass |
|-------|------|
| Kill switch | `ALPSTEIN_WEBSITE_CHAT_ENABLED=true` in n8n env |
| URL | Production: `…/webhook/alpstein/unified-customer-ingress/website-chat/incoming` |
| `business_id` | `ALPSTEIN_WEBSITE_CHAT_BUSINESS_ID` or body field |
| Widget | `example.html` points to unified path (post E1.9) |

### 4.2 n8n execution

1. **Website Chat Webhook** received POST.
2. **IF enabled** — not 503 `WEBSITE_CHAT_DISABLED`.
3. **Normalize Website Chat** — `correlation_id`, `web:{session_id}` conversation key, `web:…` message id.
4. **POST Backend** — same as Telegram.

### 4.3 Website-specific failures

| Symptom | Check |
|---------|-------|
| 503 on webhook | Kill switch false |
| Session bleed | `external_conversation_id` = `web:{session_id}` — E2.2 conversation lookup |
| CORS / widget | Browser network tab → webhook URL and response `correlation_id` |
| Empty reply | POST Backend `data.reply_to_customer` |

---

## 5. correlation_id visibility map

| Location | Field |
|----------|-------|
| n8n Normalize output | `correlation_id` |
| POST body | `correlation_id` |
| Request header | `X-Correlation-Id` |
| Response body | `correlation_id` |
| `prompt_runs.metadata` | `correlation_id` |
| Langfuse (dev) | trace metadata |
| `message_traces` (future) | column `correlation_id` |

---

## 6. Logs and tables reference

| System | What to inspect | Avoid logging |
|--------|-----------------|---------------|
| n8n execution | Node I/O per stage | Full customer PII dumps |
| Backend uvicorn | HTTP status, error codes | Tokens, prompts |
| `messages` | `conversation_id`, `external_message_id` | `raw_payload` in tickets |
| `prompt_runs` | `latency_ms`, `error`, metadata | `final_prompt` in production tickets |
| `conversations` | `channel`, `status`, `external_conversation_id` | — |
| Langfuse | Trace timeline (dev) | Production secrets |

---

## 7. flow_id (future)

When E2.1+ is live, always record **`flow_key`** from n8n in tickets. Filter:

```sql
SELECT c.id, c.channel, c.external_conversation_id, f.flow_key
FROM conversations c
JOIN flows f ON f.id = c.flow_id
WHERE f.flow_key = 'alpstein_assistant';
```

---

## 8. Escalation checklist

- [ ] `correlation_id` captured
- [ ] n8n execution ID captured
- [ ] `business_id` / channel confirmed
- [ ] POST Backend status + `error.code` if failed
- [ ] `prompt_run_id` or AI error noted
- [ ] Delivery node status noted
- [ ] No secrets pasted in issue

**Related runbooks:** [`n8n-unified-customer-ingress-runbook.md`](n8n-unified-customer-ingress-runbook.md), [`runtime-surface-hardening.md`](runtime-surface-hardening.md)
