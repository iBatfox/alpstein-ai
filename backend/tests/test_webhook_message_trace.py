"""E2.4 — webhook path message trace wiring."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.business import Business
from app.models.customer import Customer
from app.models.delivery_event import DELIVERY_STATUS_PENDING, DeliveryEvent
from app.models.message import Message
from app.schemas.ai_reply import AiReplyResult
from app.schemas.ai_reply_orchestration import AiReplyOrchestrationOutcome
from app.schemas.webhook_response import serialize_webhook_message_success
from app.services.ai_reply_orchestration_coordinator import REASON_AI_CHAIN_EXECUTED
from app.services.message_service import IncomingMessageSaveResult
from app.services.webhook_message_service import WebhookMessageService
from tests.test_webhook_message_ai_wiring import (
    _default_flow,
    _flow_service_mock,
    _request,
)
from tests.test_webhook_message_service import _lead_service_mock
from tests.webhook_test_helpers import (
    inbound_processing_lock_service_mock,
    message_trace_service_mock,
)


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
        status="open",
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
    delivery_event = DeliveryEvent(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        conversation_id=conversation.id,
        trace_id=uuid.uuid4(),
        outbound_message_id=outbound.id,
        channel="telegram",
        status=DELIVERY_STATUS_PENDING,
    )
    delivery_service = MagicMock()
    delivery_service.create_pending_for_outbound = AsyncMock(return_value=delivery_event)
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
        delivery_visibility_service=delivery_service,
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
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
    delivery_service.create_pending_for_outbound.assert_awaited_once()


@pytest.mark.anyio
async def test_webhook_process_result_includes_trace_metadata():
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
        status="open",
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
    outbound = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel="website_chat",
        message_text="ok",
    )
    trace_service = message_trace_service_mock()
    delivery_service = MagicMock()
    delivery_service.create_pending_for_outbound = AsyncMock(
        return_value=DeliveryEvent(
            id=uuid.uuid4(),
            tenant_id=business.tenant_id,
            business_id=business.id,
            flow_id=flow.id,
            conversation_id=conversation.id,
            trace_id=uuid.uuid4(),
            outbound_message_id=outbound.id,
            channel="website_chat",
            status=DELIVERY_STATUS_PENDING,
        )
    )
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=False)
    )
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outbound)

    from app.schemas.observability import ObservabilityContext

    correlation_id = uuid.uuid4()
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
        delivery_visibility_service=delivery_service,
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        ai_reply_coordinator=MagicMock(
            execute_for_incoming_message=AsyncMock(
                return_value=AiReplyOrchestrationOutcome(
                    is_duplicate=False,
                    ai_executed=True,
                    reason=REASON_AI_CHAIN_EXECUTED,
                    ai_reply=AiReplyResult(
                        text="ok",
                        is_success=True,
                        prompt_run_id=uuid.uuid4(),
                        model="gpt-4o-mini",
                        provider="openai",
                        error=None,
                    ),
                )
            )
        ),
    )

    session = MagicMock()
    session.flush = AsyncMock()
    result = await service.process_incoming_message(
        session,
        _request(channel="website_chat", message={"text": "Hi"}),
        observability=ObservabilityContext(
            correlation_id=correlation_id,
            channel="website_chat",
        ),
    )

    assert result.message_trace_id is not None
    assert result.processing_status == "completed"
    assert result.correlation_id == correlation_id
    assert result.delivery_status == DELIVERY_STATUS_PENDING
    assert result.delivery_id is not None

    payload = serialize_webhook_message_success(
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
        trace_id=str(result.message_trace_id),
        correlation_id=str(result.correlation_id),
        processing_status=result.processing_status,
        delivery_id=str(result.delivery_id),
        delivery_status=result.delivery_status,
        outbound_message_id=str(result.outbound_message_id),
    )
    assert payload["data"]["trace"]["trace_id"] == str(result.message_trace_id)
    assert payload["data"]["trace"]["processing_status"] == "completed"
    assert payload["data"]["delivery"]["delivery_status"] == DELIVERY_STATUS_PENDING


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
        status="open",
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

    trace_id = uuid.uuid4()
    trace_record = SimpleNamespace(id=trace_id, status="accepted")

    async def _record_duplicate(_session, *, is_duplicate: bool, **_kwargs):
        if is_duplicate:
            trace_record.status = "skipped_duplicate"
        return trace_record

    trace_service = message_trace_service_mock(trace_id=trace_id)
    trace_service.record_inbound_turn = AsyncMock(side_effect=_record_duplicate)
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=True)
    )
    message_service.find_last_outgoing_ai_message = AsyncMock(return_value=None)
    delivery_service = MagicMock()
    delivery_service.create_pending_for_outbound = AsyncMock()

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
        delivery_visibility_service=delivery_service,
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
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

    from app.schemas.observability import ObservabilityContext

    session = MagicMock()
    session.flush = AsyncMock()

    dup_result = await service.process_incoming_message(
        session,
        _request(channel="website_chat", message={"text": "Hi"}),
        observability=ObservabilityContext(
            correlation_id=uuid.uuid4(),
            channel="website_chat",
        ),
    )

    trace_service.record_inbound_turn.assert_awaited_once()
    assert trace_service.record_inbound_turn.await_args.kwargs["is_duplicate"] is True
    trace_service.mark_processing.assert_not_awaited()
    trace_service.mark_completed.assert_not_awaited()
    delivery_service.create_pending_for_outbound.assert_not_awaited()
    assert dup_result.message_trace_id == trace_id
    assert dup_result.processing_status == "skipped_duplicate"
    assert dup_result.delivery_id is None
