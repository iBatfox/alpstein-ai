import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.business import Business
from app.models.flow import Flow
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.lead import LEAD_PRIORITY_NORMAL, LEAD_STATUS_NEW, Lead
from app.models.message import Message
from app.schemas.ai_configuration import (
    AiConfigurationBundle,
    PlatformPromptTemplateConfig,
    TenantBehaviorConfig,
    TenantBusinessContextConfig,
    TenantChannelRulesConfig,
)
from app.schemas.ai_fallback import FallbackDecision
from app.schemas.ai_reply import AiReplyResult
from app.schemas.ai_reply_orchestration import AiReplyOrchestrationOutcome
from app.schemas.webhook import NormalizedWebhookMessageRequest
from app.services.ai_reply_fallback_service import PLATFORM_DEFAULT_FALLBACK
from app.services.ai_reply_orchestration_coordinator import (
    REASON_AI_CHAIN_EXECUTED,
    REASON_DUPLICATE_INCOMING_MESSAGE,
)
from app.services.message_service import IncomingMessageSaveResult
from app.services.webhook_message_service import (
    DUPLICATE_SAFE_ACKNOWLEDGMENT,
    WebhookMessageService,
)


def _request(**overrides) -> NormalizedWebhookMessageRequest:
    payload = {
        "business_id": "demo_barbershop_001",
        "channel": "whatsapp",
        "customer": {"phone": "+41790000000"},
        "message": {
            "text": "Book tomorrow?",
            "external_message_id": "wamid.example",
        },
    }
    payload.update(overrides)
    return NormalizedWebhookMessageRequest.model_validate(payload)


@pytest.fixture
def business() -> Business:
    return Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id="demo_barbershop_001",
        name="Demo",
    )


@pytest.fixture
def customer(business: Business) -> Customer:
    return Customer(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        phone="+41790000000",
        source_channel="whatsapp",
    )


@pytest.fixture
def conversation(business: Business, customer: Customer) -> Conversation:
    return Conversation(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        customer_id=customer.id,
        channel="whatsapp",
        status="open",
    )


@pytest.fixture
def incoming_message(
    business: Business,
    conversation: Conversation,
) -> Message:
    return Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="whatsapp",
        message_text="Book tomorrow?",
    )


def _default_flow(business: Business) -> Flow:
    return Flow(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_key="default",
        flow_name="Default flow",
        status="active",
        is_default=True,
    )


def _flow_service_mock(business: Business) -> MagicMock:
    flow_service = MagicMock()
    flow_service.resolve_for_webhook = AsyncMock(return_value=_default_flow(business))
    return flow_service


def _configuration_bundle(business: Business) -> AiConfigurationBundle:
    return AiConfigurationBundle(
        tenant_id=business.tenant_id,
        business_id=business.id,
        channel="whatsapp",
        template_key="customer_reply_v1",
        platform_template=PlatformPromptTemplateConfig(
            id=uuid.uuid4(),
            template_key="customer_reply_v1",
            template_name="Customer reply",
            version="1",
            system_prompt="Platform safety rules.",
        ),
        business_context=TenantBusinessContextConfig.missing(),
        behavior=TenantBehaviorConfig(
            present=True,
            fallback_response="Tenant fallback reply.",
        ),
        channel_rules=TenantChannelRulesConfig.missing("whatsapp"),
    )


def _base_service_mocks(
    *,
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
    is_duplicate: bool,
):
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(
            message=incoming_message,
            is_duplicate=is_duplicate,
        )
    )
    message_service.save_outgoing_ai_message = AsyncMock(
        return_value=Message(
            id=uuid.uuid4(),
            tenant_id=business.tenant_id,
            business_id=business.id,
            conversation_id=conversation.id,
            sender_type="ai",
            direction="outgoing",
            channel="whatsapp",
            message_text="outgoing",
        )
    )
    message_service.find_last_outgoing_ai_message = AsyncMock(return_value=None)

    async def _create_lead(session, **kwargs) -> Lead:
        return Lead(
            id=uuid.uuid4(),
            tenant_id=business.tenant_id,
            business_id=business.id,
            customer_id=customer.id,
            conversation_id=conversation.id,
            status=LEAD_STATUS_NEW,
            priority=LEAD_PRIORITY_NORMAL,
            source_channel="whatsapp",
        )

    lead_service = MagicMock()
    lead_service.find_active_lead = AsyncMock(return_value=None)
    lead_service.create_lead = AsyncMock(side_effect=_create_lead)
    lead_service.update_lead = AsyncMock(side_effect=lambda session, *, lead, **kw: lead)

    return {
        "business_service": MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        "customer_service": MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        "conversation_service": MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        "message_service": message_service,
        "lead_service": lead_service,
        "flow_service": _flow_service_mock(business),
    }


