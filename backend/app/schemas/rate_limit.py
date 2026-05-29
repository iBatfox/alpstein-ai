"""Rate limit observability API schemas (E3.5c)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

FORBIDDEN_RATE_LIMIT_RESPONSE_FIELDS = frozenset(
    {
        "raw_payload",
        "provider_payload",
        "api_key",
        "secret",
        "bot_token",
        "password",
        "message_text",
        "prompt",
        "system_prompt",
    }
)


class RateLimitViolationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    scope_type: str
    scope_key: str
    channel: str | None = None
    conversation_id: UUID | None = None
    limit_value: int
    window_seconds: int
    window_start: datetime
    observed_count: int
    correlation_id: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            forbidden = FORBIDDEN_RATE_LIMIT_RESPONSE_FIELDS.intersection(data.keys())
            if forbidden:
                raise ValueError(
                    f"Forbidden rate limit response fields: {', '.join(sorted(forbidden))}"
                )
        return data


class RateLimitViolationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RateLimitViolationResponse]
    limit: int
    offset: int


class RateLimitViolationListSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: RateLimitViolationListResponse
