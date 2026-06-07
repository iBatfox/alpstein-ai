"""E2.7 — end-to-end observability continuity verification."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.base import Base
from app.main import app
from app.models.business import Business
from app.models.customer import Customer
from app.models.delivery_event import (
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_FAILED,
    DELIVERY_STATUS_PENDING,
    DeliveryEvent,
)
from app.models.message import Message
from app.models.message_trace import (
    TRACE_STATUS_COMPLETED,
    TRACE_STATUS_FAILED,
    TRACE_STATUS_SKIPPED_DUPLICATE,
    MessageTrace,
)
from app.schemas.ai_reply import AiReplyResult
from app.schemas.ai_reply_orchestration import AiReplyOrchestrationOutcome
from app.schemas.delivery_event_mapper import delivery_event_to_response
from app.schemas.message_trace_mapper import message_trace_to_response
from app.services.ai_reply_orchestration_coordinator import REASON_AI_CHAIN_EXECUTED
from app.services.delivery_visibility_service import DeliveryVisibilityService
from app.services.message_service import IncomingMessageSaveResult
from app.services.webhook_message_service import WebhookMessageService
from tests.test_webhook_message_ai_wiring import (
    _default_flow,
    _flow_service_mock,
    _request,
)
from tests.test_webhook_message_service import _lead_service_mock
from tests.webhook_test_helpers import inbound_processing_lock_service_mock
from tests.webhook_test_helpers import (
    delivery_visibility_service_mock,
    message_trace_service_mock,
)

TEST_TOKEN = "e2-continuity-test-token"
BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def configure_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.n8n_backend_api_token", TEST_TOKEN)
    monkeypatch.setattr("app.api.webhook_auth.settings.n8n_backend_api_token", TEST_TOKEN)


def _route_paths() -> set[str]:
    return {getattr(route, "path", "") or "" for route in app.routes}


def test_observability_routes_registered():
    paths = _route_paths()
    assert any("/observability/traces/{trace_id}" in p for p in paths)
    assert any("/observability/traces" in p for p in paths)
    assert any("/observability/conversations/{conversation_id}/traces" in p for p in paths)
    assert any("/observability/deliveries/{delivery_id}" in p for p in paths)
    assert any("/observability/conversations/{conversation_id}/deliveries" in p for p in paths)


def test_e2_persistence_tables_in_model_metadata():
    tables = set(Base.metadata.tables)
    assert "message_traces" in tables
    assert "delivery_events" in tables


def test_alembic_head_is_0024():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert heads == ["0024"]


def test_trace_and_delivery_mappers_share_outbound_message_id():
    outbound_id = uuid.uuid4()
    trace_id = uuid.uuid4()
    now = datetime(2026, 5, 28, 14, 0, 0)
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    inbound_id = uuid.uuid4()

    trace = MessageTrace(
        id=trace_id,
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=uuid.uuid4(),
        conversation_id=conversation_id,
        inbound_message_id=inbound_id,
        outbound_message_id=outbound_id,
        channel="telegram",
        status=TRACE_STATUS_COMPLETED,
        created_at=now,
        updated_at=now,
    )
    delivery = DeliveryEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=trace.flow_id,
        conversation_id=conversation_id,
        trace_id=trace_id,
        outbound_message_id=outbound_id,
        channel="telegram",
        status=DELIVERY_STATUS_PENDING,
        retry_count=0,
        created_at=now,
        updated_at=now,
    )

    trace_payload = message_trace_to_response(trace)
    delivery_payload = delivery_event_to_response(delivery)

    assert trace_payload.outbound_message_id == delivery_payload.outbound_message_id
    assert delivery_payload.trace_id == trace_payload.id
    assert trace_payload.inbound_message_id == str(inbound_id)


@pytest.mark.parametrize("channel", ["telegram", "website_chat"])
@pytest.mark.anyio
async def test_webhook_channel_links_trace_outbound_and_delivery_pending(channel: str):
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
        source_channel=channel,
    )
    flow = _default_flow(business)
    conversation = MagicMock(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        customer_id=customer.id,
        channel=channel,
        status="open",
    )
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel=channel,
        message_text="Hi",
        external_message_id=f"{channel}:msg-1",
        idempotency_key=f"ext:{channel}:msg-1",
    )
    outbound = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel=channel,
        message_text="Reply",
    )

    trace_record = MessageTrace(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        conversation_id=conversation.id,
        inbound_message_id=incoming.id,
        channel=channel,
        status="accepted",
    )
    trace_service = message_trace_service_mock(trace_id=trace_record.id)
    trace_service.record_inbound_turn = AsyncMock(return_value=trace_record)

    delivery_event = DeliveryEvent(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        conversation_id=conversation.id,
        trace_id=trace_record.id,
        outbound_message_id=outbound.id,
        channel=channel,
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
                        text="Reply",
                        is_success=True,
                        prompt_run_id=uuid.uuid4(),
                        model="gpt-4o-mini",
                        provider="openai",
                        error=None,
                    ),
                    langfuse_trace_id="lf-e2-continuity",
                )
            )
        ),
    )

    session = MagicMock()
    session.flush = AsyncMock()
    result = await service.process_incoming_message(
        session,
        _request(
            channel=channel,
            message={
                "text": "Hi",
                "external_message_id": f"{channel}:msg-1",
            },
        ),
    )

    completed_kwargs = trace_service.mark_completed.await_args.kwargs
    assert completed_kwargs["outbound_message_id"] == outbound.id
    assert completed_kwargs["langfuse_trace_id"] == "lf-e2-continuity"

    pending_kwargs = delivery_service.create_pending_for_outbound.await_args.kwargs
    assert pending_kwargs["outbound_message_id"] == outbound.id
    assert pending_kwargs["trace_id"] == trace_record.id
    assert pending_kwargs["channel"] == channel

    assert result.message_trace_id == trace_record.id
    assert result.outbound_message_id == outbound.id
    assert result.delivery_id == delivery_event.id
    assert result.delivery_status == DELIVERY_STATUS_PENDING


@pytest.mark.anyio
async def test_langfuse_absent_trace_and_delivery_still_complete():
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
    )
    outbound = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel="telegram",
        message_text="OK",
    )

    trace_service = message_trace_service_mock()
    delivery_service = delivery_visibility_service_mock(outbound_message_id=outbound.id)

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
                        text="OK",
                        is_success=True,
                        prompt_run_id=uuid.uuid4(),
                        model="gpt-4o-mini",
                        provider="openai",
                        error=None,
                    ),
                    langfuse_trace_id=None,
                )
            )
        ),
    )

    session = MagicMock()
    session.flush = AsyncMock()
    result = await service.process_incoming_message(
        session,
        _request(channel="telegram", message={"text": "Hi"}),
    )

    assert trace_service.mark_completed.await_args.kwargs["langfuse_trace_id"] is None
    assert result.delivery_status == DELIVERY_STATUS_PENDING
    delivery_service.create_pending_for_outbound.assert_awaited_once()


@pytest.mark.anyio
async def test_duplicate_inbound_skips_delivery_and_reuses_trace():
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
    )

    trace_id = uuid.uuid4()
    trace_service = message_trace_service_mock(trace_id=trace_id)
    delivery_service = MagicMock()
    delivery_service.create_pending_for_outbound = AsyncMock()

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

    session = MagicMock()
    session.flush = AsyncMock()
    result = await service.process_incoming_message(
        session,
        _request(channel="telegram", message={"text": "Hi"}),
    )

    delivery_service.create_pending_for_outbound.assert_not_awaited()
    message_service.save_outgoing_ai_message.assert_not_called()
    assert result.message_trace_id == trace_id
    assert result.delivery_id is None
    assert result.outbound_message_id is None


@pytest.mark.anyio
async def test_delivery_idempotent_by_outbound_message_id():
    service = DeliveryVisibilityService()
    session = MagicMock()
    session.flush = AsyncMock()

    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    outbound_id = uuid.uuid4()
    existing = DeliveryEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        trace_id=uuid.uuid4(),
        outbound_message_id=outbound_id,
        channel="website_chat",
        status=DELIVERY_STATUS_DELIVERED,
    )

    service.get_by_outbound_message_id = AsyncMock(return_value=existing)  # type: ignore[method-assign]

    result = await service.create_pending_for_outbound(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        outbound_message_id=outbound_id,
        channel="website_chat",
    )

    assert result is existing
    session.add.assert_not_called()


@pytest.mark.anyio
async def test_observability_api_trace_delivery_correlation_chain():
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    inbound_id = uuid.uuid4()
    outbound_id = uuid.uuid4()
    trace_id = uuid.uuid4()
    delivery_id = uuid.uuid4()
    correlation = str(uuid.uuid4())
    now = datetime(2026, 5, 28, 15, 0, 0)

    trace = MessageTrace(
        id=trace_id,
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=uuid.uuid4(),
        conversation_id=conversation_id,
        inbound_message_id=inbound_id,
        outbound_message_id=outbound_id,
        channel="telegram",
        status=TRACE_STATUS_COMPLETED,
        external_trace_id=correlation,
        metadata_={"correlation_id": correlation},
        created_at=now,
        updated_at=now,
    )
    delivery = DeliveryEvent(
        id=delivery_id,
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=trace.flow_id,
        conversation_id=conversation_id,
        trace_id=trace_id,
        outbound_message_id=outbound_id,
        channel="telegram",
        status=DELIVERY_STATUS_PENDING,
        retry_count=0,
        created_at=now,
        updated_at=now,
    )

    from app.api.routes import observability as observability_routes

    trace_service = MagicMock()
    trace_service.get_trace_by_id = AsyncMock(return_value=trace)
    trace_service.find_by_inbound_message_id = AsyncMock(return_value=trace)
    trace_service.list_traces_for_conversation = AsyncMock(return_value=[trace])

    delivery_service = MagicMock()
    delivery_service.get_by_id = AsyncMock(return_value=delivery)
    delivery_service.list_for_conversation = AsyncMock(return_value=[delivery])

    observability_routes.message_trace_service = trace_service
    observability_routes.delivery_visibility_service = delivery_service

    session = MagicMock()
    session.commit = AsyncMock()

    async def _override() -> MagicMock:
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override

    headers = {"X-Alpstein-Webhook-Token": TEST_TOKEN}
    params = {"tenant_id": str(tenant_id), "business_id": str(business_id)}
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            by_trace = await client.get(
                f"/api/v1/observability/traces/{trace_id}",
                params=params,
                headers=headers,
            )
            by_inbound = await client.get(
                "/api/v1/observability/traces",
                params={**params, "inbound_message_id": str(inbound_id)},
                headers=headers,
            )
            conv_traces = await client.get(
                f"/api/v1/observability/conversations/{conversation_id}/traces",
                params=params,
                headers=headers,
            )
            by_delivery = await client.get(
                f"/api/v1/observability/deliveries/{delivery_id}",
                params=params,
                headers=headers,
            )
            conv_deliveries = await client.get(
                f"/api/v1/observability/conversations/{conversation_id}/deliveries",
                params=params,
                headers=headers,
            )

        assert by_trace.status_code == 200
        assert by_inbound.status_code == 200
        assert conv_traces.status_code == 200
        assert by_delivery.status_code == 200
        assert conv_deliveries.status_code == 200

        trace_body = by_trace.json()["data"]
        delivery_body = by_delivery.json()["data"]

        assert trace_body["outbound_message_id"] == str(outbound_id)
        assert delivery_body["outbound_message_id"] == str(outbound_id)
        assert delivery_body["trace_id"] == str(trace_id)
        assert trace_body["metadata"]["correlation_id"] == correlation
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_failed_trace_visible_via_observability_api():
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    trace = MessageTrace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        inbound_message_id=uuid.uuid4(),
        channel="website_chat",
        status=TRACE_STATUS_FAILED,
        error_type="RuntimeError",
        error_message="AI timeout",
        created_at=datetime(2026, 5, 28, 15, 0, 0),
        updated_at=datetime(2026, 5, 28, 15, 0, 0),
    )

    from app.api.routes import observability as observability_routes

    observability_routes.message_trace_service = MagicMock(
        get_trace_by_id=AsyncMock(return_value=trace),
    )

    async def _override() -> MagicMock:
        yield MagicMock()

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/observability/traces/{trace.id}",
                params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
                headers={"X-Alpstein-Webhook-Token": TEST_TOKEN},
            )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == TRACE_STATUS_FAILED
        assert data["error_type"] == "RuntimeError"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_failed_delivery_report_and_read():
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    delivery_id = uuid.uuid4()
    now = datetime(2026, 5, 28, 15, 0, 0)

    pending = DeliveryEvent(
        id=delivery_id,
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        trace_id=uuid.uuid4(),
        outbound_message_id=uuid.uuid4(),
        channel="telegram",
        status=DELIVERY_STATUS_PENDING,
        retry_count=0,
        created_at=now,
        updated_at=now,
    )
    failed = DeliveryEvent(
        id=delivery_id,
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=pending.flow_id,
        conversation_id=pending.conversation_id,
        trace_id=pending.trace_id,
        outbound_message_id=pending.outbound_message_id,
        channel="telegram",
        status=DELIVERY_STATUS_FAILED,
        retry_count=0,
        error_type="TELEGRAM_API_ERROR",
        error_message="send failed",
        failed_at=now,
        created_at=now,
        updated_at=now,
    )

    from app.api.routes import observability as observability_routes

    delivery_service = MagicMock()
    delivery_service.report_status = AsyncMock(return_value=failed)
    delivery_service.get_by_id = AsyncMock(return_value=failed)
    observability_routes.delivery_visibility_service = delivery_service

    session = MagicMock()
    session.commit = AsyncMock()

    async def _override() -> MagicMock:
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override
    params = {"tenant_id": str(tenant_id), "business_id": str(business_id)}
    headers = {"X-Alpstein-Webhook-Token": TEST_TOKEN}

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            patch_resp = await client.patch(
                f"/api/v1/observability/deliveries/{delivery_id}",
                params=params,
                headers=headers,
                json={
                    "status": "failed",
                    "error_type": "TELEGRAM_API_ERROR",
                    "error_message": "send failed",
                },
            )
            get_resp = await client.get(
                f"/api/v1/observability/deliveries/{delivery_id}",
                params=params,
                headers=headers,
            )

        assert patch_resp.status_code == 200
        assert patch_resp.json()["data"]["status"] == DELIVERY_STATUS_FAILED
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["error_type"] == "TELEGRAM_API_ERROR"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_cross_business_delivery_get_returns_not_found():
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    other_business_id = uuid.uuid4()
    delivery_id = uuid.uuid4()

    from app.api.routes import observability as observability_routes

    now = datetime(2026, 5, 28, 15, 0, 0)

    async def _get_by_id(_session, *, tenant_id, business_id, delivery_id):
        if business_id == other_business_id:
            return None
        return DeliveryEvent(
            id=delivery_id,
            tenant_id=tenant_id,
            business_id=business_id,
            flow_id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            trace_id=uuid.uuid4(),
            outbound_message_id=uuid.uuid4(),
            channel="telegram",
            status=DELIVERY_STATUS_PENDING,
            retry_count=0,
            created_at=now,
            updated_at=now,
        )

    observability_routes.delivery_visibility_service = MagicMock(
        get_by_id=AsyncMock(side_effect=_get_by_id),
    )

    async def _override() -> MagicMock:
        yield MagicMock()

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ok = await client.get(
                f"/api/v1/observability/deliveries/{delivery_id}",
                params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
                headers={"X-Alpstein-Webhook-Token": TEST_TOKEN},
            )
            denied = await client.get(
                f"/api/v1/observability/deliveries/{delivery_id}",
                params={
                    "tenant_id": str(tenant_id),
                    "business_id": str(other_business_id),
                },
                headers={"X-Alpstein-Webhook-Token": TEST_TOKEN},
            )
        assert ok.status_code == 200
        assert denied.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_cross_business_trace_get_returns_not_found():
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    other_business_id = uuid.uuid4()
    trace_id = uuid.uuid4()

    from app.api.routes import observability as observability_routes

    trace = MessageTrace(
        id=trace_id,
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        inbound_message_id=uuid.uuid4(),
        channel="telegram",
        status=TRACE_STATUS_COMPLETED,
        created_at=datetime(2026, 5, 28, 15, 0, 0),
        updated_at=datetime(2026, 5, 28, 15, 0, 0),
    )

    async def _get_trace(_session, *, tenant_id, business_id, trace_id):
        if business_id == other_business_id:
            return None
        return trace

    observability_routes.message_trace_service = MagicMock(
        get_trace_by_id=AsyncMock(side_effect=_get_trace),
    )

    async def _override() -> MagicMock:
        yield MagicMock()

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ok = await client.get(
                f"/api/v1/observability/traces/{trace_id}",
                params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
                headers={"X-Alpstein-Webhook-Token": TEST_TOKEN},
            )
            denied = await client.get(
                f"/api/v1/observability/traces/{trace_id}",
                params={
                    "tenant_id": str(tenant_id),
                    "business_id": str(other_business_id),
                },
                headers={"X-Alpstein-Webhook-Token": TEST_TOKEN},
            )
        assert ok.status_code == 200
        assert denied.status_code == 404
    finally:
        app.dependency_overrides.clear()