@pytest.mark.anyio
async def test_successful_ai_reply_returns_real_text_and_saves_outgoing(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    mocks = _base_service_mocks(
        business=business,
        customer=customer,
        conversation=conversation,
        incoming_message=incoming_message,
        is_duplicate=False,
    )
    ai_reply = AiReplyResult(
        text="Tomorrow at 10:00 works.",
        is_success=True,
        prompt_run_id=uuid.uuid4(),
        model="gpt-4o-mini",
        provider="openai",
        error=None,
    )
    mocks["ai_reply_coordinator"] = MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=False,
                ai_executed=True,
                reason=REASON_AI_CHAIN_EXECUTED,
                ai_reply=ai_reply,
            )
        )
    )
    mocks["ai_configuration_service"] = MagicMock()
    mocks["ai_fallback_service"] = MagicMock()

    session = MagicMock()
    session.flush = AsyncMock()
    service = WebhookMessageService(**mocks)

    result = await service.process_incoming_message(session, _request())

    assert result.reply_to_customer == "Tomorrow at 10:00 works."
    assert result.lead_created is True
    assert result.lead_updated is False
    assert result.notify_owner is True
    mocks["message_service"].save_outgoing_ai_message.assert_awaited_once()
    save_kwargs = mocks["message_service"].save_outgoing_ai_message.await_args.kwargs
    assert save_kwargs["message_text"] == "Tomorrow at 10:00 works."
    mocks["ai_fallback_service"].decide.assert_not_called()


@pytest.mark.anyio
async def test_ai_failure_uses_fallback_text_and_saves_outgoing(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    mocks = _base_service_mocks(
        business=business,
        customer=customer,
        conversation=conversation,
        incoming_message=incoming_message,
        is_duplicate=False,
    )
    ai_reply = AiReplyResult(
        text=None,
        is_success=False,
        prompt_run_id=uuid.uuid4(),
        model="gpt-4o-mini",
        provider="openai",
        error="timeout",
    )
    mocks["ai_reply_coordinator"] = MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=False,
                ai_executed=True,
                reason=REASON_AI_CHAIN_EXECUTED,
                ai_reply=ai_reply,
            )
        )
    )
    mocks["ai_configuration_service"] = MagicMock(
        load_for_message=AsyncMock(return_value=_configuration_bundle(business))
    )
    mocks["ai_fallback_service"] = MagicMock(
        decide=MagicMock(
            return_value=FallbackDecision(
                should_reply=True,
                fallback_text="Tenant fallback reply.",
                should_handoff=True,
                reason="ai_failure",
            )
        )
    )

    session = MagicMock()
    session.flush = AsyncMock()
    service = WebhookMessageService(**mocks)

    result = await service.process_incoming_message(session, _request())

    assert result.reply_to_customer == "Tenant fallback reply."
    mocks["message_service"].save_outgoing_ai_message.assert_awaited_once()
    assert (
        mocks["message_service"].save_outgoing_ai_message.await_args.kwargs["message_text"]
        == "Tenant fallback reply."
    )


@pytest.mark.anyio
async def test_ai_failure_without_tenant_fallback_uses_platform_default(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    mocks = _base_service_mocks(
        business=business,
        customer=customer,
        conversation=conversation,
        incoming_message=incoming_message,
        is_duplicate=False,
    )
    bundle = _configuration_bundle(business)
    bundle = AiConfigurationBundle(
        tenant_id=bundle.tenant_id,
        business_id=bundle.business_id,
        channel=bundle.channel,
        template_key=bundle.template_key,
        platform_template=bundle.platform_template,
        business_context=bundle.business_context,
        behavior=TenantBehaviorConfig.missing(),
        channel_rules=bundle.channel_rules,
    )
    ai_reply = AiReplyResult(
        text=None,
        is_success=False,
        prompt_run_id=uuid.uuid4(),
        model="gpt-4o-mini",
        provider="openai",
        error="timeout",
    )
    mocks["ai_reply_coordinator"] = MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=False,
                ai_executed=True,
                reason=REASON_AI_CHAIN_EXECUTED,
                ai_reply=ai_reply,
            )
        )
    )
    mocks["ai_configuration_service"] = MagicMock(
        load_for_message=AsyncMock(return_value=bundle)
    )
    mocks["ai_fallback_service"] = MagicMock(
        decide=MagicMock(
            return_value=FallbackDecision(
                should_reply=True,
                fallback_text=PLATFORM_DEFAULT_FALLBACK,
                should_handoff=True,
                reason="ai_failure",
            )
        )
    )

    session = MagicMock()
    session.flush = AsyncMock()
    service = WebhookMessageService(**mocks)

    result = await service.process_incoming_message(session, _request())

    assert result.reply_to_customer == PLATFORM_DEFAULT_FALLBACK


