"""Safe logging helpers for Meta WhatsApp webhook intake (no secrets)."""

from __future__ import annotations

from typing import Any


def meta_webhook_log_context(body: dict[str, Any]) -> dict[str, Any]:
    """Extract non-sensitive fields for structured logs."""
    entry = body.get("entry")
    entry_count = len(entry) if isinstance(entry, list) else 0

    messaging_products: list[str] = []
    message_ids: list[str] = []
    fields: list[str] = []

    if isinstance(entry, list):
        for item in entry:
            if not isinstance(item, dict):
                continue
            changes = item.get("changes")
            if not isinstance(changes, list):
                continue
            for change in changes:
                if not isinstance(change, dict):
                    continue
                field = change.get("field")
                if isinstance(field, str) and field:
                    fields.append(field)
                value = change.get("value")
                if not isinstance(value, dict):
                    continue
                product = value.get("messaging_product")
                if isinstance(product, str) and product:
                    messaging_products.append(product)
                messages = value.get("messages")
                if isinstance(messages, list):
                    for message in messages:
                        if isinstance(message, dict):
                            message_id = message.get("id")
                            if isinstance(message_id, str) and message_id:
                                message_ids.append(message_id)
                statuses = value.get("statuses")
                if isinstance(statuses, list):
                    for status in statuses:
                        if isinstance(status, dict):
                            status_id = status.get("id")
                            if isinstance(status_id, str) and status_id:
                                message_ids.append(status_id)

    context: dict[str, Any] = {
        "object": body.get("object") if isinstance(body.get("object"), str) else None,
        "entry_count": entry_count,
    }
    if messaging_products:
        context["messaging_product"] = messaging_products[0]
        if len(set(messaging_products)) > 1:
            context["messaging_products"] = sorted(set(messaging_products))
    if fields:
        context["change_fields"] = sorted(set(fields))
    if message_ids:
        context["message_ids"] = message_ids[:20]
        if len(message_ids) > 20:
            context["message_id_count"] = len(message_ids)
    return context
