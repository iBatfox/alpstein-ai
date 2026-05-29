"""Normalized payload fingerprint for spam detection (E3.6a)."""

from __future__ import annotations

import hashlib


def normalize_message_text(message_text: str) -> str:
    return " ".join(message_text.split())


def compute_payload_hash(message_text: str) -> str:
    normalized = normalize_message_text(message_text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def payload_hash_prefix(payload_hash: str, *, length: int = 12) -> str:
    return payload_hash[:length]
