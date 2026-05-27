"""AI reply orchestration ingress outcomes (T11.13)."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.ai_reply import AiReplyResult


@dataclass(frozen=True)
class AiReplyOrchestrationOutcome:
    """Result of running (or skipping) the AI reply chain for one incoming message."""

    is_duplicate: bool
    ai_executed: bool
    reason: str
    ai_reply: AiReplyResult | None
