"""Conversation intent policy DTOs (CIP-A — detection only)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ConversationIntent(StrEnum):
    """Customer need for the current turn (heuristic routing)."""

    SOCIAL_GREETING = "social_greeting"
    TECHNICAL_INTEREST = "technical_interest"
    IMPLEMENTATION_INTEREST = "implementation_interest"
    PRICING_INTEREST = "pricing_interest"
    UNSUPPORTED_SYSTEM = "unsupported_system"
    CONFUSED_CUSTOMER = "confused_customer"
    OFF_TOPIC = "off_topic"


@dataclass(frozen=True)
class ConversationIntentResolution:
    """Result of rule-based intent detection for one customer turn."""

    intent: ConversationIntent
    matched_rule: str
    used_previous_message: bool = False
