"""MVP keyword heuristics for urgent and human-handoff signals (T12.4).

Detection is case-insensitive and deterministic. Multi-word phrases use substring
matching on normalized text; single-token keywords use word boundaries to limit
obvious false positives (e.g. ``person`` inside ``personal``).

False-positive risk (accepted for MVP):
- Short tokens such as ``now`` or ``today`` can match unrelated scheduling text.
- ``human`` / ``manager`` can appear in non-handoff business wording.
- No multilingual (DE/FR) coverage; no LLM or configurable keyword tables.

``ai_reply_text`` and ``fallback_error`` are accepted for future wire-up but are
not scanned in T12.4 — only ``customer_message_text`` is analyzed.
"""

from __future__ import annotations

import re

from app.schemas.lead_signal import LeadSignalDetectionResult

REASON_HANDOFF_PREFIX = "handoff_keyword"
REASON_URGENT_PREFIX = "urgent_keyword"

# Longer phrases first so matching stays predictable (e.g. "call me" before "call").
_HANDOFF_PHRASES: tuple[str, ...] = (
    "speak to someone",
    "talk to someone",
    "call me",
)

_HANDOFF_WORDS: tuple[str, ...] = (
    "human",
    "manager",
    "person",
)

_URGENT_WORDS: tuple[str, ...] = (
    "asap",
    "emergency",
    "immediately",
    "urgent",
    "today",
    "now",
)


class LeadSignalDetectionService:
    def detect(
        self,
        *,
        customer_message_text: str,
        ai_reply_text: str | None = None,
        fallback_error: str | None = None,
    ) -> LeadSignalDetectionResult:
        del ai_reply_text, fallback_error  # reserved for T12.6 wire-up

        normalized = _normalize_text(customer_message_text)
        if not normalized:
            return LeadSignalDetectionResult(
                urgent_detected=False,
                handoff_requested=False,
                matched_keywords=[],
                reasons=[],
            )

        handoff_matches = _collect_handoff_matches(normalized)
        urgent_matches = _collect_urgent_matches(normalized)

        matched_keywords = handoff_matches + urgent_matches
        reasons = [
            f"{REASON_HANDOFF_PREFIX}:{keyword}"
            for keyword in handoff_matches
        ] + [
            f"{REASON_URGENT_PREFIX}:{keyword}"
            for keyword in urgent_matches
        ]

        return LeadSignalDetectionResult(
            urgent_detected=bool(urgent_matches),
            handoff_requested=bool(handoff_matches),
            matched_keywords=matched_keywords,
            reasons=reasons,
        )


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def _collect_handoff_matches(normalized_text: str) -> list[str]:
    matches: list[str] = []
    for phrase in _HANDOFF_PHRASES:
        if phrase in normalized_text:
            matches.append(phrase)
    for word in _HANDOFF_WORDS:
        if _contains_word(normalized_text, word):
            matches.append(word)
    return matches


def _collect_urgent_matches(normalized_text: str) -> list[str]:
    matches: list[str] = []
    for word in _URGENT_WORDS:
        if _contains_word(normalized_text, word):
            matches.append(word)
    return matches


def _contains_word(normalized_text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", normalized_text) is not None
