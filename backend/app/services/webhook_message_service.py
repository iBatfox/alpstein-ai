import logging
import uuid
import json
import re
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.flow import Flow
from app.models.lead import LEAD_PRIORITY_URGENT, LEAD_STATUS_IN_PROGRESS, LEAD_STATUS_NEW, Lead
from app.models.message import Message
from app.models.delivery_event import DeliveryEvent
from app.models.inbound_processing_lock import LOCK_STATUS_COMPLETED, LOCK_STATUS_FAILED
from app.models.message_trace import MessageTrace
from app.schemas.ai_reply import AiReplyResult
from app.schemas.lead_signal import LeadSignalDetectionResult
from app.schemas.notification import NotificationDecision
from app.schemas.observability import ObservabilityContext
from app.schemas.webhook import NormalizedWebhookMessageRequest, WebhookMessage
from app.schemas.webhook_response import (
    WebhookLeadSummary,
    WebhookNotificationPayload,
)
from app.exceptions import AdapterIngressContainedError
from app.seed.dev_ai_configuration import PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY
from app.services.ai_configuration_service import AiConfigurationService
from app.services.ai_reply_fallback_service import AiReplyFallbackService
from app.services.ai_reply_orchestration_coordinator import AiReplyOrchestrationCoordinator
from app.services.ai_reply_orchestration_service import AiReplyOrchestrationService
from app.services.business_service import BusinessService
from app.services.conversation_service import ConversationService
from app.services.flow_service import FlowService, LegacyWebhookFlow
from app.services.customer_service import CustomerService
from app.services.lead_service import LeadService
from app.services.lead_signal_detection_service import LeadSignalDetectionService
from app.services.message_service import IncomingMessageSaveResult, MessageService
from app.core.config import settings
from app.services.delivery_visibility_service import DeliveryVisibilityService
from app.services.instagram_outbound_dedup_service import InstagramOutboundDedupService
from app.services.inbound_processing_lock_service import InboundProcessingLockService
from app.services.message_idempotency import build_inbound_idempotency_key
from app.models.replay_event import (
    REPLAY_EVENT_DUPLICATE_RETRY,
    REPLAY_EVENT_REPLAY_IGNORED,
    REPLAY_EVENT_RETRY_EXHAUSTED,
    REPLAY_SOURCE_WEBHOOK,
)
from app.models.inbound_processing_lock import InboundProcessingLock
from app.models.retry_attempt import RETRY_STATUS_EXHAUSTED
from app.services.dead_letter_service import DeadLetterService
from app.services.adapter_monitoring_service import AdapterMonitoringService
from app.services.rate_limit_service import RateLimitService
from app.services.spam_protection_service import SpamProtectionService
from app.services.replay_event_service import ReplayEventService
from app.services.retry_lifecycle_service import RetryLifecycleService
from app.services.retry_policy import inbound_replays_exhausted
from app.services.message_trace_service import (
    MessageTraceService,
    build_trace_metadata,
)
from app.services.notification_policy_service import NotificationPolicyService
from app.services.tenant_context_validator import validate_tenant_context
from app.schemas.conversation_context import (
    ConversationHistory,
    ConversationHistoryMessage,
)

logger = logging.getLogger(__name__)

LOG_AI_REINGRESS_DECISION = "webhook_ai_reingress_decision"

DUPLICATE_SAFE_ACKNOWLEDGMENT = (
    "Thanks for your message. Our team will get back to you shortly."
)

# Backward-compatible alias for tests/docs that referenced the T10 stub name.
STUB_REPLY_TO_CUSTOMER = DUPLICATE_SAFE_ACKNOWLEDGMENT

CUSTOMER_NOTE_MAX_LENGTH = 2000
ORANGE_PARK_BUSINESS_EXTERNAL_ID = "orange-park"
ORANGE_PARK_CONTACT_COLLECTION_STAGE = "orange_park_telegram_stage1_contact_form"
ORANGE_PARK_START_RESET_STAGE = "orange_park_telegram_start_reset"
ORANGE_PARK_START_WELCOME_UK = (
    "Добрий день! 👋\n\n"
    "Я AI-асистент ЖК Orange Park.\n\n"
    "Можу допомогти з інформацією про комплекс, квартири, комерційні приміщення "
    "та умови придбання, а також передати ваш запит менеджеру.\n\n"
    "Що вас цікавить?\n"
    "🏡 Квартира\n"
    "🏢 Комерційне приміщення\n"
    "💳 Умови покупки / розтермінування"
)

_PHONE_NUMBER_PATTERN = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")
_RUSSIAN_MARKERS = (
    "свяж",
    "соедин",
    "меня",
    "пожалуйста",
    "спасибо",
    "фамил",
    "менеджером",
)
_UKRAINIAN_MARKERS = (
    "зв'яж",
    "звʼяж",
    "з'єдн",
    "зʼєдн",
    "будь ласка",
    "дякую",
    "прізви",
)
_ENGLISH_MARKERS = (
    "hello",
    "hi",
    "manager",
    "price",
    "contact",
    "phone",
)
_HANDOFF_MARKERS = (
    "свяж",
    "соедин",
    "менеджер",
    "консультац",
    "давай",
    "з'єдн",
    "зʼєдн",
    "передайте",
    "передай",
)
_CONTACT_REQUEST_MARKERS = (
    "номер",
    "телефон",
    "контакт",
    "дані",
    "данные",
    "дай дан",
    "дай контакт",
)


@dataclass(frozen=True)
class WebhookMessageProcessResult:
    conversation: Conversation
    message: Message
    flow: Flow | LegacyWebhookFlow
    is_duplicate: bool
    reply_to_customer: str
    lead_created: bool
    notify_owner: bool
    lead_updated: bool = False
    lead: WebhookLeadSummary | None = None
    notification: WebhookNotificationPayload | None = None
    message_trace_id: uuid.UUID | None = None
    processing_status: str | None = None
    correlation_id: uuid.UUID | None = None
    delivery_id: uuid.UUID | None = None
    delivery_status: str | None = None
    outbound_message_id: uuid.UUID | None = None
    instagram_outbound_allowed: bool | None = None


