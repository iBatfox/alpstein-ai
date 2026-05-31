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
LEAD_FIELD_SPECS: list[tuple[str, str, str, str, int, str | None]] = [
    ("alpstein_section", "Alpstein CRM", "Section Break", "company_name", 0, None),
    ("alpstein_channel", "Alpstein Channel", "Data", "alpstein_section", 1, None),
    ("alpstein_business_id", "Alpstein Business ID", "Data", "alpstein_channel", 1, None),
    ("alpstein_tenant_id", "Alpstein Tenant ID", "Data", "alpstein_business_id", 0, None),
    ("alpstein_external_user_id", "Alpstein External User ID", "Data", "alpstein_tenant_id", 1, None),
    ("alpstein_chat_id", "Alpstein Chat ID", "Data", "alpstein_external_user_id", 1, None),
    ("alpstein_instagram_section", "Instagram", "Section Break", "alpstein_chat_id", 0, None),
    ("instagram_username", "Instagram Username", "Data", "alpstein_instagram_section", 0, None),
    ("instagram_display_name", "Instagram Display Name", "Data", "instagram_username", 0, None),
    ("alpstein_attribution_section", "Marketing Attribution", "Section Break", "instagram_display_name", 0, None),
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

COMMUNICATION_FIELD_SPECS: list[tuple[str, str, str, str, int, str | None]] = [
    ("alpstein_section", "Alpstein", "Section Break", "content", 0, None),
    (
        "alpstein_external_message_id",
        "Alpstein External Message ID",
        "Data",
        "alpstein_section",
        1,
        None,
    ),
    ("alpstein_channel", "Alpstein Channel", "Data", "alpstein_external_message_id", 1, None),
    ("alpstein_business_id", "Alpstein Business ID", "Data", "alpstein_channel", 1, None),
    ("alpstein_direction", "Alpstein Direction", "Data", "alpstein_business_id", 0, None),
    ("alpstein_sender_type", "Alpstein Sender Type", "Data", "alpstein_direction", 0, None),
    (
        "alpstein_conversation_id",
        "Alpstein Conversation ID",
        "Data",
        "alpstein_sender_type",
        1,
        None,
    ),
]

LEAD_HISTORY_TAB_FIELD = "alpstein_conversation_history_tab"
LEAD_HISTORY_HTML_FIELD = "alpstein_conversation_history"

LEAD_HISTORY_CLIENT_SCRIPT = r"""
frappe.ui.form.on('Lead', {
  refresh(frm) {
    alpstein_render_conversation_history(frm);
  },
});

function alpstein_escape_html(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function alpstein_format_channel(value) {
  const map = {
    telegram: 'Telegram',
    instagram: 'Instagram',
    whatsapp: 'WhatsApp',
    website_chat: 'Website',
  };
  const key = String(value || '').toLowerCase();
  return map[key] || value || 'Channel';
}

function alpstein_message_side(row) {
  const direction = String(row.alpstein_direction || '').toLowerCase();
  const sender = String(row.alpstein_sender_type || '').toLowerCase();
  if (direction === 'outgoing' || sender === 'ai' || sender === 'owner' || sender === 'operator') {
    return 'right';
  }
  return 'left';
}

function alpstein_render_empty(frm, message) {
  const field = frm.fields_dict.alpstein_conversation_history;
  if (!field) return;
  field.$wrapper.html(
    `<div class="alpstein-chat-empty">${alpstein_escape_html(message)}</div>`
  );
}

function alpstein_render_rows(frm, rows) {
  const field = frm.fields_dict.alpstein_conversation_history;
  if (!field) return;

  if (!rows.length) {
    alpstein_render_empty(frm, 'Нет сообщений');
    return;
  }

  const html = rows
    .map((row) => {
      const side = alpstein_message_side(row);
      const channel = alpstein_format_channel(row.alpstein_channel || row.communication_medium);
      const timestamp = row.communication_date
        ? frappe.datetime.str_to_user(row.communication_date)
        : '';
      return `
        <div class="alpstein-chat-row alpstein-chat-row-${side}">
          <div class="alpstein-chat-bubble">
            <div class="alpstein-chat-meta">
              <span class="alpstein-chat-badge">${alpstein_escape_html(channel)}</span>
              <span>${alpstein_escape_html(timestamp)}</span>
            </div>
            <div class="alpstein-chat-content">${alpstein_escape_html(row.content)}</div>
          </div>
        </div>
      `;
    })
    .join('');

  field.$wrapper.html(`
    <style>
      .alpstein-chat-wrap {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 12px 0;
      }
      .alpstein-chat-row {
        display: flex;
        width: 100%;
      }
      .alpstein-chat-row-left {
        justify-content: flex-start;
      }
      .alpstein-chat-row-right {
        justify-content: flex-end;
      }
      .alpstein-chat-bubble {
        max-width: min(680px, 78%);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 10px 12px;
        background: var(--bg-color);
        overflow-wrap: anywhere;
      }
      .alpstein-chat-row-right .alpstein-chat-bubble {
        background: var(--control-bg);
      }
      .alpstein-chat-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
        color: var(--text-muted);
        font-size: 12px;
      }
      .alpstein-chat-badge {
        border: 1px solid var(--border-color);
        border-radius: 999px;
        padding: 1px 7px;
        color: var(--text-color);
        background: var(--card-bg);
      }
      .alpstein-chat-content {
        white-space: pre-wrap;
        line-height: 1.45;
      }
      .alpstein-chat-empty {
        padding: 12px 0;
        color: var(--text-muted);
      }
    </style>
    <div class="alpstein-chat-wrap">${html}</div>
  `);
}

function alpstein_render_conversation_history(frm) {
  if (!frm.doc || frm.is_new()) {
    alpstein_render_empty(frm, 'Сохраните Lead, чтобы увидеть историю');
    return;
  }

  const field = frm.fields_dict.alpstein_conversation_history;
  if (!field) return;
  alpstein_render_empty(frm, 'Загрузка...');

  frappe.call({
    method: 'frappe.client.get_list',
    args: {
      doctype: 'Communication',
      filters: {
        reference_doctype: 'Lead',
        reference_name: frm.doc.name,
      },
      fields: [
        'name',
        'content',
        'communication_date',
        'communication_medium',
        'sent_or_received',
        'alpstein_external_message_id',
        'alpstein_channel',
        'alpstein_business_id',
        'alpstein_direction',
        'alpstein_sender_type',
        'alpstein_conversation_id',
      ],
      order_by: 'communication_date asc, creation asc',
      limit_page_length: 200,
    },
    callback(response) {
      alpstein_render_rows(frm, response.message || []);
    },
    error() {
      alpstein_render_empty(frm, 'Не удалось загрузить историю переписки');
    },
  });
}
"""

COMMUNICATION_MEDIUM_OPTIONS = "\n".join(
    [
        "",
        "Email",
        "Chat",
        "Phone",
        "SMS",
        "Event",
        "Meeting",
        "Visit",
        "Other",
        "Telegram",
        "Instagram",
        "WhatsApp",
        "Website Chat",
    ]
)


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
    doctype: str,
    fieldname: str,
    label: str,
    fieldtype: str,
    insert_after: str,
    search_index: int = 0,
    options: str | None = None,
) -> str:
    """Return 'created' | 'updated' | 'skipped'."""
    import frappe

    name = f"{doctype}-{fieldname}"
    if not frappe.db.exists("Custom Field", name):
        doc: dict = {
            "doctype": "Custom Field",
            "dt": doctype,
            "fieldname": fieldname,
            "label": label,
            "fieldtype": fieldtype,
            "insert_after": insert_after,
            "search_index": search_index,
            "translatable": 0,
            "hidden": 0,
        }
        if options:
            doc["options"] = options
        if fieldtype == "Int":
            doc["default"] = "0"
        if fieldname == "alpstein_external_message_id":
            doc["length"] = 512

        frappe.get_doc(doc).insert(ignore_permissions=True)
        return "created"

    doc = frappe.get_doc("Custom Field", name)
    changed = False
    for attr, value in (
        ("label", label),
        ("fieldtype", fieldtype),
        ("insert_after", insert_after),
        ("search_index", search_index),
        ("hidden", 0),
    ):
        if getattr(doc, attr) != value:
            setattr(doc, attr, value)
            changed = True
    if fieldname == "alpstein_external_message_id" and getattr(doc, "length", 0) != 512:
        doc.length = 512
        changed = True
    if options is not None and doc.options != options:
        doc.options = options
        changed = True
    if changed:
        doc.save(ignore_permissions=True)
        return "updated"
    return "skipped"


