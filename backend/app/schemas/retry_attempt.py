"""Retry lifecycle observability API schemas (E3.2c)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FORBIDDEN_RETRY_RESPONSE_FIELDS = frozenset(
    {
        "raw_payload",
        "provider_payload",
        "api_key",
        "secret",
        "bot_token",
        "password",
    }
)


class RetryAttemptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    business_id: str
    scope_type: str
    scope_id: str
    trace_id: str | None = None
    conversation_id: str | None = None
    attempt_number: int
    status: str
    error_type: str | None = None
    error_message: str | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            forbidden = FORBIDDEN_RETRY_RESPONSE_FIELDS.intersection(data.keys())
            if forbidden:
                raise ValueError(
                    f"Forbidden retry response fields: {', '.join(sorted(forbidden))}"
                )
        return data


class RetryAttemptListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RetryAttemptResponse]
    limit: int
    offset: int


class RetryAttemptListSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: RetryAttemptListResponse
