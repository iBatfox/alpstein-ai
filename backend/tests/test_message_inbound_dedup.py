"""E2.3 — inbound message deduplication tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.ai_reply import AiReplyResult
from app.schemas.ai_reply_orchestration import AiReplyOrchestrationOutcome
from app.services.ai_reply_orchestration_coordinator import REASON_AI_CHAIN_EXECUTED
from app.services.message_idempotency import build_inbound_idempotency_key
from app.services.message_service import MessageService
from app.services.webhook_message_service import WebhookMessageService
from tests.test_webhook_message_ai_wiring import (
    _default_flow,
    _flow_service_mock,
    _request,
)
from tests.test_webhook_message_service import (
    _lead_service_mock,
    _success_ai_coordinator as _webhook_success_ai_coordinator,
)
from tests.webhook_test_helpers import message_trace_service_mock


def _conversation(business, customer, *, flow_id: uuid.UUID, channel: str = "telegram"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow_id,
        customer_id=customer.id,
        channel=channel,
        status="open",
    )


def test_build_inbound_idempotency_key_uses_external_id_when_present():
    business_id = uuid.uuid4()
    flow_id = uuid.uuid4()
    conversation_id = uuid.uuid4()

    key = build_inbound_idempotency_key(
        business_id=business_id,
        flow_id=flow_id,
        conversation_id=conversation_id,
        channel="telegram",
        external_message_id="tg:987654321:42",
        message_text="Hello",
    )

    assert key == "ext:tg:987654321:42"


def test_build_inbound_idempotency_key_hash_stable_without_external_id():
    business_id = uuid.uuid4()
    flow_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    timestamp = datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc)

    key_a = build_inbound_idempotency_key(
        business_id=business_id,
        flow_id=flow_id,
        conversation_id=conversation_id,
        channel="website_chat",
        external_message_id=None,
        message_text="Hi there",
        message_timestamp=timestamp,
    )
    key_b = build_inbound_idempotency_key(
        business_id=business_id,
        flow_id=flow_id,
        conversation_id=conversation_id,
        channel="website_chat",
        external_message_id=None,
        message_text="Hi there",
        message_timestamp=timestamp,
    )

    assert key_a == key_b
    assert key_a.startswith("hash:")


def test_same_external_id_different_flow_produces_different_conversation_keys():
    business_id = uuid.uuid4()
    flow_a = uuid.uuid4()
    flow_b = uuid.uuid4()
    conversation_a = uuid.uuid4()
    conversation_b = uuid.uuid4()

    key_a = build_inbound_idempotency_key(
        business_id=business_id,
        flow_id=flow_a,
        conversation_id=conversation_a,
        channel="telegram",
        external_message_id="tg:1:99",
        message_text="Hi",
    )
    key_b = build_inbound_idempotency_key(
        business_id=business_id,
        flow_id=flow_b,
        conversation_id=conversation_b,
        channel="telegram",
        external_message_id="tg:1:99",
        message_text="Hi",
    )

    assert key_a == key_b == "ext:tg:1:99"


@pytest.mark.anyio
async def test_telegram_webhook_retry_does_not_duplicate_ai_response():
    from app.models.business import Business
    from app.models.customer import Customer
    from app.models.message import Message
    from app.services.message_service import IncomingMessageSaveResult

    business = Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id="demo_barbershop_001",
        name="Demo",
    )
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        phone="+41790000000",
        source_channel="telegram",
    )
    flow = _default_flow(business)
    conversation = _conversation(business, customer, flow_id=flow.id, channel="telegram")

    first_message = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="telegram",
        message_text="Привет",
        external_message_id="tg:12345:99",
    )

    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        side_effect=[
            IncomingMessageSaveResult(message=first_message, is_duplicate=False),
            IncomingMessageSaveResult(message=first_message, is_duplicate=True),
        ]
    )
    message_service.save_outgoing_ai_message = AsyncMock()
    message_service.find_last_outgoing_ai_message = AsyncMock(return_value=None)

    async def _coordinator_execute(*_args, is_duplicate: bool = False, **_kwargs):
        if is_duplicate:
            return AiReplyOrchestrationOutcome(
                is_duplicate=True,
                ai_executed=False,
                reason="duplicate_inbound",
                ai_reply=None,
            )
        return AiReplyOrchestrationOutcome(
            is_duplicate=False,
            ai_executed=True,
            reason=REASON_AI_CHAIN_EXECUTED,
            ai_reply=AiReplyResult(
                text="AI reply",
                is_success=True,
                prompt_run_id=uuid.uuid4(),
                model="gpt-4o-mini",
                provider="openai",
                error=None,
            ),
        )

    coordinator = MagicMock()
    coordinator.execute_for_incoming_message = AsyncMock(side_effect=_coordinator_execute)

    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=_lead_service_mock(business, customer, conversation),
        ai_reply_coordinator=coordinator,
        message_trace_service=message_trace_service_mock(),
    )

    request = _request(
        channel="telegram",
        message={
            "text": "Привет",
            "external_message_id": "tg:12345:99",
            "external_conversation_id": "tg:12345",
        },
    )
    session = MagicMock()
    session.flush = AsyncMock()

    first = await service.process_incoming_message(session, request)
    second = await service.process_incoming_message(session, request)

    assert first.is_duplicate is False
    assert second.is_duplicate is True
    assert message_service.save_outgoing_ai_message.await_count == 1
    non_duplicate_ai_calls = [
        call
        for call in coordinator.execute_for_incoming_message.await_args_list
        if call.kwargs.get("is_duplicate") is False
    ]
    assert len(non_duplicate_ai_calls) == 1


@pytest.mark.anyio
async def test_website_chat_webhook_retry_uses_hash_idempotency_without_external_message_id():
    from app.models.business import Business
    from app.models.customer import Customer
    from app.models.message import Message
    from app.services.message_service import IncomingMessageSaveResult

    business = Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id="demo_barbershop_001",
        name="Demo",
    )
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        phone="+41790000001",
        source_channel="website_chat",
    )
    flow = _default_flow(business)
    conversation = _conversation(
        business, customer, flow_id=flow.id, channel="website_chat"
    )
    stored = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="website_chat",
        message_text="Hello",
    )

    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        side_effect=[
            IncomingMessageSaveResult(message=stored, is_duplicate=False),
            IncomingMessageSaveResult(message=stored, is_duplicate=True),
        ]
    )
    message_service.save_outgoing_ai_message = AsyncMock()

    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=_lead_service_mock(business, customer, conversation),
        ai_reply_coordinator=_webhook_success_ai_coordinator(),
        message_trace_service=message_trace_service_mock(),
    )

    request = _request(
        channel="website_chat",
        message={
            "text": "Hello",
            "timestamp": "2026-05-28T10:00:00Z",
            "external_conversation_id": "web:session-abc",
        },
    )
    session = MagicMock()
    session.flush = AsyncMock()

    first = await service.process_incoming_message(session, request)
    second = await service.process_incoming_message(session, request)

    assert first.is_duplicate is False
    assert second.is_duplicate is True
    assert message_service.save_incoming_customer_message.await_count == 2


@pytest.mark.anyio
async def test_same_external_id_different_business_isolated_at_conversation_scope():
    tenant_id, business_a, conversation_a, customer_a = _message_service_context()
    _, business_b, conversation_b, customer_b = _message_service_context(
        tenant_id=tenant_id
    )

    service = MessageService()
    session = MagicMock()
    nested = AsyncMock()
    nested.__aenter__ = AsyncMock(return_value=None)
    nested.__aexit__ = AsyncMock(return_value=None)
    session.begin_nested.return_value = nested
    session.flush = AsyncMock()

    with patch.object(
        service,
        "find_inbound_customer_message",
        new_callable=AsyncMock,
        return_value=None,
    ):
        await service.save_incoming_customer_message(
            session,
            tenant_id=tenant_id,
            business=business_a,
            conversation=conversation_a,
            customer=customer_a,
            message_text="hello",
            external_message_id="shared-ext-id",
            flow_id=conversation_a.flow_id,
        )
        await service.save_incoming_customer_message(
            session,
            tenant_id=tenant_id,
            business=business_b,
            conversation=conversation_b,
            customer=customer_b,
            message_text="hello",
            external_message_id="shared-ext-id",
            flow_id=conversation_b.flow_id,
        )

    assert session.add.call_count == 2


def _message_service_context(*, tenant_id: uuid.UUID | None = None):
    tenant_id = tenant_id or uuid.uuid4()
    business_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    flow_id = uuid.uuid4()
    business = SimpleNamespace(id=business_id, tenant_id=tenant_id)
    customer = SimpleNamespace(
        id=customer_id, tenant_id=tenant_id, business_id=business_id
    )
    conversation = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=flow_id,
        customer_id=customer_id,
        channel="whatsapp",
    )
    return tenant_id, business, conversation, customer
