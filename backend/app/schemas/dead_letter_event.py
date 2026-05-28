"""Dead-letter observability API schemas (E3.2c)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FORBIDDEN_DEAD_LETTER_RESPONSE_FIELDS = frozenset(
    {
        "raw_payload",
        "provider_payload",
        "api_key",
        "secret",
        "bot_token",
        "password",
    }
)


class DeadLetterEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    business_id: str
    flow_id: str | None = None
    conversation_id: str | None = None
    trace_id: str | None = None
    delivery_id: str | None = None
    inbound_message_id: str | None = None
    outbound_message_id: str | None = None
    scope_type: str
    scope_id: str
    event_type: str
    failure_reason: str
    error_type: str | None = None
    retry_count: int
    correlation_id: str | None = None
    metadata: dict[str, Any] | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    last_seen_at: datetime

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            forbidden = FORBIDDEN_DEAD_LETTER_RESPONSE_FIELDS.intersection(data.keys())
            if forbidden:
                raise ValueError(
                    f"Forbidden dead-letter response fields: {', '.join(sorted(forbidden))}"
                )
        return data


class DeadLetterEventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[DeadLetterEventResponse]
    limit: int
    offset: int


class DeadLetterEventListSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: DeadLetterEventListResponse
