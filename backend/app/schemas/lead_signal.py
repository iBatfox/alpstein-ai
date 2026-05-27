"""Lead urgency and handoff signal DTOs (T12.4)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LeadSignalDetectionResult:
    """Keyword-based signals derived from customer message text (MVP)."""

    urgent_detected: bool
    handoff_requested: bool
    matched_keywords: list[str]
    reasons: list[str]
