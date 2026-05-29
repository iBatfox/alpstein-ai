"""Spam protection observability API schemas (E3.6c)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

FORBIDDEN_SPAM_RESPONSE_FIELDS = frozenset(
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


class SpamDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    rule_id: str
    scope_type: str
    scope_key: str
    channel: str | None = None
    conversation_id: UUID | None = None
    decision: str
    outcome: str
    observed_count: int | None = None
    threshold: int | None = None
    window_seconds: int | None = None
    containment_id: UUID | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            forbidden = FORBIDDEN_SPAM_RESPONSE_FIELDS.intersection(data.keys())
            if forbidden:
                raise ValueError(
                    f"Forbidden spam response fields: {', '.join(sorted(forbidden))}"
                )
        return data


class SpamContainmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    rule_id: str
    scope_type: str
    scope_key: str
    channel: str | None = None
    conversation_id: UUID | None = None
    action: str
    expires_at: datetime
    released_at: datetime | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            forbidden = FORBIDDEN_SPAM_RESPONSE_FIELDS.intersection(data.keys())
            if forbidden:
                raise ValueError(
                    f"Forbidden spam response fields: {', '.join(sorted(forbidden))}"
                )
        return data


class SpamDecisionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SpamDecisionResponse]
    limit: int
    offset: int


class SpamContainmentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SpamContainmentResponse]
    limit: int
    offset: int


class SpamDecisionListSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: SpamDecisionListResponse


class SpamContainmentListSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: SpamContainmentListResponse
