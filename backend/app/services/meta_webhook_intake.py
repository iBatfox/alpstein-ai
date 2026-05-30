"""Safe logging helpers for Meta webhook intake (WhatsApp + Instagram; no secrets)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MAX_LOG_TEXT_LEN = 200
_MAX_INSTAGRAM_MESSAGES_LOGGED = 20
_SENSITIVE_PAYLOAD_KEYS = frozenset(
    {
        "access_token",
        "app_secret",
        "client_secret",
        "token",
        "password",
        "secret",
        "authorization",
        "x-hub-signature",
        "x-hub-signature-256",
    }
)
_NON_MESSAGE_INSTAGRAM_CHANGE_FIELDS = frozenset(
    {
        "messaging_seen",
        "read",
        "delivery",
        "message_reads",
    }
)


@dataclass(frozen=True)
class InstagramInboundMessage:
    sender_id: str
    message_id: str
    message_text: str
    message_type: str | None = None
    raw_event_type: str = ""
    event_timestamp: str | None = None


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
                singular_message = value.get("message")
                if isinstance(singular_message, dict):
                    message_id = singular_message.get("mid") or singular_message.get("id")
                    if isinstance(message_id, str) and message_id:
                        message_ids.append(message_id)
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

    instagram_messages = extract_instagram_inbound_messages(body)
    if instagram_messages:
        if "message_ids" not in context:
            context["message_ids"] = [
                message.message_id for message in instagram_messages[:20]
            ]
            if len(instagram_messages) > 20:
                context["message_id_count"] = len(instagram_messages)
        context["instagram_inbound"] = [
            _instagram_message_log_entry(message) for message in instagram_messages
        ]
        if len(instagram_messages) > _MAX_INSTAGRAM_MESSAGES_LOGGED:
            context["instagram_inbound_count"] = len(instagram_messages)

    return context


def extract_instagram_inbound_messages(body: dict[str, Any]) -> list[InstagramInboundMessage]:
    """Parse inbound Instagram DM fields from a Meta webhook POST body."""
    results: list[InstagramInboundMessage] = []
    obj = body.get("object")
    is_instagram_object = obj == "instagram"

    entry = body.get("entry")
    if not isinstance(entry, list):
        return results

    for item in entry:
        if not isinstance(item, dict):
            continue
        changes = item.get("changes")
        if isinstance(changes, list):
            for change in changes:
                if not isinstance(change, dict):
                    continue
                field = change.get("field")
                if isinstance(field, str) and field in _NON_MESSAGE_INSTAGRAM_CHANGE_FIELDS:
                    continue
                value = change.get("value")
                if not isinstance(value, dict):
                    continue
                if isinstance(field, str) and field == "messages":
                    if isinstance(value.get("message"), dict):
                        parsed = _parse_instagram_changes_value_message(value)
                        if parsed is not None:
                            results.append(parsed)
                            continue
                product = value.get("messaging_product")
                if product != "instagram" and not is_instagram_object:
                    continue
                messages = value.get("messages")
                if isinstance(messages, list):
                    for message in messages:
                        parsed = _parse_cloud_api_message(message)
                        if parsed is not None:
                            results.append(parsed)

        if is_instagram_object:
            messaging = item.get("messaging")
            if isinstance(messaging, list):
                for event in messaging:
                    parsed = _parse_messaging_event(event)
                    if parsed is not None:
                        results.append(parsed)

    return results


def instagram_payload_shape_diagnostic(body: dict[str, Any]) -> dict[str, Any]:
    """Safe structural snapshot when Instagram parser finds no inbound messages."""
    entry = body.get("entry")
    entry_count = len(entry) if isinstance(entry, list) else 0
    top_level_keys = [
        key
        for key in sorted(body.keys())
        if isinstance(key, str) and key.lower() not in _SENSITIVE_PAYLOAD_KEYS
    ]

    entries: list[dict[str, Any]] = []
    if isinstance(entry, list):
        for item in entry:
            entries.append(_instagram_entry_shape(item))

    return {
        "top_level_keys": top_level_keys,
        "entry_count": entry_count,
        "entries": entries,
    }


def instagram_unparsed_message_values_for_log(body: dict[str, Any]) -> list[dict[str, Any]]:
    """Return redacted changes[].value payloads for unparsed Instagram message events."""
    values: list[dict[str, Any]] = []
    entry = body.get("entry")
    if not isinstance(entry, list):
        return values

    for item in entry:
        if not isinstance(item, dict):
            continue
        changes = item.get("changes")
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, dict):
                continue
            if change.get("field") != "messages":
                continue
            value = change.get("value")
            if isinstance(value, dict):
                redacted = redact_meta_payload_for_log(value)
                if isinstance(redacted, dict):
                    values.append(redacted)

    return values


def redact_meta_payload_for_log(payload: Any) -> Any:
    """Recursively omit secret-looking keys while preserving diagnostic structure."""
    if isinstance(payload, dict):
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            key_text = str(key)
            if key_text.lower() in _SENSITIVE_PAYLOAD_KEYS:
                continue
            redacted[key_text] = redact_meta_payload_for_log(value)
        return redacted
    if isinstance(payload, list):
        return [redact_meta_payload_for_log(item) for item in payload]
    return payload


def _instagram_entry_shape(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {"entry_type": type(item).__name__}

    entry_diag: dict[str, Any] = {
        "entry_keys": sorted(str(key) for key in item.keys()),
    }
    entry_id = item.get("id")
    if isinstance(entry_id, str):
        entry_diag["entry_id"] = entry_id
    elif entry_id is not None:
        entry_diag["entry_id_present"] = True

    messaging = item.get("messaging")
    entry_diag["has_messaging"] = isinstance(messaging, list)
    if isinstance(messaging, list):
        entry_diag["messaging_items"] = [
            _instagram_messaging_item_shape(event) for event in messaging
        ]

    changes = item.get("changes")
    if isinstance(changes, list):
        entry_diag["changes"] = [
            _instagram_change_shape(change) for change in changes
        ]

    return entry_diag


def _instagram_messaging_item_shape(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        return {"messaging_item_type": type(event).__name__}

    item_diag: dict[str, Any] = {
        "messaging_item_keys": sorted(str(key) for key in event.keys()),
    }
    sender = event.get("sender")
    if isinstance(sender, dict) and isinstance(sender.get("id"), str):
        item_diag["sender_id"] = sender["id"]
    recipient = event.get("recipient")
    if isinstance(recipient, dict) and isinstance(recipient.get("id"), str):
        item_diag["recipient_id"] = recipient["id"]

    message = event.get("message")
    if isinstance(message, dict):
        item_diag["message_keys"] = sorted(str(key) for key in message.keys())
        mid = message.get("mid")
        if isinstance(mid, str):
            item_diag["message_mid"] = mid
        item_diag["has_message_text"] = "text" in message

    return item_diag


def _instagram_change_shape(change: Any) -> dict[str, Any]:
    if not isinstance(change, dict):
        return {"change_type": type(change).__name__}

    change_diag: dict[str, Any] = {
        "change_keys": sorted(str(key) for key in change.keys()),
    }
    field = change.get("field")
    if isinstance(field, str):
        change_diag["field"] = field

    value = change.get("value")
    if isinstance(value, dict):
        change_diag["value_keys"] = sorted(str(key) for key in value.keys())

    return change_diag


def _instagram_message_log_entry(message: InstagramInboundMessage) -> dict[str, Any]:
    text = message.message_text
    entry: dict[str, Any] = {
        "sender_id": message.sender_id,
        "message_id": message.message_id,
        "message_text": safe_message_text_for_log(text),
    }
    if len(text) > _MAX_LOG_TEXT_LEN:
        entry["message_text_length"] = len(text)
    if message.message_type:
        entry["message_type"] = message.message_type
    return entry


def safe_message_text_for_log(text: str, *, max_len: int = _MAX_LOG_TEXT_LEN) -> str:
    """Truncate inbound message text for logs; never alter IDs elsewhere."""
    stripped = text.strip()
    if len(stripped) <= max_len:
        return stripped
    return f"{stripped[:max_len]}…"


def _extract_actor_id(actor: Any) -> str | None:
    if isinstance(actor, str) and actor.strip():
        return actor.strip()
    if isinstance(actor, int):
        return str(actor)
    if isinstance(actor, dict):
        actor_id = actor.get("id")
        if isinstance(actor_id, str) and actor_id.strip():
            return actor_id.strip()
        if isinstance(actor_id, int):
            return str(actor_id)
    return None


def _parse_instagram_changes_value_message(
    value: dict[str, Any],
) -> InstagramInboundMessage | None:
    """Real Instagram DM: changes[].value with sender, recipient, message."""
    message = value.get("message")
    if not isinstance(message, dict):
        return None
    if message.get("is_echo") is True:
        return None
    if message.get("is_deleted") is True:
        return None

    sender_id = _extract_actor_id(value.get("sender"))
    if not sender_id:
        return None

    message_id = message.get("mid") or message.get("id")
    if not isinstance(message_id, str) or not message_id.strip():
        timestamp = _extract_timestamp(value.get("timestamp"))
        if timestamp is None:
            return None
        message_id = f"instagram:{sender_id}:{timestamp}"

    message_type = message.get("type")
    type_str = message_type if isinstance(message_type, str) else None
    message_text = _extract_text_body(message)
    if not message_text.strip():
        return None
    return InstagramInboundMessage(
        sender_id=sender_id,
        message_id=message_id.strip(),
        message_text=message_text,
        message_type=type_str,
        raw_event_type="changes.value.message",
        event_timestamp=_extract_timestamp(value.get("timestamp")),
    )


def _extract_timestamp(timestamp: Any) -> str | None:
    if isinstance(timestamp, bool):
        return None
    if isinstance(timestamp, int):
        return str(timestamp)
    if isinstance(timestamp, str) and timestamp.strip():
        return timestamp.strip()
    return None


def _parse_cloud_api_message(message: Any) -> InstagramInboundMessage | None:
    if not isinstance(message, dict):
        return None
    if message.get("is_echo") is True:
        return None
    if message.get("is_deleted") is True:
        return None
    sender_id = message.get("from")
    message_id = message.get("id")
    if not isinstance(sender_id, str) or not sender_id.strip():
        return None
    if not isinstance(message_id, str) or not message_id.strip():
        return None

    message_type = message.get("type")
    type_str = message_type if isinstance(message_type, str) else None
    message_text = _extract_text_body(message)
    if not message_text.strip():
        return None
    return InstagramInboundMessage(
        sender_id=sender_id.strip(),
        message_id=message_id.strip(),
        message_text=message_text,
        message_type=type_str,
        raw_event_type="changes.value.messages",
        event_timestamp=_extract_timestamp(message.get("timestamp")),
    )


def _parse_messaging_event(event: Any) -> InstagramInboundMessage | None:
    if not isinstance(event, dict):
        return None
    if "read" in event or "delivery" in event:
        return None

    message = event.get("message")
    if not isinstance(message, dict):
        return None
    if message.get("is_echo") is True:
        return None
    if message.get("is_deleted") is True:
        return None

    sender_id = _extract_actor_id(event.get("sender"))
    recipient_id = _extract_actor_id(event.get("recipient"))
    message_id = _extract_message_id(message)
    if not sender_id:
        return None
    if not recipient_id:
        return None
    if not message_id:
        return None

    message_text = _extract_text_body(message)
    if not message_text.strip():
        return None
    return InstagramInboundMessage(
        sender_id=sender_id,
        message_id=message_id,
        message_text=message_text,
        message_type=None,
        raw_event_type="entry.messaging",
        event_timestamp=_extract_timestamp(event.get("timestamp")),
    )


def _extract_message_id(message: dict[str, Any]) -> str | None:
    message_id = message.get("mid") or message.get("id")
    if isinstance(message_id, str) and message_id.strip():
        return message_id.strip()
    if isinstance(message_id, int):
        return str(message_id)
    return None


def _extract_text_body(message: dict[str, Any]) -> str:
    text_field = message.get("text")
    if isinstance(text_field, dict):
        body = text_field.get("body")
        if isinstance(body, str):
            return body
    if isinstance(text_field, str):
        return text_field
    return ""


def should_log_instagram_payload_shape(
    body: dict[str, Any],
    *,
    accepted_count: int,
    duplicate_count: int,
) -> bool:
    """Log payload shape only for unrecognized Instagram message field structures."""
    if accepted_count or duplicate_count:
        return False
    for change in _iter_instagram_changes(body):
        if change.get("field") != "messages":
            continue
        value = change.get("value")
        if not isinstance(value, dict):
            return True
        if "message" in value or "messages" in value:
            return False
        return True
    return False


def _iter_instagram_changes(body: dict[str, Any]) -> list[dict[str, Any]]:
    changes_out: list[dict[str, Any]] = []
    entry = body.get("entry")
    if not isinstance(entry, list):
        return changes_out
    for item in entry:
        if not isinstance(item, dict):
            continue
        changes = item.get("changes")
        if isinstance(changes, list):
            for change in changes:
                if isinstance(change, dict):
                    changes_out.append(change)
    return changes_out
