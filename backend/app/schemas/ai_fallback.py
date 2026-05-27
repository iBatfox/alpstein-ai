"""AI reply fallback policy DTOs (T11.12)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FallbackDecision:
    """Whether and how to reply when AI output is missing or failed."""

    should_reply: bool
    fallback_text: str | None
    should_handoff: bool
    reason: str
