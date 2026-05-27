"""Typed knowledge DTOs for AI prompt building (T11.5)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class KnowledgeSnippet:
    """Bounded tenant knowledge excerpt for Prompt Builder."""

    id: uuid.UUID
    source_type: str
    title: str | None
    content: str
    tags: dict[str, Any] | list[Any] | None = None
    truncated: bool = False


@dataclass(frozen=True)
class KnowledgeRetrievalResult:
    """Active, tenant-scoped knowledge snippets selected for one AI turn."""

    snippets: tuple[KnowledgeSnippet, ...]

    @classmethod
    def empty(cls) -> KnowledgeRetrievalResult:
        return cls(snippets=())
