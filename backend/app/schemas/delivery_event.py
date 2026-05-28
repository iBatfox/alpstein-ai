"""Delivery visibility API schemas (E2.6)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DeliveryStatus = Literal[
    "pending",
    "delivered",
    "failed",
    "skipped",
    "retrying",
    "dead_letter",
]

ReportableDeliveryStatus = Literal[
    "delivered",
    "failed",
    "skipped",
    "retrying",
]

FORBIDDEN_DELIVERY_RESPONSE_FIELDS = frozenset(
    {
        "raw_payload",
        "provider_payload",
        "api_key",
        "secret",
        "bot_token",
    }
)


class DeliveryEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="delivery_id")
    tenant_id: str
    business_id: str
    flow_id: str
    conversation_id: str
    trace_id: str | None = None
    outbound_message_id: str
    channel: str
    status: DeliveryStatus
    provider_message_id: str | None = None
    provider_status: str | None = None
    retry_count: int = 0
    error_type: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    delivered_at: datetime | None = None
    failed_at: datetime | None = None


class DeliveryEventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[DeliveryEventResponse]
    limit: int
    offset: int


class DeliveryEventSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: DeliveryEventResponse


class DeliveryEventListSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: DeliveryEventListResponse


class DeliveryStatusReportRequest(BaseModel):
    """n8n reports channel delivery outcome after send (E2.6)."""

    model_config = ConfigDict(extra="forbid")

    status: ReportableDeliveryStatus
    provider_message_id: str | None = Field(default=None, max_length=255)
    provider_status: str | None = Field(default=None, max_length=100)
    error_type: str | None = Field(default=None, max_length=100)
    error_message: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def failed_requires_error_fields(self) -> DeliveryStatusReportRequest:
        if self.status == "failed":
            if not self.error_type and not self.error_message:
                raise ValueError(
                    "error_type or error_message is required when status is failed"
                )
        return self