def _lead_history_insert_after() -> str:
    import frappe

    for row in frappe.get_meta("Lead").fields:
        if row.fieldtype in {"Tab Break", "Section Break"} and row.label == "Подробности":
            return row.fieldname
    for fallback in ("notes", "job_title", "company_name"):
        if frappe.get_meta("Lead").get_field(fallback):
            return fallback
    return "lead_name"


def ensure_lead_history_fields() -> dict[str, str]:
    import frappe

    insert_after = _lead_history_insert_after()
    tab_result = ensure_custom_field(
        "Lead",
        LEAD_HISTORY_TAB_FIELD,
        "История переписки",
        "Tab Break",
        insert_after,
        search_index=0,
    )
    html_result = ensure_custom_field(
        "Lead",
        LEAD_HISTORY_HTML_FIELD,
        "История переписки",
        "HTML",
        LEAD_HISTORY_TAB_FIELD,
        search_index=0,
    )
    frappe.clear_cache(doctype="Lead")
    return {
        LEAD_HISTORY_TAB_FIELD: tab_result,
        LEAD_HISTORY_HTML_FIELD: html_result,
    }


def ensure_lead_history_client_script() -> str:
    import frappe

    name = "Alpstein Lead Conversation History"
    if not frappe.db.exists("Client Script", name):
        frappe.get_doc(
            {
                "doctype": "Client Script",
                "name": name,
                "dt": "Lead",
                "view": "Form",
                "enabled": 1,
                "script": LEAD_HISTORY_CLIENT_SCRIPT,
            }
        ).insert(ignore_permissions=True)
        return "created"

    doc = frappe.get_doc("Client Script", name)
    changed = False
    for attr, value in (
        ("dt", "Lead"),
        ("view", "Form"),
        ("enabled", 1),
        ("script", LEAD_HISTORY_CLIENT_SCRIPT),
    ):
        if getattr(doc, attr, None) != value:
            setattr(doc, attr, value)
            changed = True
    if changed:
        doc.save(ignore_permissions=True)
        return "updated"
    return "skipped"


