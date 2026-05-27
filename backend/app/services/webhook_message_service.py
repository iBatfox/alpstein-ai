import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.lead import LEAD_PRIORITY_URGENT, LEAD_STATUS_IN_PROGRESS, LEAD_STATUS_NEW, Lead
from app.models.message import Message
from app.schemas.ai_reply import AiReplyResult
from app.schemas.lead_signal import LeadSignalDetectionResult
from app.schemas.notification import NotificationDecision
from app.schemas.webhook import NormalizedWebhookMessageRequest, WebhookMessage
from app.schemas.webhook_response import (
    WebhookLeadSummary,
    WebhookNotificationPayload,
)
from app.seed.dev_ai_configuration import PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY
from app.services.ai_configuration_service import AiConfigurationService
from app.services.ai_reply_fallback_service import AiReplyFallbackService
from app.services.ai_reply_orchestration_coordinator import AiReplyOrchestrationCoordinator
from app.services.business_service import BusinessService
from app.services.conversation_service import ConversationService
from app.services.customer_service import CustomerService
from app.services.lead_service import LeadService
from app.services.lead_signal_detection_service import LeadSignalDetectionService
from app.services.message_service import MessageService
from app.services.notification_policy_service import NotificationPolicyService
from app.services.tenant_context_validator import validate_tenant_context

DUPLICATE_SAFE_ACKNOWLEDGMENT = (
    "Thanks for your message. Our team will get back to you shortly."
)

# Backward-compatible alias for tests/docs that referenced the T10 stub name.
STUB_REPLY_TO_CUSTOMER = DUPLICATE_SAFE_ACKNOWLEDGMENT

CUSTOMER_NOTE_MAX_LENGTH = 2000


@dataclass(frozen=True)
class WebhookMessageProcessResult:
    conversation: Conversation
    message: Message
    is_duplicate: bool
    reply_to_customer: str
    lead_created: bool
    notify_owner: bool
    lead_updated: bool = False
    lead: WebhookLeadSummary | None = None
    notification: WebhookNotificationPayload | None = None


@dataclass(frozen=True)
class _ReplyResolution:
    reply_to_customer: str
    ai_failed: bool


@dataclass(frozen=True)
class _LeadProcessOutcome:
    lead_created: bool
    lead_updated: bool
    lead: Lead | None


