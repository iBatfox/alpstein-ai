"""AI reply orchestration result DTOs (T11.11)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class AiReplyResult:
    """Orchestrated AI reply for webhook/lead layers (no final_prompt exposure)."""

    text: str | None
    is_success: bool
    prompt_run_id: uuid.UUID
    model: str
    provider: str
    error: str | None
