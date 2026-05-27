"""Greeting orchestration DTOs (MVP)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GreetingMode(StrEnum):
    """How the assistant should open this reply."""

    FIRST_CONTACT = "first_contact"
    FOLLOW_UP = "follow_up"
    SOFT_RETURN = "soft_return"


SUPPORTED_GREETING_LANGUAGE_CODES = frozenset(
    {"de", "en", "ru", "fr", "it", "es", "uk"}
)


@dataclass(frozen=True)
class GreetingPolicy:
    mode: GreetingMode
    reply_language_code: str
    reply_language_name: str