@dataclass(frozen=True)
class _ReplyResolution:
    reply_to_customer: str
    ai_failed: bool
    outbound_message_id: uuid.UUID | None = None
    langfuse_trace_id: str | None = None
    prompt_run_id: uuid.UUID | None = None


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
        flow_service: FlowService | None = None,
        message_service: MessageService | None = None,
        lead_service: LeadService | None = None,
        lead_signal_detection_service: LeadSignalDetectionService | None = None,
        notification_policy_service: NotificationPolicyService | None = None,
        ai_reply_coordinator: AiReplyOrchestrationCoordinator | None = None,
        ai_configuration_service: AiConfigurationService | None = None,
        ai_fallback_service: AiReplyFallbackService | None = None,
        message_trace_service: MessageTraceService | None = None,
        delivery_visibility_service: DeliveryVisibilityService | None = None,
        inbound_processing_lock_service: InboundProcessingLockService | None = None,
        replay_event_service: ReplayEventService | None = None,
        retry_lifecycle_service: RetryLifecycleService | None = None,
        dead_letter_service: DeadLetterService | None = None,
        adapter_monitoring_service: AdapterMonitoringService | None = None,
        rate_limit_service: RateLimitService | None = None,
        spam_protection_service: SpamProtectionService | None = None,
        instagram_outbound_dedup_service: InstagramOutboundDedupService | None = None,
    ) -> None:
        self.business_service = business_service or BusinessService()
        self.customer_service = customer_service or CustomerService()
        self.conversation_service = conversation_service or ConversationService()
        self.flow_service = flow_service or FlowService()
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
        self.message_trace_service = message_trace_service or MessageTraceService()
        self.delivery_visibility_service = (
            delivery_visibility_service or DeliveryVisibilityService()
        )
        self.inbound_processing_lock_service = (
            inbound_processing_lock_service or InboundProcessingLockService()
        )
        self.replay_event_service = replay_event_service or ReplayEventService()
        self.retry_lifecycle_service = retry_lifecycle_service or RetryLifecycleService()
        self.dead_letter_service = dead_letter_service or DeadLetterService()
        self.adapter_monitoring_service = (
            adapter_monitoring_service or AdapterMonitoringService()
        )
        self.rate_limit_service = rate_limit_service or RateLimitService()
        self.spam_protection_service = spam_protection_service or SpamProtectionService()
        self.instagram_outbound_dedup_service = (
            instagram_outbound_dedup_service or InstagramOutboundDedupService()
        )

    async def _instagram_outbound_allowed_for_response(
        self,
        session: AsyncSession,
        *,
        channel: str,
        business_external_id: str,
        external_message_id: str | None,
        reply_to_customer: str,
    ) -> bool | None:
        if channel != "instagram":
            return None
        if not settings.instagram_outbound_enabled:
            return False
        reply = (reply_to_customer or "").strip()
        inbound_id = (external_message_id or "").strip()
        if not reply or not inbound_id:
            return False
        already_sent = await self.instagram_outbound_dedup_service.is_already_sent(
            session,
            business_external_id=business_external_id,
            external_inbound_message_id=inbound_id,
        )
        return not already_sent

    async def _should_reject_ingress(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
    ) -> bool:
        return await self.adapter_monitoring_service.should_reject_ingress_for_channel(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            channel=channel,
        )

    async def process_incoming_message(
        self,
        session: AsyncSession,
        request: NormalizedWebhookMessageRequest,
        *,
        observability: ObservabilityContext | None = None,
    ) -> WebhookMessageProcessResult:
        if observability is None:
            observability = ObservabilityContext(
                correlation_id=uuid.uuid4(),
                channel=request.channel.value,
                external_message_id=request.message.external_message_id,
                external_conversation_id=request.message.external_conversation_id,
            )
        business = await self.business_service.get_by_external_id(
            session,
            request.business_id,
        )
        tenant_id = business.tenant_id
        channel = request.channel.value
        observability = observability.with_business(
            tenant_id=tenant_id,
            business_id=business.id,
            business_external_id=business.external_id,
        )

        flow = await self.flow_service.resolve_for_webhook(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            flow_key=request.flow_key,
        )
        if isinstance(flow, LegacyWebhookFlow):
            return await self._process_incoming_message_legacy(
                session,
                request,
                observability=observability,
                business=business,
                tenant_id=tenant_id,
                channel=channel,
                flow=flow,
            )

        observability = observability.with_flow(
            flow_id=flow.id,
            flow_key=flow.flow_key,
        )

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
            flow_id=flow.id,
            customer_id=customer.id,
            channel=channel,
            external_conversation_id=request.message.external_conversation_id,
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
            flow_id=flow.id,
            message_timestamp=request.message.timestamp,
        )
        observability = observability.with_session(
            conversation_id=conversation.id,
            inbound_message_id=save_result.message.id,
            is_duplicate=save_result.is_duplicate,
        )

        conversation.last_message_at = _message_timestamp(request.message)
        await session.flush()

        signals = self.lead_signal_detection_service.detect(
            customer_message_text=request.message.text,
        )

        trace_metadata = build_trace_metadata(
            correlation_id=observability.correlation_id,
            n8n_execution_id=observability.n8n_execution_id,
        )
        message_trace = await self.message_trace_service.record_inbound_turn(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            flow_id=flow.id,
            conversation_id=conversation.id,
            inbound_message_id=save_result.message.id,
            channel=channel,
            is_duplicate=save_result.is_duplicate,
            flow_key=flow.flow_key,
            external_conversation_id=request.message.external_conversation_id,
            external_message_id=save_result.message.external_message_id,
            idempotency_key=save_result.message.idempotency_key,
            trace_metadata=trace_metadata,
            external_trace_id=str(observability.correlation_id),
        )

        if save_result.is_duplicate:
            replay_lock = await self._record_lock_replay_attempt(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                conversation_id=conversation.id,
                idempotency_key=save_result.message.idempotency_key,
            )
            await self._maybe_handle_inbound_exhaustion(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                flow=flow,
                conversation=conversation,
                message=save_result.message,
                message_trace=message_trace,
                observability=observability,
                lock=replay_lock,
            )
            await self._record_webhook_replay_event(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                flow_id=flow.id,
                conversation_id=conversation.id,
                message_trace=message_trace,
                inbound_message_id=save_result.message.id,
                idempotency_key=save_result.message.idempotency_key,
                external_message_id=save_result.message.external_message_id,
                correlation_id=str(observability.correlation_id),
                event_type=REPLAY_EVENT_DUPLICATE_RETRY,
            )
            ai_is_duplicate = await self._ai_duplicate_for_incoming_replay(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                channel=channel,
                persisted_duplicate=save_result.is_duplicate,
                incoming_message=save_result.message,
            )
            logger.info(
                LOG_AI_REINGRESS_DECISION,
                extra={
                    "channel": channel,
                    "persisted_duplicate": save_result.is_duplicate,
                    "ai_is_duplicate": ai_is_duplicate,
                    "inbound_message_id": str(save_result.message.id),
                    "external_message_id": save_result.message.external_message_id,
                },
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
                is_duplicate=ai_is_duplicate,
                operator_business_context=request.operator_business_context,
                message_timestamp=request.message.timestamp,
                raw_payload=request.message.raw_payload,
                observability=observability,
                flow_id=flow.id,
            )
            if not ai_is_duplicate and reply_resolution.outbound_message_id is not None:
                await self.message_trace_service.mark_completed(
                    session,
                    message_trace,
                    outbound_message_id=reply_resolution.outbound_message_id,
                    external_trace_id=str(observability.correlation_id),
                    langfuse_trace_id=reply_resolution.langfuse_trace_id,
                    trace_metadata=build_trace_metadata(
                        correlation_id=observability.correlation_id,
                        n8n_execution_id=observability.n8n_execution_id,
                        prompt_run_id=reply_resolution.prompt_run_id,
                    ),
                )
            trace_id, trace_status, trace_correlation = _trace_fields_for_response(
                message_trace,
                observability=observability,
            )
            instagram_outbound_allowed = await self._instagram_outbound_allowed_for_response(
                session,
                channel=channel,
                business_external_id=business.external_id,
                external_message_id=request.message.external_message_id,
                reply_to_customer=reply_resolution.reply_to_customer,
            )
            return WebhookMessageProcessResult(
                conversation=conversation,
                message=save_result.message,
                flow=flow,
                is_duplicate=True,
                reply_to_customer=reply_resolution.reply_to_customer,
                lead_created=False,
                lead_updated=False,
                notify_owner=False,
                lead=None,
                notification=None,
                message_trace_id=trace_id,
                processing_status=trace_status,
                correlation_id=trace_correlation,
                instagram_outbound_allowed=instagram_outbound_allowed,
            )

        await self.rate_limit_service.consume_ingress_request(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            channel=channel,
            conversation_id=conversation.id,
            correlation_id=str(observability.correlation_id),
        )

        await self.spam_protection_service.evaluate_ingress_request(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            channel=channel,
            conversation_id=conversation.id,
            message_text=request.message.text,
            correlation_id=str(observability.correlation_id),
        )

        if await self._should_reject_ingress(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            channel=channel,
        ):
            raise AdapterIngressContainedError(channel)

        if message_trace is None:
            raise RuntimeError("message trace missing for new inbound message")

        idempotency_key = save_result.message.idempotency_key
        if not idempotency_key:
            idempotency_key = build_inbound_idempotency_key(
                business_id=business.id,
                flow_id=flow.id,
                conversation_id=conversation.id,
                channel=channel,
                external_message_id=save_result.message.external_message_id,
                message_text=request.message.text,
                message_timestamp=request.message.timestamp,
            )

        lock_acquire = await self.inbound_processing_lock_service.acquire_processing_owner(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            flow_id=flow.id,
            conversation_id=conversation.id,
            channel=channel,
            idempotency_key=idempotency_key,
            owner_correlation_id=str(observability.correlation_id),
            external_message_id=save_result.message.external_message_id,
        )
        if lock_acquire.conflict:
            await self._maybe_handle_inbound_exhaustion(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                flow=flow,
                conversation=conversation,
                message=save_result.message,
                message_trace=message_trace,
                observability=observability,
                lock=lock_acquire.lock,
            )
            return await self._respond_inflight_replay(
                session,
                tenant_id=tenant_id,
                business=business,
                flow=flow,
                conversation=conversation,
                customer=customer,
                message=save_result.message,
                message_trace=message_trace,
                channel=channel,
                customer_message_text=request.message.text,
                observability=observability,
                flow_id=flow.id,
            )

        processing_lock = lock_acquire.lock
        await self.message_trace_service.mark_processing(session, message_trace)

        delivery_event: DeliveryEvent | None = None
        try:
            if _lead_creation_enabled_for_flow(
                flow
            ) and not _orange_park_stage1_contact_collection_only(business, channel):
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
            else:
                lead_outcome = _LeadProcessOutcome(
                    lead_created=False,
                    lead_updated=False,
                    lead=None,
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
                observability=observability,
                flow_id=flow.id,
            )

            await self.message_trace_service.mark_completed(
                session,
                message_trace,
                outbound_message_id=reply_resolution.outbound_message_id,
                external_trace_id=str(observability.correlation_id),
                langfuse_trace_id=reply_resolution.langfuse_trace_id,
                trace_metadata=build_trace_metadata(
                    correlation_id=observability.correlation_id,
                    n8n_execution_id=observability.n8n_execution_id,
                    prompt_run_id=reply_resolution.prompt_run_id,
                ),
            )

            delivery_event = await self._create_pending_delivery_if_outbound(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                flow_id=flow.id,
                conversation_id=conversation.id,
                trace_id=message_trace.id,
                outbound_message_id=reply_resolution.outbound_message_id,
                channel=channel,
            )
            if processing_lock is not None:
                await self.inbound_processing_lock_service.release(
                    session,
                    processing_lock,
                    status=LOCK_STATUS_COMPLETED,
                )
        except Exception as exc:
            await self.message_trace_service.mark_failed(
                session,
                message_trace,
                error_type=type(exc).__name__,
                error_message=str(exc),
                trace_metadata=trace_metadata,
            )
            if processing_lock is not None:
                await self.inbound_processing_lock_service.release(
                    session,
                    processing_lock,
                    status=LOCK_STATUS_FAILED,
                )
            raise

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

        trace_id, trace_status, trace_correlation = _trace_fields_for_response(
            message_trace,
            observability=observability,
        )
        delivery_id, delivery_status, outbound_id = _delivery_fields_for_response(
            delivery_event,
        )
        instagram_outbound_allowed = await self._instagram_outbound_allowed_for_response(
            session,
            channel=channel,
            business_external_id=business.external_id,
            external_message_id=request.message.external_message_id,
            reply_to_customer=reply_resolution.reply_to_customer,
        )
        return WebhookMessageProcessResult(
            conversation=conversation,
            message=save_result.message,
            flow=flow,
            is_duplicate=False,
            reply_to_customer=reply_resolution.reply_to_customer,
            lead_created=lead_outcome.lead_created,
            lead_updated=lead_outcome.lead_updated,
            notify_owner=notification_decision.should_notify_owner,
            lead=lead_summary,
            notification=notification,
            message_trace_id=trace_id,
            processing_status=trace_status,
            correlation_id=trace_correlation,
            delivery_id=delivery_id,
            delivery_status=delivery_status,
            outbound_message_id=outbound_id,
            instagram_outbound_allowed=instagram_outbound_allowed,
        )

    async def _process_incoming_message_legacy(
        self,
        session: AsyncSession,
        request: NormalizedWebhookMessageRequest,
        *,
        observability: ObservabilityContext,
        business: object,
        tenant_id: uuid.UUID,
        channel: str,
        flow: LegacyWebhookFlow,
    ) -> WebhookMessageProcessResult:
        observability = observability.with_flow(
            flow_id=flow.id,
            flow_key=flow.flow_key,
        )
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
        conversation = await _legacy_get_or_create_open_conversation(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            customer_id=customer.id,
            channel=channel,
            external_conversation_id=request.message.external_conversation_id,
        )
        save_result = await _legacy_save_incoming_customer_message(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            conversation_id=conversation.id,
            message_text=request.message.text,
            channel=channel,
            external_message_id=request.message.external_message_id,
            raw_payload=request.message.raw_payload,
        )
        conversation.last_message_at = _message_timestamp(request.message)
        await _legacy_update_conversation_last_message_at(
            session,
            conversation_id=conversation.id,
            last_message_at=conversation.last_message_at,
        )
        observability = observability.with_session(
            conversation_id=conversation.id,
            inbound_message_id=save_result.message.id,
            is_duplicate=save_result.is_duplicate,
        )

        if save_result.is_duplicate:
            reply_text = await _legacy_find_last_outgoing_ai_message_text(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                conversation_id=conversation.id,
            )
            return WebhookMessageProcessResult(
                conversation=conversation,
                message=save_result.message,
                flow=flow,
                is_duplicate=True,
                reply_to_customer=reply_text or DUPLICATE_SAFE_ACKNOWLEDGMENT,
                lead_created=False,
                lead_updated=False,
                notify_owner=False,
                lead=None,
                notification=None,
                correlation_id=observability.correlation_id,
                instagram_outbound_allowed=None,
            )

        signals = self.lead_signal_detection_service.detect(
            customer_message_text=request.message.text,
        )
        reply_resolution = await self._resolve_reply_to_customer_legacy(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            incoming_message=save_result.message,
            customer_message_text=request.message.text,
            channel=channel,
            operator_business_context=request.operator_business_context,
            message_timestamp=request.message.timestamp,
            raw_payload=request.message.raw_payload,
            observability=observability,
        )
        if _orange_park_stage1_contact_collection_only(business, channel):
            lead_outcome = _LeadProcessOutcome(
                lead_created=False,
                lead_updated=False,
                lead=None,
            )
        else:
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
        notification_decision = self.notification_policy_service.decide(
            is_duplicate=False,
            lead_created=lead_outcome.lead_created,
            lead_updated=lead_outcome.lead_updated,
            urgent_detected=signals.urgent_detected,
            handoff_requested=signals.handoff_requested,
            ai_failed=reply_resolution.ai_failed,
        )
        return WebhookMessageProcessResult(
            conversation=conversation,
            message=save_result.message,
            flow=flow,
            is_duplicate=False,
            reply_to_customer=reply_resolution.reply_to_customer,
            lead_created=lead_outcome.lead_created,
            lead_updated=lead_outcome.lead_updated,
            notify_owner=notification_decision.should_notify_owner,
            lead=_lead_summary_from_model(lead_outcome.lead)
            if lead_outcome.lead is not None
            else None,
            notification=_notification_from_decision(notification_decision),
            correlation_id=observability.correlation_id,
            outbound_message_id=reply_resolution.outbound_message_id,
            instagram_outbound_allowed=None,
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
        observability: ObservabilityContext | None = None,
        flow_id: uuid.UUID | None = None,
    ) -> _ReplyResolution:
        orange_park_start = await self._resolve_orange_park_start_reply(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            incoming_message=incoming_message,
            customer_message_text=customer_message_text,
            channel=channel,
            raw_payload=raw_payload,
            flow_id=flow_id,
        )
        if orange_park_start is not None:
            return orange_park_start

        orange_park_reply = await self._resolve_orange_park_contact_collection_reply(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            incoming_message=incoming_message,
            customer_message_text=customer_message_text,
            channel=channel,
            flow_id=flow_id,
        )
        if orange_park_reply is not None:
            return orange_park_reply

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
            observability=observability,
        )

        prompt_run_id = None
        langfuse_trace_id = orchestration_outcome.langfuse_trace_id
        if orchestration_outcome.is_duplicate:
            reply_text = await self._duplicate_reply_to_customer(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                conversation_id=conversation.id,
                inbound_message_id=incoming_message.id,
            )
            return _ReplyResolution(
                reply_to_customer=reply_text,
                ai_failed=False,
                langfuse_trace_id=langfuse_trace_id,
            )

        ai_reply = orchestration_outcome.ai_reply
        if ai_reply is None:
            return _ReplyResolution(
                reply_to_customer=DUPLICATE_SAFE_ACKNOWLEDGMENT,
                ai_failed=False,
                langfuse_trace_id=langfuse_trace_id,
            )

        prompt_run_id = ai_reply.prompt_run_id

        if _ai_reply_text_is_usable(ai_reply):
            reply_text = ai_reply.text.strip()
            outbound_message = await self.message_service.save_outgoing_ai_message(
                session,
                tenant_id=tenant_id,
                business=business,
                conversation=conversation,
                customer=customer,
                message_text=reply_text,
                channel=channel,
                ai_metadata=_ai_reply_metadata(ai_reply, used_fallback=False),
                flow_id=flow_id,
            )
            return _ReplyResolution(
                reply_to_customer=reply_text,
                ai_failed=False,
                outbound_message_id=outbound_message.id,
                langfuse_trace_id=langfuse_trace_id,
                prompt_run_id=prompt_run_id,
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
            outbound_message = await self.message_service.save_outgoing_ai_message(
                session,
                tenant_id=tenant_id,
                business=business,
                conversation=conversation,
                customer=customer,
                message_text=fallback_decision.fallback_text,
                channel=channel,
                ai_metadata=_ai_reply_metadata(ai_reply, used_fallback=True),
                flow_id=flow_id,
            )
            return _ReplyResolution(
                reply_to_customer=fallback_decision.fallback_text,
                ai_failed=True,
                outbound_message_id=outbound_message.id,
                langfuse_trace_id=langfuse_trace_id,
                prompt_run_id=prompt_run_id,
            )

        return _ReplyResolution(
            reply_to_customer=DUPLICATE_SAFE_ACKNOWLEDGMENT,
            ai_failed=False,
            langfuse_trace_id=langfuse_trace_id,
            prompt_run_id=prompt_run_id,
        )

    async def _resolve_orange_park_start_reply(
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
        raw_payload: dict[str, Any] | None,
        flow_id: uuid.UUID | None,
    ) -> _ReplyResolution | None:
        if not _orange_park_start_applies(business, channel, customer_message_text):
            return None

        reply_text = ORANGE_PARK_START_WELCOME_UK
        await _archive_orange_park_pre_start_history(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            conversation_id=conversation.id,
            current_message_id=incoming_message.id,
        )
        _set_message_metadata(
            incoming_message,
            {
                "orange_park_start_reset": {
                    "stage": ORANGE_PARK_START_RESET_STAGE,
                    "excluded_previous_history": True,
                    "language": "uk",
                }
            },
        )
        await session.flush()
        outbound_message = await self.message_service.save_outgoing_ai_message(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            message_text=reply_text,
            channel=channel,
            ai_metadata={
                "orange_park_start_reset": True,
                "stage": ORANGE_PARK_START_RESET_STAGE,
                "used_fallback": False,
            },
            flow_id=flow_id,
        )
        return _ReplyResolution(
            reply_to_customer=reply_text,
            ai_failed=False,
            outbound_message_id=outbound_message.id,
        )

    async def _resolve_orange_park_contact_collection_reply(
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
        flow_id: uuid.UUID | None,
    ) -> _ReplyResolution | None:
        if not _orange_park_stage1_contact_collection_only(business, channel):
            return None

        history = await self.message_service.load_recent_conversation_history(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            conversation_id=conversation.id,
        )
        reply_text, metadata = _orange_park_contact_collection_reply_and_metadata(
            customer_message_text,
            history=history,
        )
        if reply_text is None:
            return None

        _set_message_metadata(incoming_message, metadata)
        await session.flush()
        outbound_message = await self.message_service.save_outgoing_ai_message(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            message_text=reply_text,
            channel=channel,
            ai_metadata={
                "orange_park_contact_collection": True,
                "stage": ORANGE_PARK_CONTACT_COLLECTION_STAGE,
                "used_fallback": False,
            },
            flow_id=flow_id,
        )
        return _ReplyResolution(
            reply_to_customer=reply_text,
            ai_failed=False,
            outbound_message_id=outbound_message.id,
        )

    async def _resolve_reply_to_customer_legacy(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business: object,
        conversation: object,
        customer: object,
        incoming_message: object,
        customer_message_text: str,
        channel: str,
        operator_business_context: str | None = None,
        message_timestamp: datetime | None = None,
        raw_payload: dict[str, Any] | None = None,
        observability: ObservabilityContext | None = None,
    ) -> _ReplyResolution:
        orange_park_start = await _resolve_orange_park_start_reply_legacy(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            incoming_message=incoming_message,
            customer_message_text=customer_message_text,
            channel=channel,
            raw_payload=raw_payload,
        )
        if orange_park_start is not None:
            return orange_park_start

        orange_park_reply = await _resolve_orange_park_contact_collection_reply_legacy(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            incoming_message=incoming_message,
            customer_message_text=customer_message_text,
            channel=channel,
        )
        if orange_park_reply is not None:
            return orange_park_reply

        coordinator = AiReplyOrchestrationCoordinator(
            AiReplyOrchestrationService(
                message_service=_LegacyMessageHistoryService(),
            )
        )
        orchestration_outcome = await coordinator.execute_for_incoming_message(
            session,
            is_duplicate=False,
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
            observability=observability,
        )
        ai_reply = orchestration_outcome.ai_reply
        if ai_reply is not None and _ai_reply_text_is_usable(ai_reply):
            reply_text = ai_reply.text.strip()
            outbound_message = await _legacy_save_outgoing_ai_message(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                conversation_id=conversation.id,
                message_text=reply_text,
                channel=channel,
                ai_metadata=_ai_reply_metadata(ai_reply, used_fallback=False),
            )
            return _ReplyResolution(
                reply_to_customer=reply_text,
                ai_failed=False,
                outbound_message_id=outbound_message.id,
                langfuse_trace_id=orchestration_outcome.langfuse_trace_id,
                prompt_run_id=ai_reply.prompt_run_id,
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
            outbound_message = await _legacy_save_outgoing_ai_message(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                conversation_id=conversation.id,
                message_text=fallback_decision.fallback_text,
                channel=channel,
                ai_metadata=_ai_reply_metadata(ai_reply, used_fallback=True)
                if ai_reply is not None
                else {"used_fallback": True},
            )
            return _ReplyResolution(
                reply_to_customer=fallback_decision.fallback_text,
                ai_failed=True,
                outbound_message_id=outbound_message.id,
                langfuse_trace_id=orchestration_outcome.langfuse_trace_id,
                prompt_run_id=ai_reply.prompt_run_id if ai_reply is not None else None,
            )
        return _ReplyResolution(
            reply_to_customer=DUPLICATE_SAFE_ACKNOWLEDGMENT,
            ai_failed=False,
            langfuse_trace_id=orchestration_outcome.langfuse_trace_id,
            prompt_run_id=ai_reply.prompt_run_id if ai_reply is not None else None,
        )

    async def _record_webhook_replay_event(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_id: uuid.UUID,
        conversation_id: uuid.UUID,
        message_trace: MessageTrace | None,
        inbound_message_id: uuid.UUID,
        idempotency_key: str | None,
        external_message_id: str | None,
        correlation_id: str,
        event_type: str,
    ) -> None:
        await self.replay_event_service.record(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            source=REPLAY_SOURCE_WEBHOOK,
            event_type=event_type,
            flow_id=flow_id,
            conversation_id=conversation_id,
            trace_id=message_trace.id if message_trace is not None else None,
            inbound_message_id=inbound_message_id,
            idempotency_key=idempotency_key,
            external_message_id=external_message_id,
            correlation_id=correlation_id,
        )

    async def _record_lock_replay_attempt(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        idempotency_key: str | None,
    ) -> InboundProcessingLock | None:
        if not idempotency_key:
            return None
        return await self.inbound_processing_lock_service.record_replay_attempt(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            conversation_id=conversation_id,
            idempotency_key=idempotency_key,
        )

    async def _maybe_handle_inbound_exhaustion(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow: Flow,
        conversation: Conversation,
        message: Message,
        message_trace: MessageTrace | None,
        observability: ObservabilityContext,
        lock: InboundProcessingLock | None,
    ) -> None:
        if lock is None:
            return
        if not inbound_replays_exhausted(lock.replay_count or 0):
            return

        await self.retry_lifecycle_service.record_inbound_attempt(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            lock_id=lock.id,
            attempt_number=lock.replay_count or 0,
            status=RETRY_STATUS_EXHAUSTED,
            trace_id=message_trace.id if message_trace is not None else None,
            conversation_id=conversation.id,
            correlation_id=str(observability.correlation_id),
        )
        await self.dead_letter_service.record_inbound_exhausted(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            lock_id=lock.id,
            flow_id=flow.id,
            conversation_id=conversation.id,
            inbound_message_id=message.id,
            trace_id=message_trace.id if message_trace is not None else None,
            retry_count=lock.replay_count or 0,
            correlation_id=str(observability.correlation_id),
        )
        await self.replay_event_service.record(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            source=REPLAY_SOURCE_WEBHOOK,
            event_type=REPLAY_EVENT_RETRY_EXHAUSTED,
            flow_id=flow.id,
            conversation_id=conversation.id,
            trace_id=message_trace.id if message_trace is not None else None,
            inbound_message_id=message.id,
            idempotency_key=lock.idempotency_key,
            external_message_id=message.external_message_id,
            correlation_id=str(observability.correlation_id),
            metadata={"replay_count": lock.replay_count},
        )

    async def _respond_inflight_replay(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business: object,
        flow: Flow,
        conversation: Conversation,
        customer: object,
        message: Message,
        message_trace: MessageTrace | None,
        channel: str,
        customer_message_text: str,
        observability: ObservabilityContext,
        flow_id: uuid.UUID,
    ) -> WebhookMessageProcessResult:
        if message_trace is not None:
            message_trace = await self.message_trace_service.record_duplicate_retry(
                session,
                message_trace,
            )

        await self._record_webhook_replay_event(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            flow_id=flow_id,
            conversation_id=conversation.id,
            message_trace=message_trace,
            inbound_message_id=message.id,
            idempotency_key=message.idempotency_key,
            external_message_id=message.external_message_id,
            correlation_id=str(observability.correlation_id),
            event_type=REPLAY_EVENT_REPLAY_IGNORED,
        )

        reply_resolution = await self._resolve_reply_to_customer(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            incoming_message=message,
            customer_message_text=customer_message_text,
            channel=channel,
            is_duplicate=True,
            flow_id=flow_id,
            observability=observability,
        )
        trace_id, trace_status, trace_correlation = _trace_fields_for_response(
            message_trace,
            observability=observability,
        )
        instagram_outbound_allowed = await self._instagram_outbound_allowed_for_response(
            session,
            channel=channel,
            business_external_id=business.external_id,
            external_message_id=message.external_message_id,
            reply_to_customer=reply_resolution.reply_to_customer,
        )
        return WebhookMessageProcessResult(
            conversation=conversation,
            message=message,
            flow=flow,
            is_duplicate=True,
            reply_to_customer=reply_resolution.reply_to_customer,
            lead_created=False,
            lead_updated=False,
            notify_owner=False,
            lead=None,
            notification=None,
            message_trace_id=trace_id,
            processing_status=trace_status,
            correlation_id=trace_correlation,
            instagram_outbound_allowed=instagram_outbound_allowed,
        )

    async def _create_pending_delivery_if_outbound(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_id: uuid.UUID,
        conversation_id: uuid.UUID,
        trace_id: uuid.UUID,
        outbound_message_id: uuid.UUID | None,
        channel: str,
    ) -> DeliveryEvent | None:
        if outbound_message_id is None:
            return None
        return await self.delivery_visibility_service.create_pending_for_outbound(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            flow_id=flow_id,
            conversation_id=conversation_id,
            trace_id=trace_id,
            outbound_message_id=outbound_message_id,
            channel=channel,
        )

    async def _duplicate_reply_to_customer(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        inbound_message_id: uuid.UUID | None = None,
    ) -> str:
        if inbound_message_id is not None:
            inbound_reply = await self.message_service.find_outgoing_ai_for_inbound(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                inbound_message_id=inbound_message_id,
            )
            if inbound_reply is not None and inbound_reply.message_text.strip():
                return inbound_reply.message_text.strip()

        last_ai_message = await self.message_service.find_last_outgoing_ai_message(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            conversation_id=conversation_id,
        )
        if last_ai_message is not None and last_ai_message.message_text.strip():
            return last_ai_message.message_text.strip()
        return DUPLICATE_SAFE_ACKNOWLEDGMENT

    async def _ai_duplicate_for_incoming_replay(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
        persisted_duplicate: bool,
        incoming_message: Message,
    ) -> bool:
        """Skip AI on true duplicates; allow first AI pass after Meta persist + n8n re-ingress."""
        if not persisted_duplicate:
            return False
        if channel != "instagram":
            return True

        inbound_reply = await self.message_service.find_outgoing_ai_for_inbound(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            inbound_message_id=incoming_message.id,
        )
        return inbound_reply is not None


class _LegacyMessageHistoryService:
    async def load_recent_conversation_history(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        limit: int = 20,
    ) -> ConversationHistory:
        rows = (
            await session.execute(
                text(
                    """
                    select sender_type, message_text, created_at, metadata
                    from messages
                    where tenant_id = :tenant_id
                      and business_id = :business_id
                      and conversation_id = :conversation_id
                    order by created_at desc
                    limit :limit
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "business_id": business_id,
                    "conversation_id": conversation_id,
                    "limit": max(1, min(limit, 20)),
                },
            )
        ).mappings().all()
        if not rows:
            return ConversationHistory.empty()
        messages = []
        for row in reversed(rows):
            metadata = row["metadata"] or {}
            if metadata.get("excluded_from_prompt_history") is True:
                continue
            messages.append(
                ConversationHistoryMessage(
                    sender_type=row["sender_type"],
                    message_text=row["message_text"],
                    created_at=row["created_at"],
                )
            )
        return ConversationHistory(messages=tuple(messages))


async def _legacy_get_or_create_open_conversation(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    channel: str,
    external_conversation_id: str | None,
) -> SimpleNamespace:
    normalized_external_id = _normalize_legacy_string(external_conversation_id)
    if normalized_external_id is not None:
        row = (
            await session.execute(
                text(
                    """
                    select id, tenant_id, business_id, customer_id, channel,
                           external_conversation_id, status, is_ai_active,
                           last_message_at, created_at, updated_at
                    from conversations
                    where tenant_id = :tenant_id
                      and business_id = :business_id
                      and channel = :channel
                      and external_conversation_id = :external_conversation_id
                      and status in ('open', 'waiting_for_customer', 'waiting_for_owner')
                    order by last_message_at desc nulls last, created_at desc
                    limit 1
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "business_id": business_id,
                    "channel": channel,
                    "external_conversation_id": normalized_external_id,
                },
            )
        ).mappings().first()
    else:
        row = (
            await session.execute(
                text(
                    """
                    select id, tenant_id, business_id, customer_id, channel,
                           external_conversation_id, status, is_ai_active,
                           last_message_at, created_at, updated_at
                    from conversations
                    where tenant_id = :tenant_id
                      and business_id = :business_id
                      and customer_id = :customer_id
                      and channel = :channel
                      and status in ('open', 'waiting_for_customer', 'waiting_for_owner')
                    order by last_message_at desc nulls last, created_at desc
                    limit 1
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "business_id": business_id,
                    "customer_id": customer_id,
                    "channel": channel,
                },
            )
        ).mappings().first()
    if row is not None:
        return _legacy_namespace(row)

    conversation_id = uuid.uuid4()
    row = (
        await session.execute(
            text(
                """
                insert into conversations (
                    id, tenant_id, business_id, customer_id, channel,
                    external_conversation_id, status, is_ai_active
                )
                values (
                    :id, :tenant_id, :business_id, :customer_id, :channel,
                    :external_conversation_id, 'open', true
                )
                returning id, tenant_id, business_id, customer_id, channel,
                          external_conversation_id, status, is_ai_active,
                          last_message_at, created_at, updated_at
                """
            ),
            {
                "id": conversation_id,
                "tenant_id": tenant_id,
                "business_id": business_id,
                "customer_id": customer_id,
                "channel": channel,
                "external_conversation_id": normalized_external_id,
            },
        )
    ).mappings().one()
    return _legacy_namespace(row)


async def _legacy_save_incoming_customer_message(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    conversation_id: uuid.UUID,
    message_text: str,
    channel: str,
    external_message_id: str | None,
    raw_payload: dict[str, Any] | None,
) -> IncomingMessageSaveResult:
    stored_external_id = _normalize_legacy_string(external_message_id)
    if stored_external_id is not None:
        existing = (
            await session.execute(
                text(
                    """
                    select id, tenant_id, business_id, conversation_id,
                           sender_type, direction, channel, message_text,
                           message_type, external_message_id, raw_payload,
                           ai_metadata, metadata, created_at
                    from messages
                    where tenant_id = :tenant_id
                      and business_id = :business_id
                      and conversation_id = :conversation_id
                      and sender_type = 'customer'
                      and direction = 'incoming'
                      and external_message_id = :external_message_id
                    limit 1
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "business_id": business_id,
                    "conversation_id": conversation_id,
                    "external_message_id": stored_external_id,
                },
            )
        ).mappings().first()
        if existing is not None:
            return IncomingMessageSaveResult(
                message=_legacy_message_namespace(existing),
                is_duplicate=True,
            )

    row = (
        await session.execute(
            text(
                """
                insert into messages (
                    id, tenant_id, business_id, conversation_id, sender_type,
                    direction, channel, message_text, message_type,
                    external_message_id, raw_payload
                )
                values (
                    :id, :tenant_id, :business_id, :conversation_id, 'customer',
                    'incoming', :channel, :message_text, 'text',
                    :external_message_id, cast(:raw_payload as jsonb)
                )
                returning id, tenant_id, business_id, conversation_id,
                          sender_type, direction, channel, message_text,
                          message_type, external_message_id, raw_payload,
                          ai_metadata, metadata, created_at
                """
            ),
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "business_id": business_id,
                "conversation_id": conversation_id,
                "channel": channel,
                "message_text": message_text,
                "external_message_id": stored_external_id,
                "raw_payload": json.dumps(raw_payload) if raw_payload is not None else None,
            },
        )
    ).mappings().one()
    return IncomingMessageSaveResult(
        message=_legacy_message_namespace(row),
        is_duplicate=False,
    )


async def _legacy_save_outgoing_ai_message(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    conversation_id: uuid.UUID,
    message_text: str,
    channel: str,
    ai_metadata: dict[str, Any] | None,
) -> SimpleNamespace:
    row = (
        await session.execute(
            text(
                """
                insert into messages (
                    id, tenant_id, business_id, conversation_id, sender_type,
                    direction, channel, message_text, message_type, ai_metadata
                )
                values (
                    :id, :tenant_id, :business_id, :conversation_id, 'ai',
                    'outgoing', :channel, :message_text, 'text',
                    cast(:ai_metadata as jsonb)
                )
                returning id, tenant_id, business_id, conversation_id,
                          sender_type, direction, channel, message_text,
                          message_type, external_message_id, raw_payload,
                          ai_metadata, metadata, created_at
                """
            ),
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "business_id": business_id,
                "conversation_id": conversation_id,
                "channel": channel,
                "message_text": message_text,
                "ai_metadata": json.dumps(ai_metadata) if ai_metadata is not None else None,
            },
        )
    ).mappings().one()
    return _legacy_message_namespace(row)


