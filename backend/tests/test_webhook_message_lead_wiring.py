"""T12.6 — webhook lead + notification orchestration wiring tests."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import TenantContextError
from app.models.business import Business
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.lead import (
    LEAD_PRIORITY_NORMAL,
    LEAD_PRIORITY_URGENT,
    LEAD_STATUS_IN_PROGRESS,
    LEAD_STATUS_NEW,
    Lead,
)
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
from app.schemas.webhook_response import (
    FORBIDDEN_WEBHOOK_RESPONSE_FIELDS,
    serialize_webhook_message_success,
)
from app.services.ai_reply_orchestration_coordinator import (
    REASON_AI_CHAIN_EXECUTED,
    REASON_DUPLICATE_INCOMING_MESSAGE,
)
from app.services.message_service import IncomingMessageSaveResult
from app.services.notification_policy_service import REASON_LEAD_CREATED
from app.services.webhook_message_service import (
    DUPLICATE_SAFE_ACKNOWLEDGMENT,
    WebhookMessageService,
)
from tests.webhook_test_helpers import (
    delivery_visibility_service_mock,
    inbound_processing_lock_service_mock,
    message_trace_service_mock,
)
from tests.test_webhook_message_ai_wiring import (
    _configuration_bundle,
    _flow_service_mock,
    _request,
)


def _make_lead(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    *,
    status: str = LEAD_STATUS_NEW,
    priority: str = LEAD_PRIORITY_NORMAL,
) -> Lead:
    return Lead(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        customer_id=customer.id,
        conversation_id=conversation.id,
        status=status,
        priority=priority,
        source_channel="whatsapp",
    )


def _lead_service_mocks(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    *,
    active_lead: Lead | None = None,
) -> MagicMock:
    lead_service = MagicMock()

    async def _create_lead(session, **kwargs) -> Lead:
        return _make_lead(business, customer, conversation)

    async def _update_lead(session, *, lead: Lead, **kwargs) -> Lead:
        if "priority" in kwargs:
            lead.priority = kwargs["priority"]
        if "status" in kwargs:
            lead.status = kwargs["status"]
        if "customer_note" in kwargs:
            lead.customer_note = kwargs["customer_note"]
        return lead

    lead_service.find_active_lead = AsyncMock(return_value=active_lead)
    lead_service.create_lead = AsyncMock(side_effect=_create_lead)
    lead_service.update_lead = AsyncMock(side_effect=_update_lead)
    return lead_service


def _message_mocks(
    business: Business,
    conversation: Conversation,
    incoming_message: Message,
    *,
    is_duplicate: bool,
) -> MagicMock:
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(
            message=incoming_message,
            is_duplicate=is_duplicate,
        )
    )
    message_service.save_outgoing_ai_message = AsyncMock()
    message_service.find_last_outgoing_ai_message = AsyncMock(return_value=None)
    return message_service


def _ai_success_mocks() -> dict[str, MagicMock]:
    ai_reply = AiReplyResult(
        text="Sure, what time works?",
        is_success=True,
        prompt_run_id=uuid.uuid4(),
        model="gpt-4o-mini",
        provider="openai",
        error=None,
    )
    return {
        "ai_reply_coordinator": MagicMock(
            execute_for_incoming_message=AsyncMock(
                return_value=AiReplyOrchestrationOutcome(
                    is_duplicate=False,
                    ai_executed=True,
                    reason=REASON_AI_CHAIN_EXECUTED,
                    ai_reply=ai_reply,
                )
            )
        ),
        "ai_configuration_service": MagicMock(),
        "ai_fallback_service": MagicMock(),
    }


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
        message_text="Hello",
    )


@pytest.mark.anyio
async def test_duplicate_skips_lead_and_notification(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    lead_service = _lead_service_mocks(business, customer, conversation)
    message_service = _message_mocks(
        business,
        conversation,
        incoming_message,
        is_duplicate=True,
    )
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=lead_service,
        ai_reply_coordinator=MagicMock(
            execute_for_incoming_message=AsyncMock(
                return_value=AiReplyOrchestrationOutcome(
                    is_duplicate=True,
                    ai_executed=False,
                    reason=REASON_DUPLICATE_INCOMING_MESSAGE,
                    ai_reply=None,
                )
            )
        ),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _request(message={"text": "Hello", "external_message_id": "dup-1"}),
    )

    assert result.is_duplicate is True
    assert result.lead_created is False
    assert result.lead_updated is False
    assert result.notify_owner is False
    assert result.lead is None
    assert result.notification is None
    lead_service.find_active_lead.assert_not_awaited()
    lead_service.create_lead.assert_not_awaited()
    lead_service.update_lead.assert_not_awaited()


@pytest.mark.anyio
async def test_first_message_creates_lead_and_new_lead_notification(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    lead_service = _lead_service_mocks(business, customer, conversation)
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=_message_mocks(
            business,
            conversation,
            incoming_message,
            is_duplicate=False,
        ),
        lead_service=lead_service,
        **_ai_success_mocks(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _request(message={"text": "I'd like a haircut next week, thanks."}),
    )

    assert result.lead_created is True
    assert result.lead_updated is False
    assert result.notify_owner is True
    assert result.lead is not None
    assert result.notification is not None
    assert result.notification.notification_type == "new_lead"
    assert result.notification.should_notify_owner is True
    assert result.notification.reason == REASON_LEAD_CREATED
    lead_service.create_lead.assert_awaited_once()
    lead_service.update_lead.assert_not_awaited()


@pytest.mark.anyio
async def test_follow_up_updates_lead_without_notification(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    existing = _make_lead(
        business,
        customer,
        conversation,
        status=LEAD_STATUS_IN_PROGRESS,
    )
    lead_service = _lead_service_mocks(
        business,
        customer,
        conversation,
        active_lead=existing,
    )
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=_message_mocks(
            business,
            conversation,
            incoming_message,
            is_duplicate=False,
        ),
        lead_service=lead_service,
        **_ai_success_mocks(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _request(message={"text": "Tuesday afternoon works for me."}),
    )

    assert result.lead_created is False
    assert result.lead_updated is True
    assert result.notify_owner is False
    assert result.notification is None
    assert result.lead is not None
    lead_service.create_lead.assert_not_awaited()
    lead_service.update_lead.assert_awaited_once()


@pytest.mark.anyio
async def test_urgent_message_sets_lead_priority_and_urgent_lead_notification(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    lead_service = _lead_service_mocks(business, customer, conversation)
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=_message_mocks(
            business,
            conversation,
            incoming_message,
            is_duplicate=False,
        ),
        lead_service=lead_service,
        **_ai_success_mocks(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _request(message={"text": "URGENT: need an appointment ASAP"}),
    )

    assert result.lead_created is True
    assert result.lead_updated is False
    assert result.notify_owner is True
    assert result.notification is not None
    assert result.notification.notification_type == "urgent_lead"
    assert result.notification.priority == "urgent"
    update_kwargs = lead_service.update_lead.await_args.kwargs
    assert update_kwargs["priority"] == LEAD_PRIORITY_URGENT


@pytest.mark.anyio
async def test_handoff_message_returns_human_handoff_notification(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    lead_service = _lead_service_mocks(business, customer, conversation)
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=_message_mocks(
            business,
            conversation,
            incoming_message,
            is_duplicate=False,
        ),
        lead_service=lead_service,
        **_ai_success_mocks(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _request(message={"text": "Please let me speak to someone on your team."}),
    )

    assert result.notify_owner is True
    assert result.notification is not None
    assert result.notification.notification_type == "human_handoff"
    assert result.lead_created is True
    assert result.lead_updated is False


@pytest.mark.anyio
async def test_ai_fallback_failure_returns_ai_failure_notification(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    lead_service = _lead_service_mocks(business, customer, conversation)
    ai_reply = AiReplyResult(
        text=None,
        is_success=False,
        prompt_run_id=uuid.uuid4(),
        model="gpt-4o-mini",
        provider="openai",
        error="timeout",
    )
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=_message_mocks(
            business,
            conversation,
            incoming_message,
            is_duplicate=False,
        ),
        lead_service=lead_service,
        ai_reply_coordinator=MagicMock(
            execute_for_incoming_message=AsyncMock(
                return_value=AiReplyOrchestrationOutcome(
                    is_duplicate=False,
                    ai_executed=True,
                    reason=REASON_AI_CHAIN_EXECUTED,
                    ai_reply=ai_reply,
                )
            )
        ),
        ai_configuration_service=MagicMock(
            load_for_message=AsyncMock(return_value=_configuration_bundle(business))
        ),
        ai_fallback_service=MagicMock(
            decide=MagicMock(
                return_value=FallbackDecision(
                    should_reply=True,
                    fallback_text="Tenant fallback reply.",
                    should_handoff=False,
                    reason="ai_failure",
                )
            )
        ),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _request(message={"text": "Can I book for next week?"}),
    )

    assert result.reply_to_customer == "Tenant fallback reply."
    assert result.lead_created is True
    assert result.lead_updated is False
    assert result.notify_owner is True
    assert result.notification is not None
    assert result.notification.notification_type == "ai_failure"
    assert not (result.lead_created and result.lead_updated)


@pytest.mark.anyio
async def test_duplicate_safe_acknowledgment_does_not_set_ai_failed(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    lead_service = _lead_service_mocks(business, customer, conversation)
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=_message_mocks(
            business,
            conversation,
            incoming_message,
            is_duplicate=True,
        ),
        lead_service=lead_service,
        ai_reply_coordinator=MagicMock(
            execute_for_incoming_message=AsyncMock(
                return_value=AiReplyOrchestrationOutcome(
                    is_duplicate=True,
                    ai_executed=False,
                    reason=REASON_DUPLICATE_INCOMING_MESSAGE,
                    ai_reply=None,
                )
            )
        ),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(session, _request())

    assert result.reply_to_customer == DUPLICATE_SAFE_ACKNOWLEDGMENT
    assert result.notify_owner is False


@pytest.mark.anyio
async def test_tenant_context_mismatch_raises_before_lead_write(
    business: Business,
    conversation: Conversation,
    incoming_message: Message,
):
    mismatched_customer = Customer(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=business.id,
        phone="+41790000000",
        source_channel="whatsapp",
    )
    lead_service = _lead_service_mocks(
        business,
        mismatched_customer,
        conversation,
    )
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=mismatched_customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=_message_mocks(
            business,
            conversation,
            incoming_message,
            is_duplicate=False,
        ),
        lead_service=lead_service,
        **_ai_success_mocks(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    with pytest.raises(TenantContextError):
        await service.process_incoming_message(session, _request())

    lead_service.create_lead.assert_not_awaited()


@pytest.mark.anyio
async def test_route_envelope_includes_lead_fields_and_hides_internals(
    business: Business,
    customer: Customer,
    conversation: Conversation,
    incoming_message: Message,
):
    lead_service = _lead_service_mocks(business, customer, conversation)
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=_message_mocks(
            business,
            conversation,
            incoming_message,
            is_duplicate=False,
        ),
        lead_service=lead_service,
        **_ai_success_mocks(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _request(message={"text": "First visit — haircut please."}),
    )
    envelope = serialize_webhook_message_success(
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

    assert envelope["data"]["lead_created"] is True
    assert envelope["data"]["lead_updated"] is False
    assert envelope["data"]["notify_owner"] is True
    assert "lead" in envelope["data"]
    assert "notification" in envelope["data"]
    serialized = json.dumps(envelope).lower()
    for forbidden in FORBIDDEN_WEBHOOK_RESPONSE_FIELDS:
        assert forbidden not in serialized


def test_webhook_message_service_has_no_provider_imports():
    import ast
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "webhook_message_service.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported.intersection({"openai", "httpx", "n8n"})
    assert "openai" not in source.lower()
