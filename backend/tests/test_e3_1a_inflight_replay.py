"""E3.1a — in-flight replay protection webhook tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.business import Business
from app.models.customer import Customer
from app.models.message import Message
from app.models.message_trace import TRACE_STATUS_PROCESSING, MessageTrace
from app.services.inbound_processing_lock_service import ProcessingLockAcquireResult
from app.services.replay_event_service import ReplayEventService
from app.services.message_service import IncomingMessageSaveResult
from app.services.webhook_message_service import WebhookMessageService
from tests.test_webhook_message_ai_wiring import _default_flow, _flow_service_mock, _request
from tests.test_webhook_message_service import _lead_service_mock
from tests.webhook_test_helpers import delivery_visibility_service_mock, message_trace_service_mock


@pytest.mark.anyio
async def test_inflight_lock_conflict_skips_ai_and_preserves_processing_trace():
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
        external_message_id="tg:99:1",
        idempotency_key="ext:tg:99:1",
    )
    trace = MessageTrace(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        conversation_id=conversation.id,
        inbound_message_id=incoming.id,
        channel="telegram",
        status=TRACE_STATUS_PROCESSING,
    )

    trace_service = message_trace_service_mock()
    trace_service.record_inbound_turn = AsyncMock(return_value=trace)

    async def _preserve_processing(_session, active_trace):
        if active_trace.status == TRACE_STATUS_PROCESSING:
            return active_trace
        return active_trace

    trace_service.record_duplicate_retry = AsyncMock(side_effect=_preserve_processing)

    lock_service = MagicMock()
    lock_service.acquire_processing_owner = AsyncMock(
        return_value=ProcessingLockAcquireResult(acquired=False, conflict=True, lock=None)
    )
    lock_service.record_replay_attempt = AsyncMock()

    replay_service = MagicMock(spec=ReplayEventService)
    replay_service.record = AsyncMock()

    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=False)
    )
    message_service.find_last_outgoing_ai_message = AsyncMock(return_value=None)
    message_service.save_outgoing_ai_message = AsyncMock()

    coordinator = MagicMock()
    coordinator.execute_for_incoming_message = AsyncMock()

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
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=lock_service,
        replay_event_service=replay_service,
        ai_reply_coordinator=coordinator,
    )

    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _request(channel="telegram", message={"text": "Hi", "external_message_id": "tg:99:1"}),
    )

    assert result.is_duplicate is True
    assert result.processing_status == TRACE_STATUS_PROCESSING
    non_duplicate_ai_calls = [
        call
        for call in coordinator.execute_for_incoming_message.await_args_list
        if call.kwargs.get("is_duplicate") is False
    ]
    assert len(non_duplicate_ai_calls) == 0
    message_service.save_outgoing_ai_message.assert_not_awaited()
    trace_service.mark_processing.assert_not_awaited()
    lock_service.record_replay_attempt.assert_awaited()
    replay_calls = [
        c
        for c in replay_service.record.await_args_list
        if c.kwargs.get("event_type") == "replay_ignored"
    ]
    assert len(replay_calls) == 1


@pytest.mark.anyio
async def test_duplicate_inbound_preserves_processing_trace_status():
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
        idempotency_key="hash:site-1",
    )
    trace = MessageTrace(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        conversation_id=conversation.id,
        inbound_message_id=incoming.id,
        channel="website_chat",
        status=TRACE_STATUS_PROCESSING,
    )

    from app.services.message_trace_service import MessageTraceService

    trace_service = MessageTraceService()
    session = MagicMock()
    session.flush = AsyncMock()

    updated = await trace_service.record_duplicate_retry(session, trace)
    assert updated.status == TRACE_STATUS_PROCESSING
