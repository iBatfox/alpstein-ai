"""E2.4 — webhook path message trace wiring."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.business import Business
from app.models.customer import Customer
from app.models.message import Message
from app.schemas.ai_reply import AiReplyResult
from app.schemas.ai_reply_orchestration import AiReplyOrchestrationOutcome
from app.services.ai_reply_orchestration_coordinator import REASON_AI_CHAIN_EXECUTED
from app.services.message_service import IncomingMessageSaveResult
from app.services.webhook_message_service import WebhookMessageService
from tests.test_webhook_message_ai_wiring import (
    _default_flow,
    _flow_service_mock,
    _request,
)
from tests.test_webhook_message_service import _lead_service_mock
from tests.webhook_test_helpers import message_trace_service_mock


@pytest.mark.anyio
async def test_new_inbound_marks_trace_processing_then_completed():
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
    conversation = MagicMock(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        customer_id=customer.id,
        channel="telegram",
    )
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="telegram",
        message_text="Hi",
        external_message_id="tg:1:1",
        idempotency_key="ext:tg:1:1",
    )
    outbound = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel="telegram",
        message_text="Hello back",
    )

    trace_service = message_trace_service_mock()
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=False)
    )
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outbound)

    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=_lead_service_mock(business, customer, conversation),
        message_trace_service=trace_service,
        ai_reply_coordinator=MagicMock(
            execute_for_incoming_message=AsyncMock(
                return_value=AiReplyOrchestrationOutcome(
                    is_duplicate=False,
                    ai_executed=True,
                    reason=REASON_AI_CHAIN_EXECUTED,
                    ai_reply=AiReplyResult(
                        text="Hello back",
                        is_success=True,
                        prompt_run_id=uuid.uuid4(),
                        model="gpt-4o-mini",
                        provider="openai",
                        error=None,
                    ),
                    langfuse_trace_id="lf-abc",
                )
            )
        ),
    )

    session = MagicMock()
    session.flush = AsyncMock()

    await service.process_incoming_message(
        session,
        _request(
            channel="telegram",
            message={
                "text": "Hi",
                "external_message_id": "tg:1:1",
                "external_conversation_id": "tg:1",
            },
        ),
    )

    trace_service.record_inbound_turn.assert_awaited_once()
    trace_service.mark_processing.assert_awaited_once()
    trace_service.mark_completed.assert_awaited_once()
    completed_kwargs = trace_service.mark_completed.await_args.kwargs
    assert completed_kwargs["outbound_message_id"] == outbound.id
    assert completed_kwargs["langfuse_trace_id"] == "lf-abc"


@pytest.mark.anyio
async def test_duplicate_inbound_does_not_mark_processing_or_completed():
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
        source_channel="website_chat",
    )
    flow = _default_flow(business)
    conversation = MagicMock(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        customer_id=customer.id,
        channel="website_chat",
    )
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="website_chat",
        message_text="Hi",
    )

    trace_service = message_trace_service_mock()
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=True)
    )
    message_service.find_last_outgoing_ai_message = AsyncMock(return_value=None)

    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=_lead_service_mock(business, customer, conversation),
        message_trace_service=trace_service,
        ai_reply_coordinator=MagicMock(
            execute_for_incoming_message=AsyncMock(
                return_value=AiReplyOrchestrationOutcome(
                    is_duplicate=True,
                    ai_executed=False,
                    reason="duplicate_incoming_message",
                    ai_reply=None,
                )
            )
        ),
    )

    session = MagicMock()
    session.flush = AsyncMock()

    await service.process_incoming_message(
        session,
        _request(channel="website_chat", message={"text": "Hi"}),
    )

    trace_service.record_inbound_turn.assert_awaited_once()
    assert trace_service.record_inbound_turn.await_args.kwargs["is_duplicate"] is True
    trace_service.mark_processing.assert_not_awaited()
    trace_service.mark_completed.assert_not_awaited()
