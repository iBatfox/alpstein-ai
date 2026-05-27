from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.webhook_attribution import (
    EXTERNAL_CONVERSATION_ID_MAX_LENGTH,
    WebhookAttribution,
    WebhookMessageClient,
    WebhookSource,
    validate_external_conversation_id,
)

OPERATOR_BUSINESS_CONTEXT_MAX_LENGTH = 8192


class WebhookChannel(StrEnum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    WEBSITE_CHAT = "website_chat"
    TEST = "test"


class WebhookCustomer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    phone: str | None = None
    name: str | None = None
    email: str | None = None
    external_customer_id: str | None = None

    @model_validator(mode="after")
    def require_customer_identifier(self) -> "WebhookCustomer":
        phone = self.phone if self.phone not in (None, "") else None
        external_customer_id = (
            self.external_customer_id
            if self.external_customer_id not in (None, "")
            else None
        )
        if phone is None and external_customer_id is None:
            raise ValueError("phone or external_customer_id is required")
        return self


class WebhookMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = Field(min_length=1)
    external_message_id: str | None = None
    external_conversation_id: str | None = Field(
        default=None,
        max_length=EXTERNAL_CONVERSATION_ID_MAX_LENGTH,
    )
    timestamp: datetime | None = None
    client: WebhookMessageClient | None = None
    raw_payload: dict[str, Any] | None = None

    @field_validator("external_conversation_id", mode="before")
    @classmethod
    def validate_prefixed_external_conversation_id(cls, value: object) -> str | None:
        return validate_external_conversation_id(value)


class NormalizedWebhookMessageRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    business_id: str = Field(min_length=1)
    channel: WebhookChannel
    source: WebhookSource | None = None
    attribution: WebhookAttribution | None = None
    customer: WebhookCustomer
    message: WebhookMessage
    operator_business_context: str | None = Field(
        default=None,
        max_length=OPERATOR_BUSINESS_CONTEXT_MAX_LENGTH,
    )

    @field_validator("operator_business_context", mode="before")
    @classmethod
    def normalize_operator_business_context(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value  # type: ignore[return-value]
        stripped = value.strip()
        return stripped if stripped else None
