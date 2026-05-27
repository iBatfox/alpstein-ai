"""Provider-neutral assembled prompt DTOs (T11.7)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PromptSectionKind = Literal["system", "data"]

CANONICAL_SECTION_ORDER: tuple[str, ...] = (
    "platform_system",
    "task_instructions",
    "tenant_business_context",
    "tenant_behavior",
    "channel_rules",
    "knowledge",
    "conversation_history",
    "current_customer_message",
)

PLATFORM_SECTION_IDS: frozenset[str] = frozenset(
    {
        "platform_system",
        "task_instructions",
    }
)

DATA_SECTION_IDS: frozenset[str] = frozenset(
    set(CANONICAL_SECTION_ORDER) - PLATFORM_SECTION_IDS
)


@dataclass(frozen=True)
class AssembledPromptSection:
    section_id: str
    label: str
    content: str
    kind: PromptSectionKind


@dataclass(frozen=True)
class AssembledPrompt:
    """Logical prompt sections for AI Gateway mapping (not provider messages)."""

    task: str
    sections: tuple[AssembledPromptSection, ...]

    def section_ids(self) -> tuple[str, ...]:
        return tuple(section.section_id for section in self.sections)

    def total_chars(self) -> int:
        return sum(len(section.content) for section in self.sections)
