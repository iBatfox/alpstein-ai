"""E3.1c — replay observability."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.business import Business
from app.models.customer import Customer
from app.models.delivery_event import DELIVERY_STATUS_DELIVERED, DeliveryEvent
from app.models.message import Message
from app.models.message_trace import MessageTrace
from app.models.replay_event import (
    REPLAY_EVENT_DUPLICATE_RETRY,
    REPLAY_EVENT_ILLEGAL_TRANSITION,
    REPLAY_EVENT_REPLAY_IGNORED,
    ReplayEvent,
)
from app.services.inbound_processing_lock_service import ProcessingLockAcquireResult
from app.services.message_service import IncomingMessageSaveResult
from app.services.replay_event_service import ReplayEventService
from app.services.webhook_message_service import WebhookMessageService
from tests.test_webhook_message_ai_wiring import _default_flow, _flow_service_mock, _request
from tests.test_webhook_message_service import _lead_service_mock
from tests.webhook_test_helpers import (
    delivery_visibility_service_mock,
    inbound_processing_lock_service_mock,
    message_trace_service_mock,
)

TEST_TOKEN = "replay-observability-test-token"


@pytest.fixture(autouse=True)
def configure_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.n8n_backend_api_token", TEST_TOKEN)
    monkeypatch.setattr("app.api.webhook_auth.settings.n8n_backend_api_token", TEST_TOKEN)


@pytest.fixture
def db_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def _override() -> MagicMock:
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override
    yield session
    app.dependency_overrides.clear()


def _auth_headers() -> dict[str, str]:
    return {"X-Alpstein-Webhook-Token": TEST_TOKEN}


@pytest.mark.anyio
async def test_duplicate_inbound_records_replay_event():
    business = Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id="demo",
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
        external_message_id="ext-dup",
        idempotency_key="ext:ext-dup",
    )
    trace = MessageTrace(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        conversation_id=conversation.id,
        inbound_message_id=incoming.id,
        channel="telegram",
        status="skipped_duplicate",
    )

    replay_service = MagicMock(spec=ReplayEventService)
    replay_service.record = AsyncMock()

    trace_service = message_trace_service_mock(trace_id=trace.id)
    trace_service.record_inbound_turn = AsyncMock(return_value=trace)

    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=True)
    )
    message_service.find_last_outgoing_ai_message = AsyncMock(return_value=None)

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
        inbound_processing_lock_service=MagicMock(
            record_replay_attempt=AsyncMock(
                return_value=MagicMock(
                    replay_count=0,
                    id=uuid.uuid4(),
                    idempotency_key="ext:ext-dup",
                )
            )
        ),
        ai_reply_coordinator=coordinator,
        replay_event_service=replay_service,
        dead_letter_service=MagicMock(record_inbound_exhausted=AsyncMock()),
        retry_lifecycle_service=MagicMock(record_inbound_attempt=AsyncMock()),
    )

    session = MagicMock()
    session.flush = AsyncMock()
    await service.process_incoming_message(
        session,
        _request(channel="telegram", message={"text": "Hi", "external_message_id": "ext-dup"}),
    )

    replay_service.record.assert_awaited_once()
    kwargs = replay_service.record.await_args.kwargs
    assert kwargs["event_type"] == REPLAY_EVENT_DUPLICATE_RETRY
    assert kwargs["source"] == "webhook"
    assert kwargs["idempotency_key"] == "ext:ext-dup"


@pytest.mark.anyio
async def test_inflight_duplicate_records_replay_ignored():
    replay_service = MagicMock(spec=ReplayEventService)
    replay_service.record = AsyncMock()

    lock_service = MagicMock()
    processing_lock = MagicMock()
    processing_lock.replay_count = 0
    processing_lock.id = uuid.uuid4()
    processing_lock.idempotency_key = "ext:ext-inflight"
    lock_service.acquire_processing_owner = AsyncMock(
        return_value=ProcessingLockAcquireResult(
            acquired=False,
            conflict=True,
            lock=processing_lock,
        )
    )
    lock_service.record_replay_attempt = AsyncMock()

    business = Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id="demo",
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
        external_message_id="ext-inflight",
        idempotency_key="ext:ext-inflight",
    )
    trace = MessageTrace(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        conversation_id=conversation.id,
        inbound_message_id=incoming.id,
        channel="telegram",
        status="processing",
    )

    trace_service = message_trace_service_mock()
    trace_service.record_inbound_turn = AsyncMock(return_value=trace)

    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=False)
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
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=lock_service,
        replay_event_service=replay_service,
        dead_letter_service=MagicMock(record_inbound_exhausted=AsyncMock()),
        retry_lifecycle_service=MagicMock(record_inbound_attempt=AsyncMock()),
        ai_reply_coordinator=MagicMock(execute_for_incoming_message=AsyncMock()),
    )

    session = MagicMock()
    session.flush = AsyncMock()
    await service.process_incoming_message(
        session,
        _request(channel="telegram", message={"text": "Hi", "external_message_id": "ext-inflight"}),
    )

    event_types = [call.kwargs["event_type"] for call in replay_service.record.await_args_list]
    assert REPLAY_EVENT_REPLAY_IGNORED in event_types


@pytest.mark.anyio
async def test_illegal_delivery_transition_records_replay_event():
    from app.services.delivery_visibility_service import DeliveryVisibilityService

    replay_service = MagicMock(spec=ReplayEventService)
    replay_service.record = AsyncMock()
    session = MagicMock()
    session.flush = AsyncMock()

    now = datetime(2026, 5, 28, 16, 0, 0)
    event = DeliveryEvent(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        trace_id=uuid.uuid4(),
        outbound_message_id=uuid.uuid4(),
        channel="telegram",
        status=DELIVERY_STATUS_DELIVERED,
        retry_count=0,
        delivered_at=now,
        created_at=now,
        updated_at=now,
    )

    service = DeliveryVisibilityService(
        replay_event_service=replay_service,
        retry_lifecycle_service=MagicMock(record_delivery_attempt=AsyncMock()),
        dead_letter_service=MagicMock(),
    )
    service.get_by_id = AsyncMock(return_value=event)  # type: ignore[method-assign]

    result = await service.report_status(
        session,
        tenant_id=event.tenant_id,
        business_id=event.business_id,
        delivery_id=event.id,
        status="failed",
    )

    assert result.status == DELIVERY_STATUS_DELIVERED
    replay_service.record.assert_awaited_once()
    assert replay_service.record.await_args.kwargs["event_type"] == REPLAY_EVENT_ILLEGAL_TRANSITION


@pytest.mark.anyio
async def test_replay_api_scoped_by_tenant_business(db_session: MagicMock):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    other_business_id = uuid.uuid4()
    trace_id = uuid.uuid4()
    now = datetime(2026, 5, 28, 12, 0, 0)
    scoped = ReplayEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        source="webhook",
        event_type=REPLAY_EVENT_REPLAY_IGNORED,
        trace_id=trace_id,
        created_at=now,
    )
    other = ReplayEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=other_business_id,
        source="webhook",
        event_type=REPLAY_EVENT_REPLAY_IGNORED,
        created_at=now,
    )

    from app.api.routes import observability as observability_routes

    service = MagicMock()

    async def _list_events(_session, *, tenant_id, business_id, trace_id=None, **_kwargs):
        if business_id != scoped.business_id:
            return []
        if trace_id is not None and trace_id != scoped.trace_id:
            return []
        return [scoped]

    service.list_events = AsyncMock(side_effect=_list_events)
    observability_routes.replay_event_service = service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/observability/replays",
            params={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
                "trace_id": str(trace_id),
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["trace_id"] == str(trace_id)
    assert "raw_payload" not in body["data"]["items"][0]
    _ = other
