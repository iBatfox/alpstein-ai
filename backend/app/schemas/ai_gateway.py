"""Normalized AI Gateway result DTOs (T11.8)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiGatewayResult:
    """Provider-independent AI execution result for orchestration and PromptRun."""

    text: str | None
    model: str
    provider: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    error: str | None

    @property
    def succeeded(self) -> bool:
        return self.error is None and self.text is not None and self.text.strip() != ""
