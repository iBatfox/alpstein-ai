# n8n delivery outcome PATCH (E2 post-cutover)

**Workflow:** `alpstein-customer-ingress` (`e1_8_unified_customer_ingress_skeleton.json`)  
**Backend contract:** [`specs/api/api-endpoints.md`](../../specs/api/api-endpoints.md) § observability PATCH  
**Lifecycle:** [`docs/architecture/message-trace-lifecycle.md`](../architecture/message-trace-lifecycle.md)

---

## Purpose

After n8n performs channel transport (Telegram Send / Website Respond), report **`delivered`** or **`failed`** to the backend so `delivery_events` rows move beyond **`pending`**.

n8n does **not** write PostgreSQL directly — only `PATCH /api/v1/observability/deliveries/{delivery_id}`.

---

## Where `delivery_id` is available

| Step | Source |
|------|--------|
| POST Backend success | `$('POST Backend').first().json.data.delivery.delivery_id` |
| Also in response | `delivery_status`, `outbound_message_id` |
| Skipped when | `data.message.is_duplicate === true` or `data.delivery` absent |

The **Prepare Delivery PATCH** Code node reads POST Backend output; it does not depend on Shape Canonical output.

---

## Workflow nodes (E2 wiring)

```text
POST Backend (success)
  → Shape Canonical → channel delivery
       ├─ Telegram Send Message ──┐
       ├─ Respond Website Reply ──┼→ Prepare Delivery PATCH → PATCH Delivery Outcome
       └─ Respond Website Error ──┘
```

| Node | Role |
|------|------|
| **Prepare Delivery PATCH** | Build PATCH body; skip duplicate / missing env / missing delivery_id |
| **PATCH Delivery Outcome** | HTTP PATCH to backend; `continueOnFail` — non-blocking |

---

## Environment variables (names only)

| Variable | Required for PATCH | Notes |
|----------|-------------------|--------|
| `BACKEND_BASE_URL` | Yes | Same as POST Backend |
| `N8N_BACKEND_API_TOKEN` | Yes | Header `X-Alpstein-Webhook-Token` |
| `ALPSTEIN_OBSERVABILITY_TENANT_ID` | Yes | UUID — tenant scope for PATCH query |
| `ALPSTEIN_OBSERVABILITY_BUSINESS_ID` | Yes | UUID — business scope for PATCH query |

Resolve UUIDs for demo business:

```sql
SELECT b.tenant_id, b.id AS business_id, b.external_id
FROM businesses b
WHERE b.external_id = 'alpstein_ai_demo_001';
```

Set in `n8n/.env` (see [`n8n/.env.example`](../../n8n/.env.example)).

If observability env vars are unset, PATCH is **skipped silently** (customer delivery still proceeds).

---

## PATCH payloads

### Successful Telegram send

```json
{
  "status": "delivered",
  "provider_message_id": "12345",
  "provider_status": "sent"
}
```

### Failed Telegram send

```json
{
  "status": "failed",
  "error_type": "telegram_send_failed",
  "error_message": "safe truncated provider error"
}
```

### Successful Website respond

```json
{
  "status": "delivered",
  "provider_message_id": "ai:1735689600000",
  "provider_status": "responded"
}
```

### Failed Website respond (502 path)

```json
{
  "status": "failed",
  "error_type": "website_chat_delivery_failed",
  "error_message": "safe truncated message"
}
```

**Endpoint:**

```http
PATCH /api/v1/observability/deliveries/{delivery_id}?tenant_id={uuid}&business_id={uuid}
X-Alpstein-Webhook-Token: {N8N_BACKEND_API_TOKEN}
```

---

## Duplicate inbound safety

When backend returns `message.is_duplicate: true`, **no new** `delivery_events` row is created and **Prepare Delivery PATCH returns empty** — no PATCH call.

Re-PATCH of an already-`delivered` row is idempotent on the backend (`mark_delivered` no-op).

---

## If PATCH fails

| Scenario | Customer impact | Ops state |
|----------|-----------------|-----------|
| PATCH HTTP error / timeout | None — reply already sent | `delivery_events.status` stays **`pending`** |
| Missing observability env | None | PATCH skipped |
| Wrong tenant/business UUID | PATCH 404 | pending until corrected + manual PATCH |

**Retry guidance:** Do not auto-retry PATCH in n8n (avoid storms). Ops may manually PATCH or replay from observability tools once root cause fixed.

**Pending is expected** until n8n reports outcome or ops intervenes.

---

## Rollout

1. Set `ALPSTEIN_OBSERVABILITY_TENANT_ID` + `ALPSTEIN_OBSERVABILITY_BUSINESS_ID` in n8n env.
2. Import updated export (`versionId`: `e2-delivery-outcome-patch-v1`).
3. Re-bind credentials if import reset bindings.
4. Restart n8n if activation changed.
5. Smoke: Website POST + Telegram inject; verify `GET …/deliveries/{id}` → `delivered`.

Regenerate export:

```bash
python3 scripts/n8n/build_e1_8_unified_workflow.py
scripts/n8n/export-scrub.sh
```

---

## Rollback

1. Re-import pre-E2 workflow export from [`docs/ops/backups/e1-9-cutover-2026-05-28/`](../../docs/ops/backups/e1-9-cutover-2026-05-28/) (`versionId`: `e1.9-unified-customer-ingress-v1`).
2. Restart n8n.
3. Deliveries remain **`pending`** until manually updated — no data corruption.

---

## Validation checklist

- [ ] POST Backend returns `data.delivery.delivery_id` on non-duplicate AI reply
- [ ] Telegram path: execution shows **Prepare Delivery PATCH** + **PATCH Delivery Outcome**
- [ ] Website path: same after **Respond Website Reply**
- [ ] `GET /api/v1/observability/deliveries/{id}` → `status: delivered` or `failed`
- [ ] Duplicate inbound: no PATCH node output
- [ ] Customer reply unchanged (PATCH is parallel tail)

---

## Related

- [`n8n-unified-customer-ingress-runbook.md`](../ops/n8n-unified-customer-ingress-runbook.md)
- [`e2-observability-verification.md`](../audits/e2-observability-verification.md)
- [`tasks/done/T-e2.6-delivery-visibility.md`](../../tasks/done/T-e2.6-delivery-visibility.md)