async def _legacy_update_conversation_last_message_at(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    last_message_at: datetime,
) -> None:
    await session.execute(
        text(
            """
            update conversations
            set last_message_at = :last_message_at,
                updated_at = now()
            where id = :conversation_id
            """
        ),
        {
            "conversation_id": conversation_id,
            "last_message_at": last_message_at,
        },
    )


async def _legacy_find_last_outgoing_ai_message_text(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> str | None:
    row = (
        await session.execute(
            text(
                """
                select message_text
                from messages
                where tenant_id = :tenant_id
                  and business_id = :business_id
                  and conversation_id = :conversation_id
                  and sender_type = 'ai'
                  and direction = 'outgoing'
                order by created_at desc
                limit 1
                """
            ),
            {
                "tenant_id": tenant_id,
                "business_id": business_id,
                "conversation_id": conversation_id,
            },
        )
    ).mappings().first()
    if row is None:
        return None
    text_value = row["message_text"]
    return text_value.strip() if text_value and text_value.strip() else None


def _legacy_namespace(row: object) -> SimpleNamespace:
    return SimpleNamespace(**dict(row))


def _legacy_message_namespace(row: object) -> SimpleNamespace:
    data = dict(row)
    data.setdefault("idempotency_key", None)
    data.setdefault("metadata_", data.pop("metadata", None))
    if "metadata" in data:
        data.pop("metadata")
    return SimpleNamespace(**data)


def _normalize_legacy_string(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


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


async def _resolve_orange_park_start_reply_legacy(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    business: object,
    conversation: object,
    incoming_message: object,
    customer_message_text: str,
    channel: str,
    raw_payload: dict[str, Any] | None,
) -> _ReplyResolution | None:
    if not _orange_park_start_applies(business, channel, customer_message_text):
        return None

    reply_text = ORANGE_PARK_START_WELCOME_UK
    await _archive_orange_park_pre_start_history(
        session,
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        current_message_id=incoming_message.id,
    )
    await _legacy_set_message_metadata(
        session,
        tenant_id=tenant_id,
        business_id=business.id,
        message=incoming_message,
        metadata={
            "orange_park_start_reset": {
                "stage": ORANGE_PARK_START_RESET_STAGE,
                "excluded_previous_history": True,
                "language": "uk",
            }
        },
    )
    outbound_message = await _legacy_save_outgoing_ai_message(
        session,
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        message_text=reply_text,
        channel=channel,
        ai_metadata={
            "orange_park_start_reset": True,
            "stage": ORANGE_PARK_START_RESET_STAGE,
            "used_fallback": False,
        },
    )
    return _ReplyResolution(
        reply_to_customer=reply_text,
        ai_failed=False,
        outbound_message_id=outbound_message.id,
    )


def _orange_park_start_applies(
    business: object,
    channel: str,
    customer_message_text: str,
) -> bool:
    if not _orange_park_stage1_contact_collection_only(business, channel):
        return False
    normalized = customer_message_text.strip()
    return normalized == "/start" or normalized.startswith("/start ")


async def _archive_orange_park_pre_start_history(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_message_id: uuid.UUID,
) -> None:
    await session.execute(
        text(
            """
            update messages
            set metadata = coalesce(metadata, '{}'::jsonb) || cast(:metadata as jsonb)
            where tenant_id = :tenant_id
              and business_id = :business_id
              and conversation_id = :conversation_id
              and id <> :current_message_id
            """
        ),
        {
            "metadata": json.dumps(
                {
                    "excluded_from_prompt_history": True,
                    "excluded_by_orange_park_start_reset": True,
                }
            ),
            "tenant_id": tenant_id,
            "business_id": business_id,
            "conversation_id": conversation_id,
            "current_message_id": current_message_id,
        },
    )


async def _resolve_orange_park_contact_collection_reply_legacy(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    business: object,
    conversation: object,
    incoming_message: object,
    customer_message_text: str,
    channel: str,
) -> _ReplyResolution | None:
    if not _orange_park_stage1_contact_collection_only(business, channel):
        return None

    history = await _LegacyMessageHistoryService().load_recent_conversation_history(
        session,
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
    )
    reply_text, metadata = _orange_park_contact_collection_reply_and_metadata(
        customer_message_text,
        history=history,
    )
    if reply_text is None:
        return None

    await _legacy_set_message_metadata(
        session,
        tenant_id=tenant_id,
        business_id=business.id,
        message=incoming_message,
        metadata=metadata,
    )
    outbound_message = await _legacy_save_outgoing_ai_message(
        session,
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        message_text=reply_text,
        channel=channel,
        ai_metadata={
            "orange_park_contact_collection": True,
            "stage": ORANGE_PARK_CONTACT_COLLECTION_STAGE,
            "used_fallback": False,
        },
    )
    return _ReplyResolution(
        reply_to_customer=reply_text,
        ai_failed=False,
        outbound_message_id=outbound_message.id,
    )


def _orange_park_contact_collection_reply_and_metadata(
    customer_message_text: str,
    *,
    history: ConversationHistory,
) -> tuple[str | None, dict[str, Any]]:
    phone = _extract_phone_number(customer_message_text)
    language = _orange_park_dialogue_language(
        customer_message_text,
        history=history,
    )
    metadata: dict[str, Any] = {
        "orange_park_contact_collection": {
            "stage": ORANGE_PARK_CONTACT_COLLECTION_STAGE,
            "minimum_fields": [
                "first_name",
                "last_name",
                "phone",
                "telegram_id_or_username",
                "interest_summary",
            ],
            "external_crm_stage": "disabled_stage_1",
        }
    }

    if phone is not None:
        metadata["orange_park_contact_collection"].update(
            {
                "intent": "phone_provided_missing_name",
                "phone": phone,
                "missing_fields": ["first_name", "last_name"],
            }
        )
        if language == "ru":
            return (
                "Спасибо, номер получил. Напишите, пожалуйста, имя и фамилию.",
                metadata,
            )
        if language == "en":
            return (
                "Thanks, I received your number. Please send your first and last name.",
                metadata,
            )
        return (
            "Дякую, номер отримав. Напишіть, будь ласка, ім'я та прізвище.",
            metadata,
        )

    if _is_contact_collection_trigger(customer_message_text):
        metadata["orange_park_contact_collection"].update(
            {
                "intent": "contact_collection_requested",
                "missing_fields": ["first_name", "last_name", "phone"],
            }
        )
        if language == "ru":
            return (
                "Пожалуйста, оставьте данные в таком формате:\n\n"
                "Имя:\n"
                "Фамилия:\n"
                "Телефон:",
                metadata,
            )
        if language == "en":
            return (
                "Please leave your details in this format:\n\n"
                "First name:\n"
                "Last name:\n"
                "Phone:",
                metadata,
            )
        return (
            "Будь ласка, залиште дані у такому форматі:\n\n"
            "Ім'я:\n"
            "Прізвище:\n"
            "Телефон:",
            metadata,
        )

    return None, metadata


def _orange_park_stage1_contact_collection_only(
    business: object,
    channel: str,
) -> bool:
    return (
        getattr(business, "external_id", None) == ORANGE_PARK_BUSINESS_EXTERNAL_ID
        and channel == "telegram"
    )


def _extract_phone_number(text_value: str) -> str | None:
    match = _PHONE_NUMBER_PATTERN.search(text_value)
    if match is None:
        return None
    return match.group(0).strip()


def _is_contact_collection_trigger(text_value: str) -> bool:
    normalized = text_value.casefold()
    return any(marker in normalized for marker in _HANDOFF_MARKERS) or any(
        marker in normalized for marker in _CONTACT_REQUEST_MARKERS
    )


def _orange_park_dialogue_language(
    customer_message_text: str,
    *,
    history: ConversationHistory,
) -> str:
    samples = [
        message.message_text
        for message in history.messages
        if message.sender_type == "customer"
    ]
    samples.append(customer_message_text)

    for text_value in reversed(samples):
        normalized = text_value.casefold()
        if any(marker in normalized for marker in _RUSSIAN_MARKERS) or any(
            char in normalized for char in ("ы", "э", "ё", "ъ")
        ):
            return "ru"
        if _is_clearly_english(normalized):
            return "en"
        if any(marker in normalized for marker in _UKRAINIAN_MARKERS) or any(
            char in normalized for char in ("і", "ї", "є", "ґ")
        ):
            return "uk"
    return "uk"


def _is_clearly_english(normalized_text: str) -> bool:
    ascii_letters = sum(1 for char in normalized_text if "a" <= char <= "z")
    if ascii_letters < 4:
        return False
    has_cyrillic = any("а" <= char <= "я" or char in "іїєґё" for char in normalized_text)
    if has_cyrillic:
        return False
    return any(marker in normalized_text for marker in _ENGLISH_MARKERS)


def _set_message_metadata(message: Message, metadata: dict[str, Any]) -> None:
    existing = message.metadata_ or {}
    message.metadata_ = {**existing, **metadata}


async def _legacy_set_message_metadata(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    message: object,
    metadata: dict[str, Any],
) -> None:
    message_id = getattr(message, "id")
    existing = getattr(message, "metadata_", None) or {}
    merged = {**existing, **metadata}
    setattr(message, "metadata_", merged)
    await session.execute(
        text(
            """
            update messages
            set metadata = cast(:metadata as jsonb)
            where id = :message_id
              and tenant_id = :tenant_id
              and business_id = :business_id
            """
        ),
        {
            "metadata": json.dumps(merged),
            "message_id": message_id,
            "tenant_id": tenant_id,
            "business_id": business_id,
        },
    )


def _lead_creation_enabled_for_flow(flow: Flow) -> bool:
    metadata = flow.metadata_ or {}
    if not isinstance(metadata, dict):
        return True
    return metadata.get("lead_creation_enabled") is not False


def _trace_fields_for_response(
    message_trace: MessageTrace | None,
    *,
    observability: ObservabilityContext | None,
) -> tuple[uuid.UUID | None, str | None, uuid.UUID | None]:
    correlation_id = observability.correlation_id if observability is not None else None
    if message_trace is None:
        return None, None, correlation_id
    return message_trace.id, message_trace.status, correlation_id


def _delivery_fields_for_response(
    delivery_event: DeliveryEvent | None,
) -> tuple[uuid.UUID | None, str | None, uuid.UUID | None]:
    if delivery_event is None:
        return None, None, None
    return (
        delivery_event.id,
        delivery_event.status,
        delivery_event.outbound_message_id,
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
