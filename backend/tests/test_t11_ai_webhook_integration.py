"""T11.15 — integration/regression tests for the full AI webhook path."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.config import Settings
from app.exceptions import TenantContextError
from app.models.business import Business
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.lead import (
    LEAD_PRIORITY_NORMAL,
    LEAD_PRIORITY_URGENT,
    LEAD_STATUS_NEW,
    Lead,
)
from app.models.message import Message
from app.models.prompt_run import PromptRun
from app.models.prompt_template import PromptTemplate
from app.models.tenant_ai_profile import TenantAiProfile
from app.models.tenant_business_profile import TenantBusinessProfile
from app.models.tenant_channel_setting import TenantChannelSetting
from app.models.tenant_knowledge_source import TenantKnowledgeSource
from app.schemas.webhook import NormalizedWebhookMessageRequest
from app.seed.dev_ai_configuration import PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY
from app.services.ai_configuration_service import AiConfigurationService
from app.services.ai_gateway._openai import OpenAIChatCompletionResponse
from app.services.ai_gateway_service import AiGatewayService
from app.services.ai_reply_fallback_service import PLATFORM_DEFAULT_FALLBACK
from app.services.ai_reply_orchestration_coordinator import AiReplyOrchestrationCoordinator
from app.services.ai_reply_orchestration_service import AiReplyOrchestrationService
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService
from app.services.message_service import IncomingMessageSaveResult, MessageService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.prompt_run_service import PromptRunService
from app.services.webhook_message_service import (
    DUPLICATE_SAFE_ACKNOWLEDGMENT,
    WebhookMessageService,
)
from tests.test_ai_gateway_service import MockOpenAIChatClient
from tests.webhook_test_helpers import message_trace_service_mock


def _webhook_request(**overrides: Any) -> NormalizedWebhookMessageRequest:
    payload = {
        "business_id": "demo_barbershop_001",
        "channel": "whatsapp",
        "customer": {"phone": "+41790000000"},
        "message": {
            "text": "Can I book a haircut tomorrow?",
            "external_message_id": "wamid.integration-001",
        },
    }
    payload.update(overrides)
    return NormalizedWebhookMessageRequest.model_validate(payload)


def _webhook_response_envelope(result) -> dict:
    """Mirror app.api.routes.webhook post_webhook_message success body."""
    from app.schemas.webhook_response import serialize_webhook_message_success

    return serialize_webhook_message_success(
        reply_to_customer=result.reply_to_customer,
        lead_created=result.lead_created,
        lead_updated=result.lead_updated,
        notify_owner=result.notify_owner,
        conversation_id=str(result.conversation.id),
        conversation_status=result.conversation.status,
        message_id=str(result.message.id),
        is_duplicate=result.is_duplicate,
        flow_id=str(result.flow.id),
        flow_key=result.flow.flow_key,
        lead=result.lead,
        notification=result.notification,
    )


class _IntegratedStack:
    def __init__(
        self,
        *,
        gateway_client: MockOpenAIChatClient,
        session: MagicMock,
        business: Business,
        customer: Customer,
        conversation: Conversation,
        incoming_message: Message,
        config_service: AiConfigurationService,
        knowledge_service: KnowledgeRetrievalService,
        save_incoming: AsyncMock,
    ) -> None:
        self.gateway_client = gateway_client
        self.session = session
        self.business = business
        self.customer = customer
        self.conversation = conversation
        self.incoming_message = incoming_message
        self.config_service = config_service
        self.knowledge_service = knowledge_service
        self.save_incoming = save_incoming
        self.added: list[object] = []

        gateway_settings = Settings(
            openai_api_key="integration-test-key",
            openai_model="gpt-4o-mini",
            ai_request_timeout_seconds=15.0,
        )
        message_service = MessageService()
        message_service.save_incoming_customer_message = save_incoming

        orchestration_service = AiReplyOrchestrationService(
            ai_configuration_service=config_service,
            knowledge_retrieval_service=knowledge_service,
            message_service=message_service,
            prompt_builder_service=PromptBuilderService(),
            ai_gateway_service=AiGatewayService(
                app_settings=gateway_settings,
                client=gateway_client,
            ),
            prompt_run_service=PromptRunService(),
        )
        coordinator = AiReplyOrchestrationCoordinator(
            orchestration_service=orchestration_service,
        )

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
        lead_service.update_lead = AsyncMock(
            side_effect=lambda session, *, lead, **kw: lead
        )

        self.lead_service = lead_service
        from tests.test_webhook_message_ai_wiring import _flow_service_mock

        self.webhook_service = WebhookMessageService(
            business_service=MagicMock(
                get_by_external_id=AsyncMock(return_value=business),
            ),
            flow_service=_flow_service_mock(business),
            customer_service=MagicMock(
                get_or_create_customer=AsyncMock(return_value=customer),
            ),
            conversation_service=MagicMock(
                get_or_create_open_conversation=AsyncMock(return_value=conversation),
            ),
            message_service=message_service,
            lead_service=lead_service,
            ai_reply_coordinator=coordinator,
            ai_configuration_service=config_service,
            message_trace_service=message_trace_service_mock(),
        )

    def _capture_add(self, obj: object) -> None:
        self.added.append(obj)

    def prompt_runs(self) -> list[PromptRun]:
        return [obj for obj in self.added if isinstance(obj, PromptRun)]

    def outgoing_messages(self) -> list[Message]:
        return [
            obj
            for obj in self.added
            if isinstance(obj, Message)
            and obj.sender_type == "ai"
            and obj.direction == "outgoing"
        ]


def _tenant_entities() -> tuple[Business, Customer, Conversation, Message]:
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    business = Business(
        id=business_id,
        tenant_id=tenant_id,
        external_id="demo_barbershop_001",
        name="Demo Barbershop",
    )
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        phone="+41790000000",
        source_channel="whatsapp",
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer.id,
        channel="whatsapp",
        status="open",
    )
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="whatsapp",
        message_text="Can I book a haircut tomorrow?",
        external_message_id="wamid.integration-001",
    )
    return business, customer, conversation, incoming


def _config_and_knowledge_services(
    business: Business,
    *,
    fallback_response: str | None = "We will reply shortly.",
    knowledge_sources: list[TenantKnowledgeSource] | None = None,
) -> tuple[AiConfigurationService, KnowledgeRetrievalService]:
    template = PromptTemplate(
        id=uuid.uuid4(),
        template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
        template_name="Customer reply",
        version="1",
        system_prompt="Platform core safety and role instructions.",
        is_active=True,
    )
    business_profile = TenantBusinessProfile(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        business_description="Barbershop in Zurich.",
    )
    ai_profile = TenantAiProfile(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        tone="friendly",
        fallback_response=fallback_response,
    )
    channel_setting = TenantChannelSetting(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        channel="whatsapp",
    )
    config_service = AiConfigurationService(
        business_profile_service=MagicMock(
            get_for_business=AsyncMock(return_value=business_profile),
        ),
        ai_profile_service=MagicMock(
            get_for_business=AsyncMock(return_value=ai_profile),
        ),
        channel_setting_service=MagicMock(
            get_for_channel=AsyncMock(return_value=channel_setting),
        ),
        prompt_template_service=MagicMock(
            get_by_template_key=AsyncMock(return_value=template),
        ),
    )

    sources = knowledge_sources or [
        TenantKnowledgeSource(
            id=uuid.uuid4(),
            tenant_id=business.tenant_id,
            business_id=business.id,
            source_type="faq",
            title="Hours",
            content="Mon-Fri 09:00-18:00",
            is_active=True,
            created_at=datetime(2026, 5, 1, 12, 0, 0),
        ),
    ]
    knowledge_service = KnowledgeRetrievalService(
        knowledge_source_service=MagicMock(
            list_active_for_business=AsyncMock(return_value=sources),
        ),
    )
    return config_service, knowledge_service


def _session_for_success_path(*, on_add: Any) -> MagicMock:
    async def _execute(_statement: object) -> MagicMock:
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    session = MagicMock()
    session.add = on_add
    session.flush = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    return session


def _session_for_duplicate_path(
    *,
    last_outgoing: Message | None,
    on_add: Any,
) -> MagicMock:
    async def _execute(_statement: object) -> MagicMock:
        result = MagicMock()
        result.scalar_one_or_none.return_value = last_outgoing
        return result

    session = MagicMock()
    session.add = on_add
    session.flush = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    return session


def _build_stack(
    *,
    gateway_client: MockOpenAIChatClient,
    is_duplicate: bool = False,
    last_outgoing: Message | None = None,
    fallback_response: str | None = "We will reply shortly.",
) -> _IntegratedStack:
    business, customer, conversation, incoming = _tenant_entities()
    config_service, knowledge_service = _config_and_knowledge_services(
        business,
        fallback_response=fallback_response,
    )
    added: list[object] = []

    def on_add(obj: object) -> None:
        added.append(obj)

    if is_duplicate:
        session = _session_for_duplicate_path(
            last_outgoing=last_outgoing,
            on_add=on_add,
        )
    else:
        session = _session_for_success_path(on_add=on_add)
    save_incoming = AsyncMock(
        return_value=IncomingMessageSaveResult(
            message=incoming,
            is_duplicate=is_duplicate,
        )
    )

    stack = _IntegratedStack(
        gateway_client=gateway_client,
        session=session,
        business=business,
        customer=customer,
        conversation=conversation,
        incoming_message=incoming,
        config_service=config_service,
        knowledge_service=knowledge_service,
        save_incoming=save_incoming,
    )
    stack.added = added
    return stack


@pytest.mark.anyio
async def test_non_duplicate_success_executes_full_ai_chain():
    ai_text = "Tomorrow at 10:00 works for a haircut."
    gateway_client = MockOpenAIChatClient(
        response=OpenAIChatCompletionResponse(
            content=ai_text,
            model="gpt-4o-mini",
            input_tokens=120,
            output_tokens=40,
        ),
    )
    stack = _build_stack(gateway_client=gateway_client)

    result = await stack.webhook_service.process_incoming_message(
        stack.session,
        _webhook_request(),
    )

    stack.save_incoming.assert_awaited_once()
    assert gateway_client.last_request is not None
    assert len(gateway_client.last_request.messages) >= 2

    assert len(stack.prompt_runs()) == 1
    prompt_run = stack.prompt_runs()[0]
    assert prompt_run.error is None
    assert prompt_run.result == ai_text
    assert prompt_run.tenant_id == stack.business.tenant_id
    assert prompt_run.business_id == stack.business.id

    assert len(stack.outgoing_messages()) == 1
    outgoing = stack.outgoing_messages()[0]
    assert outgoing.message_text == ai_text
    assert outgoing.sender_type == "ai"
    assert outgoing.direction == "outgoing"

    assert result.reply_to_customer == ai_text
    assert result.lead_created is True
    assert result.lead_updated is False
    assert result.notify_owner is True
    assert result.is_duplicate is False


@pytest.mark.anyio
async def test_gateway_failure_creates_prompt_run_and_fallback_outgoing():
    gateway_client = MockOpenAIChatClient(error=httpx.TimeoutException("timed out"))
    stack = _build_stack(
        gateway_client=gateway_client,
        fallback_response="Please call us back soon.",
    )

    result = await stack.webhook_service.process_incoming_message(
        stack.session,
        _webhook_request(),
    )

    assert gateway_client.last_request is not None
    assert len(stack.prompt_runs()) == 1
    assert stack.prompt_runs()[0].error is not None
    assert stack.prompt_runs()[0].result is None

    assert len(stack.outgoing_messages()) == 1
    assert stack.outgoing_messages()[0].message_text == "Please call us back soon."
    assert result.reply_to_customer == "Please call us back soon."


@pytest.mark.anyio
async def test_gateway_failure_without_tenant_fallback_uses_platform_default():
    gateway_client = MockOpenAIChatClient(error=httpx.TimeoutException("timed out"))
    stack = _build_stack(
        gateway_client=gateway_client,
        fallback_response=None,
    )

    result = await stack.webhook_service.process_incoming_message(
        stack.session,
        _webhook_request(),
    )

    assert result.reply_to_customer == PLATFORM_DEFAULT_FALLBACK
    assert stack.outgoing_messages()[0].message_text == PLATFORM_DEFAULT_FALLBACK


@pytest.mark.anyio
async def test_duplicate_skips_ai_chain_and_reuses_last_outgoing_ai_message():
    gateway_client = MockOpenAIChatClient(
        response=OpenAIChatCompletionResponse(
            content="Should not be called",
            model="gpt-4o-mini",
            input_tokens=1,
            output_tokens=1,
        ),
    )
    business, customer, conversation, incoming = _tenant_entities()
    last_outgoing = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel="whatsapp",
        message_text="Previous AI reply for duplicate retry.",
    )
    stack = _build_stack(
        gateway_client=gateway_client,
        is_duplicate=True,
        last_outgoing=last_outgoing,
    )

    result = await stack.webhook_service.process_incoming_message(
        stack.session,
        _webhook_request(),
    )

    assert gateway_client.last_request is None
    assert stack.prompt_runs() == []
    assert stack.outgoing_messages() == []
    assert result.is_duplicate is True
    assert result.reply_to_customer == "Previous AI reply for duplicate retry."
    assert result.lead_created is False
    assert result.lead_updated is False
    assert result.notify_owner is False
    stack.lead_service.find_active_lead.assert_not_awaited()
    stack.lead_service.create_lead.assert_not_awaited()
    stack.lead_service.update_lead.assert_not_awaited()


@pytest.mark.anyio
async def test_duplicate_without_prior_ai_message_uses_safe_acknowledgment():
    gateway_client = MockOpenAIChatClient(
        response=OpenAIChatCompletionResponse(
            content="unused",
            model="gpt-4o-mini",
            input_tokens=1,
            output_tokens=1,
        ),
    )
    stack = _build_stack(
        gateway_client=gateway_client,
        is_duplicate=True,
        last_outgoing=None,
    )

    result = await stack.webhook_service.process_incoming_message(
        stack.session,
        _webhook_request(),
    )

    assert gateway_client.last_request is None
    assert result.reply_to_customer == DUPLICATE_SAFE_ACKNOWLEDGMENT
    assert result.lead_created is False
    assert result.notify_owner is False


@pytest.mark.anyio
async def test_gateway_failure_sets_ai_failure_notification():
    gateway_client = MockOpenAIChatClient(error=httpx.TimeoutException("timed out"))
    stack = _build_stack(
        gateway_client=gateway_client,
        fallback_response="Please call us back soon.",
    )

    result = await stack.webhook_service.process_incoming_message(
        stack.session,
        _webhook_request(message={"text": "Can I book next week?"}),
    )

    assert result.lead_created is True
    assert result.lead_updated is False
    assert result.notify_owner is True
    assert result.notification is not None
    assert result.notification.notification_type == "ai_failure"
    assert result.notification.should_notify_owner is True


@pytest.mark.anyio
async def test_urgent_follow_up_on_active_lead_returns_urgent_lead_notification():
    gateway_client = MockOpenAIChatClient(
        response=OpenAIChatCompletionResponse(
            content="We can help you shortly.",
            model="gpt-4o-mini",
            input_tokens=10,
            output_tokens=5,
        ),
    )
    stack = _build_stack(gateway_client=gateway_client)
    active_lead = Lead(
        id=uuid.uuid4(),
        tenant_id=stack.business.tenant_id,
        business_id=stack.business.id,
        customer_id=stack.customer.id,
        conversation_id=stack.conversation.id,
        status="in_progress",
        priority=LEAD_PRIORITY_NORMAL,
        source_channel="whatsapp",
    )
    lead_service = MagicMock()
    lead_service.find_active_lead = AsyncMock(return_value=active_lead)
    lead_service.create_lead = AsyncMock()
    lead_service.update_lead = AsyncMock(
        side_effect=lambda session, *, lead, **kw: lead
    )
    stack.lead_service = lead_service
    stack.webhook_service.lead_service = lead_service

    result = await stack.webhook_service.process_incoming_message(
        stack.session,
        _webhook_request(
            message={
                "text": "URGENT: need an appointment ASAP",
                "external_message_id": "wamid.urgent-follow-up",
            },
        ),
    )

    assert result.lead_created is False
    assert result.lead_updated is True
    assert result.notify_owner is True
    assert result.notification is not None
    assert result.notification.notification_type == "urgent_lead"
    lead_service.create_lead.assert_not_awaited()
    update_kwargs = lead_service.update_lead.await_args.kwargs
    assert update_kwargs["priority"] == "urgent"


@pytest.mark.anyio
async def test_api_envelope_does_not_leak_prompt_or_raw_payload():
    gateway_client = MockOpenAIChatClient(
        response=OpenAIChatCompletionResponse(
            content="Safe customer-visible reply.",
            model="gpt-4o-mini",
            input_tokens=10,
            output_tokens=5,
        ),
    )
    stack = _build_stack(gateway_client=gateway_client)

    result = await stack.webhook_service.process_incoming_message(
        stack.session,
        _webhook_request(
            message={
                "text": "Hello",
                "external_message_id": "wamid.leak-check",
                "raw_payload": {"secret": "provider-native"},
            },
        ),
    )

    envelope = _webhook_response_envelope(result)
    serialized = json.dumps(envelope).lower()
    assert "final_prompt" not in serialized
    assert "system_prompt" not in serialized
    assert "platform core safety" not in serialized
    assert "raw_payload" not in serialized
    assert "provider-native" not in serialized
    assert envelope["data"]["reply_to_customer"] == "Safe customer-visible reply."


@pytest.mark.anyio
async def test_tenant_isolation_config_and_knowledge_use_business_scope():
    gateway_client = MockOpenAIChatClient(
        response=OpenAIChatCompletionResponse(
            content="Scoped reply",
            model="gpt-4o-mini",
            input_tokens=5,
            output_tokens=3,
        ),
    )
    stack = _build_stack(gateway_client=gateway_client)

    await stack.webhook_service.process_incoming_message(
        stack.session,
        _webhook_request(),
    )

    stack.config_service.business_profile_service.get_for_business.assert_awaited_with(
        stack.session,
        stack.business.tenant_id,
        stack.business.id,
    )
    stack.config_service.ai_profile_service.get_for_business.assert_awaited_with(
        stack.session,
        stack.business.tenant_id,
        stack.business.id,
    )
    stack.knowledge_service.knowledge_source_service.list_active_for_business.assert_awaited_with(
        stack.session,
        stack.business.tenant_id,
        stack.business.id,
    )


@pytest.mark.anyio
async def test_tenant_isolation_rejects_mis_scoped_knowledge_source():
    business, customer, conversation, incoming = _tenant_entities()
    wrong_tenant_source = TenantKnowledgeSource(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=business.id,
        source_type="faq",
        title="Wrong tenant",
        content="Must not be used",
        is_active=True,
    )
    config_service, knowledge_service = _config_and_knowledge_services(
        business,
        knowledge_sources=[wrong_tenant_source],
    )
    gateway_client = MockOpenAIChatClient(
        response=OpenAIChatCompletionResponse(
            content="unused",
            model="gpt-4o-mini",
            input_tokens=1,
            output_tokens=1,
        ),
    )
    added: list[object] = []

    stack = _IntegratedStack(
        gateway_client=gateway_client,
        session=_session_for_success_path(on_add=added.append),
        business=business,
        customer=customer,
        conversation=conversation,
        incoming_message=incoming,
        config_service=config_service,
        knowledge_service=knowledge_service,
        save_incoming=AsyncMock(
            return_value=IncomingMessageSaveResult(
                message=incoming,
                is_duplicate=False,
            )
        ),
    )

    with pytest.raises(TenantContextError):
        await stack.webhook_service.process_incoming_message(
            stack.session,
            _webhook_request(),
        )

    assert gateway_client.last_request is None
    assert [obj for obj in added if isinstance(obj, PromptRun)] == []


def test_webhook_route_module_stays_thin():
    import app.api.routes.webhook as route_module

    source = open(route_module.__file__, encoding="utf-8").read().lower()
    assert "openai" not in source
    assert "promptbuilder" not in source.replace("_", "")
    assert "httpx" not in source