class WebhookMessageService:
    def __init__(
        self,
        business_service: BusinessService | None = None,
        customer_service: CustomerService | None = None,
        conversation_service: ConversationService | None = None,
        message_service: MessageService | None = None,
        lead_service: LeadService | None = None,
        lead_signal_detection_service: LeadSignalDetectionService | None = None,
        notification_policy_service: NotificationPolicyService | None = None,
        ai_reply_coordinator: AiReplyOrchestrationCoordinator | None = None,
        ai_configuration_service: AiConfigurationService | None = None,
        ai_fallback_service: AiReplyFallbackService | None = None,
    ) -> None:
        self.business_service = business_service or BusinessService()
        self.customer_service = customer_service or CustomerService()
        self.conversation_service = conversation_service or ConversationService()
        self.message_service = message_service or MessageService()
        self.lead_service = lead_service or LeadService()
        self.lead_signal_detection_service = (
            lead_signal_detection_service or LeadSignalDetectionService()
        )
        self.notification_policy_service = (
            notification_policy_service or NotificationPolicyService()
        )
        self.ai_reply_coordinator = (
            ai_reply_coordinator or AiReplyOrchestrationCoordinator()
        )
        self.ai_configuration_service = (
            ai_configuration_service or AiConfigurationService()
        )
        self.ai_fallback_service = ai_fallback_service or AiReplyFallbackService()

    async def process_incoming_message(
        self,
        session: AsyncSession,
        request: NormalizedWebhookMessageRequest,
    ) -> WebhookMessageProcessResult:
        business = await self.business_service.get_by_external_id(
            session,
            request.business_id,
        )
        tenant_id = business.tenant_id
        channel = request.channel.value

        customer = await self.customer_service.get_or_create_customer(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            source_channel=channel,
            phone=request.customer.phone,
            external_customer_id=request.customer.external_customer_id,
            name=request.customer.name,
            email=request.customer.email,
        )

        conversation = await self.conversation_service.get_or_create_open_conversation(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            customer_id=customer.id,
            channel=channel,
        )

        save_result = await self.message_service.save_incoming_customer_message(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            message_text=request.message.text,
            channel=channel,
            external_message_id=request.message.external_message_id,
            raw_payload=request.message.raw_payload,
        )

        conversation.last_message_at = _message_timestamp(request.message)
        await session.flush()

        signals = self.lead_signal_detection_service.detect(
            customer_message_text=request.message.text,
        )

        if save_result.is_duplicate:
            reply_resolution = await self._resolve_reply_to_customer(
                session,
                tenant_id=tenant_id,
                business=business,
                conversation=conversation,
                customer=customer,
                incoming_message=save_result.message,
                customer_message_text=request.message.text,
                channel=channel,
                is_duplicate=True,
                operator_business_context=request.operator_business_context,
                message_timestamp=request.message.timestamp,
                raw_payload=request.message.raw_payload,
            )
            return WebhookMessageProcessResult(
                conversation=conversation,
                message=save_result.message,
                is_duplicate=True,
                reply_to_customer=reply_resolution.reply_to_customer,
                lead_created=False,
                lead_updated=False,
                notify_owner=False,
                lead=None,
                notification=None,
            )

        lead_outcome = await self._process_lead_for_incoming_message(
            session,
            tenant_id=tenant_id,
            business=business,
            customer=customer,
            conversation=conversation,
            channel=channel,
            customer_message_text=request.message.text,
            signals=signals,
        )

        reply_resolution = await self._resolve_reply_to_customer(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            incoming_message=save_result.message,
            customer_message_text=request.message.text,
            channel=channel,
            is_duplicate=False,
            operator_business_context=request.operator_business_context,
            message_timestamp=request.message.timestamp,
            raw_payload=request.message.raw_payload,
        )

        notification_decision = self.notification_policy_service.decide(
            is_duplicate=False,
            lead_created=lead_outcome.lead_created,
            lead_updated=lead_outcome.lead_updated,
            urgent_detected=signals.urgent_detected,
            handoff_requested=signals.handoff_requested,
            ai_failed=reply_resolution.ai_failed,
        )
        notification = _notification_from_decision(notification_decision)
        lead_summary = (
            _lead_summary_from_model(lead_outcome.lead)
            if lead_outcome.lead is not None
            else None
        )

        return WebhookMessageProcessResult(
            conversation=conversation,
            message=save_result.message,
            is_duplicate=False,
            reply_to_customer=reply_resolution.reply_to_customer,
            lead_created=lead_outcome.lead_created,
            lead_updated=lead_outcome.lead_updated,
            notify_owner=notification_decision.should_notify_owner,
            lead=lead_summary,
            notification=notification,
        )

    async def _process_lead_for_incoming_message(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business: object,
        customer: object,
        conversation: Conversation,
        channel: str,
        customer_message_text: str,
        signals: LeadSignalDetectionResult,
    ) -> _LeadProcessOutcome:
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
        )

        customer_note = _truncate_customer_note(customer_message_text)
        active_lead = await self.lead_service.find_active_lead(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            customer_id=customer.id,
            conversation_id=conversation.id,
        )

        if active_lead is None:
            lead = await self.lead_service.create_lead(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                customer_id=customer.id,
                conversation_id=conversation.id,
                source_channel=channel,
                customer_note=customer_note,
            )
            if signals.urgent_detected:
                lead = await self.lead_service.update_lead(
                    session,
                    tenant_id=tenant_id,
                    business_id=business.id,
                    lead=lead,
                    priority=LEAD_PRIORITY_URGENT,
                )
            return _LeadProcessOutcome(
                lead_created=True,
                lead_updated=False,
                lead=lead,
            )

        update_kwargs: dict[str, object] = {"customer_note": customer_note}
        if active_lead.status == LEAD_STATUS_NEW:
            update_kwargs["status"] = LEAD_STATUS_IN_PROGRESS
        if signals.urgent_detected:
            update_kwargs["priority"] = LEAD_PRIORITY_URGENT

        lead = await self.lead_service.update_lead(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            lead=active_lead,
            **update_kwargs,
        )
        return _LeadProcessOutcome(
            lead_created=False,
            lead_updated=True,
            lead=lead,
        )

    async def _resolve_reply_to_customer(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business: object,
        conversation: Conversation,
        customer: object,
        incoming_message: Message,
        customer_message_text: str,
        channel: str,
        is_duplicate: bool,
        operator_business_context: str | None = None,
        message_timestamp: datetime | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> _ReplyResolution:
        orchestration_outcome = await self.ai_reply_coordinator.execute_for_incoming_message(
            session,
            is_duplicate=is_duplicate,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            message=incoming_message,
            customer_message_text=customer_message_text,
            channel=channel,
            template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
            operator_business_context=operator_business_context,
            message_timestamp=message_timestamp,
            raw_payload=raw_payload,
        )

        if orchestration_outcome.is_duplicate:
            reply_text = await self._duplicate_reply_to_customer(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                conversation_id=conversation.id,
            )
            return _ReplyResolution(
                reply_to_customer=reply_text,
                ai_failed=False,
            )

        ai_reply = orchestration_outcome.ai_reply
        if ai_reply is None:
            return _ReplyResolution(
                reply_to_customer=DUPLICATE_SAFE_ACKNOWLEDGMENT,
                ai_failed=False,
            )

        if _ai_reply_text_is_usable(ai_reply):
            reply_text = ai_reply.text.strip()
            await self.message_service.save_outgoing_ai_message(
                session,
                tenant_id=tenant_id,
                business=business,
                conversation=conversation,
                customer=customer,
                message_text=reply_text,
                channel=channel,
                ai_metadata=_ai_reply_metadata(ai_reply, used_fallback=False),
            )
            return _ReplyResolution(
                reply_to_customer=reply_text,
                ai_failed=False,
            )

        configuration = await self.ai_configuration_service.load_for_message(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            channel=channel,
            template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
        )
        fallback_decision = self.ai_fallback_service.decide(
            ai_reply=ai_reply,
            behavior=configuration.behavior,
            channel=channel,
        )
        if fallback_decision.should_reply and fallback_decision.fallback_text:
            await self.message_service.save_outgoing_ai_message(
                session,
                tenant_id=tenant_id,
                business=business,
                conversation=conversation,
                customer=customer,
                message_text=fallback_decision.fallback_text,
                channel=channel,
                ai_metadata=_ai_reply_metadata(ai_reply, used_fallback=True),
            )
            return _ReplyResolution(
                reply_to_customer=fallback_decision.fallback_text,
                ai_failed=True,
            )

        return _ReplyResolution(
            reply_to_customer=DUPLICATE_SAFE_ACKNOWLEDGMENT,
            ai_failed=False,
        )

    async def _duplicate_reply_to_customer(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> str:
        last_ai_message = await self.message_service.find_last_outgoing_ai_message(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            conversation_id=conversation_id,
        )
        if last_ai_message is not None and last_ai_message.message_text.strip():
            return last_ai_message.message_text.strip()
        return DUPLICATE_SAFE_ACKNOWLEDGMENT


def _ai_reply_text_is_usable(ai_reply: AiReplyResult) -> bool:
    return (
        ai_reply.is_success
        and ai_reply.text is not None
        and ai_reply.text.strip() != ""
    )


def _ai_reply_metadata(
    ai_reply: AiReplyResult,
    *,
    used_fallback: bool,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "prompt_run_id": str(ai_reply.prompt_run_id),
        "model": ai_reply.model,
        "provider": ai_reply.provider,
    }
    if used_fallback:
        metadata["used_fallback"] = True
    return metadata


def _message_timestamp(message: WebhookMessage) -> datetime:
    if message.timestamp is None:
        return datetime.utcnow()
    if message.timestamp.tzinfo is not None:
        return message.timestamp.replace(tzinfo=None)
    return message.timestamp


def _truncate_customer_note(text: str) -> str:
    normalized = text.strip()
    if len(normalized) <= CUSTOMER_NOTE_MAX_LENGTH:
        return normalized
    return normalized[:CUSTOMER_NOTE_MAX_LENGTH]


def _lead_summary_from_model(lead: Lead) -> WebhookLeadSummary:
    return WebhookLeadSummary(
        id=str(lead.id),
        status=lead.status,
        priority=lead.priority or "normal",
    )


def _notification_from_decision(
    decision: NotificationDecision,
) -> WebhookNotificationPayload | None:
    if not decision.should_notify_owner:
        return None
    return WebhookNotificationPayload(
        should_notify_owner=True,
        notification_type=decision.notification_type,
        reason=decision.reason,
        priority=decision.priority,
    )
