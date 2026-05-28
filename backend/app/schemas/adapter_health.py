"""Adapter monitoring observability API schemas (E3.3b)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FORBIDDEN_ADAPTER_RESPONSE_FIELDS = frozenset(
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

AdapterStatusValue = Literal["healthy", "warning", "degraded", "inactive"]


class AdapterDeliveryBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_by_status: dict[str, int]


class AdapterHealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter: str
    status: AdapterStatusValue
    status_reasons: list[str]
    recent_messages: int
    delivery_success_count: int
    delivery_failure_count: int
    delivery_pending_count: int
    retry_count: int
    dead_letter_count: int
    delivery_failure_rate: float | None = None
    last_activity_at: datetime | None = None
    evaluated_at: datetime | None = None
    breakdown: AdapterDeliveryBreakdown | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            forbidden = FORBIDDEN_ADAPTER_RESPONSE_FIELDS.intersection(data.keys())
            if forbidden:
                raise ValueError(
                    f"Forbidden adapter response fields: {', '.join(sorted(forbidden))}"
                )
        return data


class AdapterHealthListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_hours: int
    items: list[AdapterHealthResponse]


class AdapterHealthListSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: AdapterHealthListResponse


class AdapterHealthSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: AdapterHealthResponse
