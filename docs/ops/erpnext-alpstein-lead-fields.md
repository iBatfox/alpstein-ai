# ERPNext — Alpstein Lead custom fields (F.2.2)

**DocType:** `Lead`  
**Site:** `crm.alpstein-ai.ch`  
**Migration script:** [`scripts/erpnext/create_alpstein_lead_fields.py`](../../scripts/erpnext/create_alpstein_lead_fields.py)

## Purpose

Structured CRM fields for n8n ERPNext Lead sync. Replaces description-text dedupe markers (F.2.1).

Alpstein PostgreSQL remains source of truth. These fields are **CRM copy metadata only**.

## Run migration (operator)

```bash
cd /opt/alpstein-ai
docker cp scripts/erpnext/create_alpstein_lead_fields.py \
  alpstein-erpnext-backend-1:/tmp/create_alpstein_lead_fields.py
cd /opt/alpstein-erpnext
export COMPOSE_FILE="compose.yaml:overrides/compose.mariadb.yaml:overrides/compose.redis.yaml:compose.alpstein.override.yaml"
docker compose -p alpstein-erpnext exec -T backend \
  /home/frappe/frappe-bench/env/bin/python /tmp/create_alpstein_lead_fields.py
```

Safe to re-run: existing Custom Field records are skipped.

## Fields created

| Group | Fieldnames |
|-------|------------|
| Identity | `alpstein_channel`, `alpstein_business_id`, `alpstein_tenant_id`, `alpstein_external_user_id`, `alpstein_chat_id` |
| First touch | `first_touch_source`, `first_touch_medium`, `first_touch_campaign`, `first_touch_content`, `first_touch_term` |
| Last touch | `last_touch_source`, `last_touch_medium`, `last_touch_campaign`, `last_touch_content`, `last_touch_term` |
| URLs / click IDs | `landing_page`, `referrer_url`, `gclid`, `fbclid` |
| Telegram | `telegram_username`, `telegram_language_code` |
| Instagram | `instagram_username`, `instagram_display_name` |
| Operations | `first_message_at`, `last_message_at`, `conversation_count`, `last_message_channel` |

Indexed (`search_index=1`) for API filters: `alpstein_channel`, `alpstein_business_id`, `alpstein_external_user_id`, `alpstein_chat_id`.

## Standard Lead fields used (not duplicated)

| ERPNext field | Use |
|---------------|-----|
| `mobile_no` / `phone` | Phone dedupe tier 1 |
| `email_id` | Email dedupe tier 2 |
| `lead_name` | Display name; tier 5 fallback |
| `source` | Lead Source link (Telegram, Website Chat, …) |
| `status` | `Lead` |

**Not used:** `company_name` for `business_id` (was F.2.1 anti-pattern). Use `alpstein_business_id`.

**Not used for dedupe:** `description` (not on Lead form in ERPNext v15).

## Dedupe (n8n)

See [`n8n-erpnext-lead-sync.md`](n8n-erpnext-lead-sync.md) § Dedupe order (F.2.2).

## Evidence

| Date | Action | Result |
|------|--------|--------|
| | Migration run | |
| | `bench` meta field count | |
