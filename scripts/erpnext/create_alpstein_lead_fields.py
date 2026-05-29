#!/usr/bin/env python3
"""
Idempotent ERPNext Lead custom fields for Alpstein CRM sync (F.2.2).

Run on ERPNext bench host (Docker backend container):

  docker cp scripts/erpnext/create_alpstein_lead_fields.py \\
    alpstein-erpnext-backend-1:/tmp/create_alpstein_lead_fields.py
  docker compose -p alpstein-erpnext exec -T backend \\
    /home/frappe/frappe-bench/env/bin/python /tmp/create_alpstein_lead_fields.py

Requires: frappe site initialized (crm.alpstein-ai.ch).
Does not modify Alpstein PostgreSQL.
"""
from __future__ import annotations

import json
import os
import sys

SITE = os.environ.get("FRAPPE_SITE", "crm.alpstein-ai.ch")
BENCH_SITES_PATH = os.environ.get("FRAPPE_SITES_PATH", "/home/frappe/frappe-bench/sites")

# (fieldname, label, fieldtype, insert_after, search_index, options)
FIELD_SPECS: list[tuple[str, str, str, str, int, str | None]] = [
    ("alpstein_section", "Alpstein CRM", "Section Break", "company_name", 0, None),
    ("alpstein_channel", "Alpstein Channel", "Data", "alpstein_section", 1, None),
    ("alpstein_business_id", "Alpstein Business ID", "Data", "alpstein_channel", 1, None),
    ("alpstein_tenant_id", "Alpstein Tenant ID", "Data", "alpstein_business_id", 0, None),
    ("alpstein_external_user_id", "Alpstein External User ID", "Data", "alpstein_tenant_id", 1, None),
    ("alpstein_chat_id", "Alpstein Chat ID", "Data", "alpstein_external_user_id", 1, None),
    ("alpstein_attribution_section", "Marketing Attribution", "Section Break", "alpstein_chat_id", 0, None),
    ("first_touch_source", "First Touch Source", "Data", "alpstein_attribution_section", 0, None),
    ("first_touch_medium", "First Touch Medium", "Data", "first_touch_source", 0, None),
    ("first_touch_campaign", "First Touch Campaign", "Data", "first_touch_medium", 0, None),
    ("first_touch_content", "First Touch Content", "Data", "first_touch_campaign", 0, None),
    ("first_touch_term", "First Touch Term", "Data", "first_touch_content", 0, None),
    ("last_touch_source", "Last Touch Source", "Data", "first_touch_term", 0, None),
    ("last_touch_medium", "Last Touch Medium", "Data", "last_touch_source", 0, None),
    ("last_touch_campaign", "Last Touch Campaign", "Data", "last_touch_medium", 0, None),
    ("last_touch_content", "Last Touch Content", "Data", "last_touch_campaign", 0, None),
    ("last_touch_term", "Last Touch Term", "Data", "last_touch_content", 0, None),
    ("landing_page", "Landing Page", "Data", "last_touch_term", 0, None),
    ("referrer_url", "Referrer URL", "Data", "landing_page", 0, None),
    ("gclid", "Google Click ID", "Data", "referrer_url", 0, None),
    ("fbclid", "Facebook Click ID", "Data", "gclid", 0, None),
    ("alpstein_telegram_section", "Telegram", "Section Break", "fbclid", 0, None),
    ("telegram_username", "Telegram Username", "Data", "alpstein_telegram_section", 0, None),
    ("telegram_language_code", "Telegram Language Code", "Data", "telegram_username", 0, None),
    ("alpstein_ops_section", "Alpstein Operations", "Section Break", "telegram_language_code", 0, None),
    ("first_message_at", "First Message At", "Datetime", "alpstein_ops_section", 0, None),
    ("last_message_at", "Last Message At", "Datetime", "first_message_at", 0, None),
    ("conversation_count", "Conversation Count", "Int", "last_message_at", 0, None),
    ("last_message_channel", "Last Message Channel", "Data", "conversation_count", 0, None),
]


def _init_frappe() -> None:
    import frappe

    if frappe.db:
        return
    bench_root = os.environ.get("FRAPPE_BENCH_PATH", "/home/frappe/frappe-bench")
    os.chdir(bench_root)
    frappe.init(site=SITE, sites_path=os.path.join(bench_root, "sites"))
    frappe.connect()
    frappe.flags.ignore_permissions = True


def ensure_custom_field(
    fieldname: str,
    label: str,
    fieldtype: str,
    insert_after: str,
    search_index: int = 0,
    options: str | None = None,
) -> str:
    """Return 'created' | 'skipped'."""
    import frappe

    name = f"Lead-{fieldname}"
    if frappe.db.exists("Custom Field", name):
        return "skipped"

    doc: dict = {
        "doctype": "Custom Field",
        "dt": "Lead",
        "fieldname": fieldname,
        "label": label,
        "fieldtype": fieldtype,
        "insert_after": insert_after,
        "search_index": search_index,
        "translatable": 0,
    }
    if options:
        doc["options"] = options
    if fieldtype == "Int":
        doc["default"] = "0"

    frappe.get_doc(doc).insert(ignore_permissions=True)
    return "created"


def main() -> int:
    _init_frappe()
    import frappe

    created: list[str] = []
    skipped: list[str] = []

    frappe.db.begin()
    try:
        for fieldname, label, fieldtype, insert_after, search_index, options in FIELD_SPECS:
            result = ensure_custom_field(
                fieldname,
                label,
                fieldtype,
                insert_after,
                search_index=search_index,
                options=options,
            )
            if result == "created":
                created.append(fieldname)
            else:
                skipped.append(fieldname)
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    frappe.clear_cache(doctype="Lead")
    summary = {
        "site": SITE,
        "created": created,
        "skipped": skipped,
        "created_count": len(created),
        "skipped_count": len(skipped),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from exc