@pytest.mark.anyio
async def test_duplicate_skips_outgoing_save_and_uses_last_ai_message(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    mocks = _base_service_mocks(
        business=business,
        customer=customer,
        conversation=conversation,
        incoming_message=incoming_message,
        is_duplicate=True,
    )
    mocks["ai_reply_coordinator"] = MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=True,
                ai_executed=False,
                reason=REASON_DUPLICATE_INCOMING_MESSAGE,
                ai_reply=None,
            )
        )
    )
    mocks["message_service"].find_last_outgoing_ai_message = AsyncMock(
        return_value=Message(
            id=uuid.uuid4(),
            tenant_id=business.tenant_id,
            business_id=business.id,
            conversation_id=conversation.id,
            sender_type="ai",
            direction="outgoing",
            channel="whatsapp",
            message_text="Previous AI reply",
        )
    )
    mocks["ai_configuration_service"] = MagicMock()
    mocks["ai_fallback_service"] = MagicMock()

    session = MagicMock()
    session.flush = AsyncMock()
    service = WebhookMessageService(**mocks)

    result = await service.process_incoming_message(session, _request())

    assert result.is_duplicate is True
    assert result.reply_to_customer == "Previous AI reply"
    mocks["message_service"].save_outgoing_ai_message.assert_not_awaited()
    coordinator_kwargs = (
        mocks["ai_reply_coordinator"].execute_for_incoming_message.await_args.kwargs
    )
    assert coordinator_kwargs["is_duplicate"] is True


@pytest.mark.anyio
async def test_duplicate_without_prior_ai_message_uses_safe_acknowledgment(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    mocks = _base_service_mocks(
        business=business,
        customer=customer,
        conversation=conversation,
        incoming_message=incoming_message,
        is_duplicate=True,
    )
    mocks["ai_reply_coordinator"] = MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=True,
                ai_executed=False,
                reason=REASON_DUPLICATE_INCOMING_MESSAGE,
                ai_reply=None,
            )
        )
    )
    mocks["ai_configuration_service"] = MagicMock()
    mocks["ai_fallback_service"] = MagicMock()

    session = MagicMock()
    session.flush = AsyncMock()
    service = WebhookMessageService(**mocks)

    result = await service.process_incoming_message(session, _request())

    assert result.reply_to_customer == DUPLICATE_SAFE_ACKNOWLEDGMENT
    mocks["message_service"].save_outgoing_ai_message.assert_not_awaited()


@pytest.mark.anyio
async def test_webhook_response_does_not_expose_prompt_internals(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    mocks = _base_service_mocks(
        business=business,
        customer=customer,
        conversation=conversation,
        incoming_message=incoming_message,
        is_duplicate=False,
    )
    mocks["ai_reply_coordinator"] = MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=False,
                ai_executed=True,
                reason=REASON_AI_CHAIN_EXECUTED,
                ai_reply=AiReplyResult(
                    text="Visible reply only",
                    is_success=True,
                    prompt_run_id=uuid.uuid4(),
                    model="gpt-4o-mini",
                    provider="openai",
                    error=None,
                ),
            )
        )
    )
    mocks["ai_configuration_service"] = MagicMock()
    mocks["ai_fallback_service"] = MagicMock()

    session = MagicMock()
    session.flush = AsyncMock()
    service = WebhookMessageService(**mocks)
    result = await service.process_incoming_message(session, _request())

    serialized = json.dumps(
        {
            "reply_to_customer": result.reply_to_customer,
            "lead_created": result.lead_created,
            "notify_owner": result.notify_owner,
        }
    ).lower()
    assert "final_prompt" not in serialized
    assert "system_prompt" not in serialized
    assert "platform safety" not in serialized
