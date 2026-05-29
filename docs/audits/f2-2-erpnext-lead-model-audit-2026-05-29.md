# F.2.2 — ERPNext Lead DocType audit

**Site:** `crm.alpstein-ai.ch`  
**Date:** 2026-05-29  
**Method:** `bench --site crm.alpstein-ai.ch console` → `frappe.get_meta("Lead")` / `tabDocField`

## Existing standard fields (relevant)

| fieldname | label | fieldtype | search_index | Notes |
|-----------|-------|-----------|--------------|-------|
| `lead_name` | Full Name | Data | 1 | Tier 5 fallback dedupe |
| `mobile_no` | Mobile No | Data | 0 | Tier 1 dedupe (+ `phone`) |
| `phone` | Phone | Data | 0 | Contact |
| `email_id` | Email | Data | 1 | Tier 2 dedupe |
| `source` | Source | Link | 0 | Lead Source master — not UTM |
| `company_name` | Organization Name | Data | 0 | **Not** Alpstein `business_id` |
| `campaign_name` | Campaign Name | Link | 0 | ERPNext Campaign — not utm string |
| `status` | Status | Select | 1 | Set to `Lead` |
| `language` | Print Language | Link | 0 | **Not** Telegram `language_code` |

**Absent on Lead (v15):** `description`, `utm_*`, Telegram identity, Alpstein IDs.

**Custom fields before F.2.2:** 0

## Candidate Alpstein fields — gap analysis

| Required field | Standard equivalent? | Action |
|----------------|---------------------|--------|
| `alpstein_channel` | No | **Created** |
| `alpstein_business_id` | No (`company_name` ≠ business_id) | **Created** |
| `alpstein_tenant_id` | No | **Created** |
| `alpstein_external_user_id` | No | **Created** |
| `alpstein_chat_id` | No | **Created** |
| `first_touch_*` / `last_touch_*` | No (≠ `campaign_name` Link) | **Created** (5+5) |
| `landing_page`, `referrer_url` | No | **Created** |
| `gclid`, `fbclid` | No | **Created** |
| `telegram_username` | No | **Created** |
| `telegram_language_code` | No (≠ `language`) | **Created** |
| `first_message_at`, `last_message_at` | No | **Created** |
| `conversation_count` | No | **Created** |
| `last_message_channel` | No | **Created** |

## Migration result (2026-05-29)

**29 custom fields created**, 0 skipped (first run).

Script: [`scripts/erpnext/create_alpstein_lead_fields.py`](../../scripts/erpnext/create_alpstein_lead_fields.py)

## Lead Source masters

Created for Link field `source`: `Telegram`, `Website Chat`, `WhatsApp`, `Instagram`.

## API verification (field-based dedupe)

| Check | Result |
|-------|--------|
| POST Lead with custom fields | **PASS** — `CRM-LEAD-2026-00001` |
| GET filter `alpstein_chat_id` + `alpstein_business_id` | **PASS** — 1 row |
