"""Request/response schemas for Instagram outbound send (n8n → backend)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

INSTAGRAM_OUTBOUND_MESSAGE_MAX_LENGTH = 1000


class InstagramSendMessageRequest(BaseModel):
    business_id: str = Field(min_length=1)
    recipient_id: str = Field(min_length=1)
    message_text: str = Field(min_length=1, max_length=INSTAGRAM_OUTBOUND_MESSAGE_MAX_LENGTH)
    correlation_id: str | None = None
    external_inbound_message_id: str | None = None

    @field_validator("business_id", "recipient_id", "message_text")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class InstagramSendMessageData(BaseModel):
    provider_message_id: str
    status: str = "sent"


class InstagramSendMessageResponse(BaseModel):
    success: bool
    data: InstagramSendMessageData | None = None
    error: dict[str, str] | None = None
