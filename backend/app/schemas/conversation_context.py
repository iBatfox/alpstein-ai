"""Typed conversation history DTOs for Prompt Builder (T11.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ConversationHistoryMessage:
    """Prompt-safe message excerpt (no transport or AI internals)."""

    sender_type: str
    message_text: str
    created_at: datetime


@dataclass(frozen=True)
class ConversationHistory:
    """Recent conversation messages ordered oldest → newest for prompt context."""

    messages: tuple[ConversationHistoryMessage, ...]

    @classmethod
    def empty(cls) -> ConversationHistory:
        return cls(messages=())
