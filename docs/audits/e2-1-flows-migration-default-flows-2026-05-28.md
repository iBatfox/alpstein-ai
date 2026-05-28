# E2.1 — Flows migration + default flows

**Date:** 2026-05-28  
**Verdict:** **PASS WITH NOTES**

## Summary

E2.1 adds the `flows` table, backfills one default flow per business, and resolves flow identity on `POST /api/v1/webhook/message` without changing conversation/message persistence or n8n ingress.

## Migration

| Item | Value |
|------|--------|
| Revision | `0008` (`0008_create_flows.py`) |
| Parent | `0007` |
| Table | `flows` |

### Columns

`id`, `tenant_id`, `business_id`, `flow_key`, `flow_name`, `status`, `is_default`, `metadata`, `created_at`, `updated_at`

### Constraints / indexes

- `UNIQUE (business_id, flow_key)` — `flows_business_flow_key_unique`
- Partial unique: one `is_default=true` per business — `flows_business_default_unique`
- FKs: `tenant_id` → `tenants`, `business_id` → `businesses`
- Indexes: `flows_tenant_id_idx`, `flows_business_id_idx`, `flows_status_idx`

### Backfill

- Demo rows with fixed UUIDs for `demo_barbershop_001` and `alpstein_ai_demo_001`
- All other businesses: `flow_key=default`, `is_default=true`, deterministic `uuid5` id

## Flow resolution

| Input | Behavior |
|-------|----------|
| `flow_key` omitted or blank | Active flow with `is_default=true` for `(tenant_id, business_id)` |
| `flow_key` provided | Must exist for business; else **404** `FLOW_NOT_FOUND` |
| Success response | `data.flow: { id, flow_key }` always present |

Conversation service still uses **customer + channel** only (no `flow_id` on conversations).

## Validation run

| Check | Result |
|-------|--------|
| `alembic upgrade head` (compose DB) | OK (`0007` → `0008`) |
| `GET /api/v1/health/ready` | 200 |
| pytest `backend/tests/` | **400 passed** |
| Telegram path smoke (`alpstein_ai_demo_001`) | 200; `flow_key=default` |
| Website Chat smoke (`demo_barbershop_001`) | 200; `flow_key=barbershop_default` |
| Unknown `flow_key` | 404 `FLOW_NOT_FOUND` |

## Files (primary)

- `backend/alembic/versions/0008_create_flows.py`
- `backend/app/models/flow.py`
- `backend/app/services/flow_service.py`
- `backend/app/services/webhook_message_service.py`
- `backend/app/schemas/webhook.py`, `webhook_response.py`
- `backend/app/api/routes/webhook.py`
- `backend/tests/test_flow_service.py` (+ webhook test updates)

## Risks / open questions

1. **Image drift:** Running `alpstein_backend` image may not include `0008` or flow code until `docker compose build backend` — migration was validated via `docker cp` + restart for this audit only.
2. **Spec vs task keys:** Task mentioned `alpstein_demo` / `barbershop_demo`; implemented keys match E2.0 bridge table (`default`, `barbershop_default`).
3. **`database-schema.md`:** Not updated; architect may add `flows` entity in a follow-up doc sync.
4. **Backward compatibility:** New `data.flow` field is additive; clients ignoring it are unaffected.

## Next

- **E2.2:** `conversations.flow_id` (nullable → backfill → NOT NULL)
- **E2.3:** Flow-scoped message idempotency index
- **E2.6:** n8n passes `flow_key` explicitly
