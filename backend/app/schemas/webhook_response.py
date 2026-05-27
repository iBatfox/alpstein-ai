"""Webhook success response models (T12.5). Provider-agnostic; no transport/AI internals."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Fields that must never appear in public webhook JSON.
FORBIDDEN_WEBHOOK_RESPONSE_FIELDS = frozenset(
    {
        "raw_payload",
        "ai_metadata",
        "final_prompt",
        "system_prompt",
        "assembled_prompt",
        "prompt_template",
        "input_tokens",
        "output_tokens",
        "provider_payload",
        "openai",
        "api_key",
        "secret",
        "operator_business_context",
    }
)


class WebhookLeadSummary(BaseModel):
    """Lead snapshot for n8n when a lead was created or updated this turn."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    priority: str = Field(min_length=1)


class WebhookNotificationPayload(BaseModel):
    """Owner notification signaling for n8n; optional on webhook `data`."""

    model_config = ConfigDict(extra="forbid")

    should_notify_owner: bool
    notification_type: str | None = None
    reason: str = Field(min_length=1)
    priority: str = Field(min_length=1)


class WebhookConversationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    status: str = Field(min_length=1)


class WebhookMessageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    is_duplicate: bool


class WebhookMessageResponseData(BaseModel):
    """`data` object for successful `POST /api/v1/webhook/message`."""

    model_config = ConfigDict(extra="forbid")

    reply_to_customer: str = Field(min_length=1)
    lead_created: bool
    lead_updated: bool = False
    notify_owner: bool
    conversation: WebhookConversationSummary
    message: WebhookMessageSummary
    lead: WebhookLeadSummary | None = None
    notification: WebhookNotificationPayload | None = None


class WebhookMessageSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: WebhookMessageResponseData


def build_webhook_message_success_envelope(
    *,
    reply_to_customer: str,
    lead_created: bool,
    notify_owner: bool,
    conversation_id: str,
    conversation_status: str,
    message_id: str,
    is_duplicate: bool,
    lead_updated: bool = False,
    lead: WebhookLeadSummary | None = None,
    notification: WebhookNotificationPayload | None = None,
) -> WebhookMessageSuccessEnvelope:
    """Map orchestration fields to the public success envelope."""
    return WebhookMessageSuccessEnvelope(
        success=True,
        data=WebhookMessageResponseData(
            reply_to_customer=reply_to_customer,
            lead_created=lead_created,
            lead_updated=lead_updated,
            notify_owner=notify_owner,
            conversation=WebhookConversationSummary(
                id=conversation_id,
                status=conversation_status,
            ),
            message=WebhookMessageSummary(
                id=message_id,
                is_duplicate=is_duplicate,
            ),
            lead=lead,
            notification=notification,
        ),
    )


def serialize_webhook_message_success(
    *,
    reply_to_customer: str,
    lead_created: bool,
    notify_owner: bool,
    conversation_id: str,
    conversation_status: str,
    message_id: str,
    is_duplicate: bool,
    lead_updated: bool = False,
    lead: WebhookLeadSummary | None = None,
    notification: WebhookNotificationPayload | None = None,
) -> dict:
    """JSON-serializable dict; omits null `lead` and `notification`."""
    return build_webhook_message_success_envelope(
        reply_to_customer=reply_to_customer,
        lead_created=lead_created,
        lead_updated=lead_updated,
        notify_owner=notify_owner,
        conversation_id=conversation_id,
        conversation_status=conversation_status,
        message_id=message_id,
        is_duplicate=is_duplicate,
        lead=lead,
        notification=notification,
    ).model_dump(mode="json", exclude_none=True)
