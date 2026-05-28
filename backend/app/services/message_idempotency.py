"""Inbound message deduplication keys (E2.3)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime


def normalize_external_message_id(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def build_inbound_idempotency_key(
    *,
    business_id: uuid.UUID,
    flow_id: uuid.UUID,
    conversation_id: uuid.UUID,
    channel: str,
    external_message_id: str | None,
    message_text: str,
    message_timestamp: datetime | None = None,
) -> str:
    """Stable dedup identity for inbound customer messages within a conversation."""
    normalized_external_id = normalize_external_message_id(external_message_id)
    if normalized_external_id is not None:
        return f"ext:{normalized_external_id}"

    normalized_text = " ".join(message_text.split())
    parts = [
        str(business_id),
        str(flow_id),
        str(conversation_id),
        channel,
        normalized_text,
    ]
    if message_timestamp is not None:
        parts.append(message_timestamp.isoformat())

    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"hash:{digest}"