def ensure_communication_medium_options() -> str:
    import frappe
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    field = frappe.get_meta("Communication").get_field("communication_medium")
    existing_options = field.options if field else ""
    if existing_options == COMMUNICATION_MEDIUM_OPTIONS:
        return "skipped"

    make_property_setter(
        "Communication",
        "communication_medium",
        "options",
        COMMUNICATION_MEDIUM_OPTIONS,
        "Text",
        for_doctype=False,
    )
    return "updated" if existing_options else "created"


def main() -> int:
    _init_frappe()
    import frappe

    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []

    frappe.db.begin()
    try:
        for fieldname, label, fieldtype, insert_after, search_index, options in LEAD_FIELD_SPECS:
            result = ensure_custom_field(
                "Lead",
                fieldname,
                label,
                fieldtype,
                insert_after,
                search_index=search_index,
                options=options,
            )
            if result == "created":
                created.append(f"Lead.{fieldname}")
            elif result == "updated":
                updated.append(f"Lead.{fieldname}")
            else:
                skipped.append(f"Lead.{fieldname}")
        for fieldname, label, fieldtype, insert_after, search_index, options in COMMUNICATION_FIELD_SPECS:
            result = ensure_custom_field(
                "Communication",
                fieldname,
                label,
                fieldtype,
                insert_after,
                search_index=search_index,
                options=options,
            )
            if result == "created":
                created.append(f"Communication.{fieldname}")
            elif result == "updated":
                updated.append(f"Communication.{fieldname}")
            else:
                skipped.append(f"Communication.{fieldname}")

        for fieldname, result in ensure_lead_history_fields().items():
            if result == "created":
                created.append(f"Lead.{fieldname}")
            elif result == "updated":
                updated.append(f"Lead.{fieldname}")
            else:
                skipped.append(f"Lead.{fieldname}")

        script_result = ensure_lead_history_client_script()
        if script_result == "created":
            created.append("Client Script.Alpstein Lead Conversation History")
        elif script_result == "updated":
            updated.append("Client Script.Alpstein Lead Conversation History")
        else:
            skipped.append("Client Script.Alpstein Lead Conversation History")

        medium_options_result = ensure_communication_medium_options()
        if medium_options_result == "created":
            created.append("Communication.communication_medium.options")
        elif medium_options_result == "updated":
            updated.append("Communication.communication_medium.options")
        else:
            skipped.append("Communication.communication_medium.options")
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    frappe.clear_cache(doctype="Lead")
    frappe.clear_cache(doctype="Communication")
    summary = {
        "site": SITE,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "created_count": len(created),
        "updated_count": len(updated),
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
