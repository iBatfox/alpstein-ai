"""Replay observability API schemas (E3.1c)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FORBIDDEN_REPLAY_RESPONSE_FIELDS = frozenset(
    {
        "raw_payload",
        "provider_payload",
        "api_key",
        "secret",
        "bot_token",
        "password",
    }
)


class ReplayEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="replay_event_id")
    tenant_id: str
    business_id: str
    flow_id: str | None = None
    conversation_id: str | None = None
    trace_id: str | None = None
    delivery_id: str | None = None
    inbound_message_id: str | None = None
    outbound_message_id: str | None = None
    source: str
    event_type: str
    idempotency_key: str | None = None
    external_message_id: str | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            forbidden = FORBIDDEN_REPLAY_RESPONSE_FIELDS.intersection(data.keys())
            if forbidden:
                raise ValueError(
                    f"Forbidden replay response fields: {', '.join(sorted(forbidden))}"
                )
        return data


class ReplayEventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ReplayEventResponse]
    limit: int
    offset: int


class ReplayEventListSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: ReplayEventListResponse
