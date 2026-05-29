"""E3.5 — ingress rate limiting enforcement and observability tests."""

from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app
from app.models.rate_limit_bucket import SCOPE_ADAPTER, SCOPE_BUSINESS
from app.models.rate_limit_violation import RateLimitViolation
from app.services.rate_limit_policy import build_rate_limit_scopes
from app.services.rate_limit_service import (
    RateLimitExceededDetails,
    RateLimitExceededError,
    RateLimitService,
    sanitize_violation_metadata,
)
from app.models.business import Business
from app.models.customer import Customer
from app.models.message import Message
from app.models.message_trace import MessageTrace
from app.services.inbound_processing_lock_service import ProcessingLockAcquireResult
from app.services.message_service import IncomingMessageSaveResult
from app.services.webhook_message_service import WebhookMessageService
from tests.test_webhook_message_ai_wiring import _default_flow, _flow_service_mock, _request
from tests.test_webhook_message_service import _lead_service_mock
from tests.webhook_test_helpers import (
    delivery_visibility_service_mock,
    inbound_processing_lock_service_mock,
    message_trace_service_mock,
)

TEST_TOKEN = "e3-5-rate-limit-test"


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


def _webhook_body(channel: str = "telegram") -> dict:
    return {
        "business_id": "demo_barbershop_001",
        "channel": channel,
        "customer": {"phone": "+41790000000"},
        "message": {"text": "hello", "external_message_id": "ext-rl-1"},
    }


def _exceeded_details(scope_type: str = "conversation") -> RateLimitExceededDetails:
    return RateLimitExceededDetails(
        scope_type=scope_type,
        scope_key="scope-key",
        adapter="telegram",
        limit=30,
        window_seconds=60,
        window_start=datetime(2026, 5, 28, 12, 0, 0),
        observed_count=30,
        retry_after_seconds=15,
    )


@pytest.mark.anyio
async def test_webhook_returns_429_on_rate_limit(db_session: MagicMock, monkeypatch: pytest.MonkeyPatch):
    service = MagicMock(spec=WebhookMessageService)
    service.process_incoming_message = AsyncMock(
        side_effect=RateLimitExceededError(_exceeded_details())
    )
    monkeypatch.setattr("app.api.routes.webhook.webhook_message_service", service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_webhook_body(),
            headers=_auth_headers(),
        )

    assert response.status_code == 429
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "message_text" not in str(body)
    db_session.rollback.assert_awaited()


@pytest.mark.anyio
async def test_rate_limit_disabled_skips_consume(monkeypatch: pytest.MonkeyPatch):
    service = RateLimitService(Settings(rate_limit_enabled=False))
    session = MagicMock()
    await service.consume_ingress_request(
        session,
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        channel="telegram",
        conversation_id=uuid.uuid4(),
    )
    session.execute.assert_not_called()


@pytest.mark.anyio
async def test_duplicate_inbound_does_not_call_rate_limit():
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
        external_message_id="ext:dup",
        idempotency_key="ext:dup",
    )
    trace = MessageTrace(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        conversation_id=conversation.id,
        inbound_message_id=incoming.id,
        channel="telegram",
        status="completed",
    )

    rate_limit = MagicMock(spec=RateLimitService)
    rate_limit.consume_ingress_request = AsyncMock()

    lock_service = inbound_processing_lock_service_mock()
    lock_service.record_replay_attempt = AsyncMock(return_value=None)

    trace_service = message_trace_service_mock()
    trace_service.record_inbound_turn = AsyncMock(return_value=trace)
    trace_service.record_duplicate_retry = AsyncMock(return_value=trace)

    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=True)
    )
    message_service.find_last_outgoing_ai_message = AsyncMock(return_value=incoming)

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
        rate_limit_service=rate_limit,
        ai_reply_coordinator=MagicMock(execute_for_incoming_message=AsyncMock()),
    )

    session = MagicMock()
    session.flush = AsyncMock()
    await service.process_incoming_message(
        session,
        _request(channel="telegram", message={"text": "Hi", "external_message_id": "ext:dup"}),
    )

    rate_limit.consume_ingress_request.assert_not_awaited()


@pytest.mark.anyio
async def test_non_duplicate_calls_rate_limit_before_orchestration():
    call_order: list[str] = []

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
        external_message_id="ext:new",
        idempotency_key="ext:new",
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

    async def _consume(*args, **kwargs) -> None:
        call_order.append("rate_limit")

    rate_limit = MagicMock(spec=RateLimitService)
    rate_limit.consume_ingress_request = AsyncMock(side_effect=_consume)

    lock_service = inbound_processing_lock_service_mock()
    acquired_lock = MagicMock()
    lock_service.acquire_processing_owner = AsyncMock(
        return_value=ProcessingLockAcquireResult(
            acquired=True,
            conflict=False,
            lock=acquired_lock,
        )
    )
    lock_service.release = AsyncMock()

    trace_service = message_trace_service_mock()
    trace_service.record_inbound_turn = AsyncMock(return_value=trace)

    adapter_monitoring = MagicMock()
    adapter_monitoring.should_reject_ingress_for_channel = AsyncMock(
        side_effect=lambda *a, **k: call_order.append("ingress_gate") or False
    )

    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=MagicMock(
            save_incoming_customer_message=AsyncMock(
                return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=False)
            )
        ),
        lead_service=_lead_service_mock(business, customer, conversation),
        message_trace_service=trace_service,
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=lock_service,
        rate_limit_service=rate_limit,
        adapter_monitoring_service=adapter_monitoring,
        ai_reply_coordinator=MagicMock(),
    )

    async def _resolve(*args, **kwargs) -> SimpleNamespace:
        call_order.append("orchestration")
        return SimpleNamespace(
            reply_to_customer="ok",
            outbound_message_id=None,
            langfuse_trace_id=None,
            prompt_run_id=None,
            ai_failed=False,
        )

    service._resolve_reply_to_customer = AsyncMock(side_effect=_resolve)
    service._create_pending_delivery_if_outbound = AsyncMock(return_value=None)

    session = MagicMock()
    session.flush = AsyncMock()
    await service.process_incoming_message(
        session,
        _request(channel="telegram", message={"text": "Hi", "external_message_id": "ext:new"}),
    )

    assert call_order == ["rate_limit", "ingress_gate", "orchestration"]
    rate_limit.consume_ingress_request.assert_awaited_once()


@pytest.mark.anyio
async def test_list_rate_limits_requires_tenant_scope(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    row = RateLimitViolation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        scope_type="conversation",
        scope_key=str(uuid.uuid4()),
        channel="telegram",
        conversation_id=uuid.uuid4(),
        limit_value=30,
        window_seconds=60,
        window_start=datetime.utcnow(),
        observed_count=31,
        correlation_id="corr-1",
        metadata_={"limit": 30},
        created_at=datetime.utcnow(),
    )
    monkeypatch.setattr(
        "app.api.routes.observability.rate_limit_service.list_violations",
        AsyncMock(return_value=[row]),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/observability/rate-limits",
            params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["items"]) == 1
    item = body["data"]["items"][0]
    assert item["scope_type"] == "conversation"
    assert "message_text" not in item
    assert "password" not in item


def test_violation_metadata_sanitizer_removes_pii_fields():
    assert sanitize_violation_metadata({"limit": 1, "message_text": "hi"}) == {"limit": 1}


def test_adapter_scopes_isolated_per_channel():
    business_id = str(uuid.uuid4())
    scopes_tg = build_rate_limit_scopes(
        tenant_id=str(uuid.uuid4()),
        business_id=business_id,
        channel="telegram",
        conversation_id=str(uuid.uuid4()),
    )
    scopes_web = build_rate_limit_scopes(
        tenant_id=str(uuid.uuid4()),
        business_id=business_id,
        channel="website_chat",
        conversation_id=str(uuid.uuid4()),
    )
    tg = next(s for s in scopes_tg if s.scope_type == SCOPE_ADAPTER)
    web = next(s for s in scopes_web if s.scope_type == SCOPE_ADAPTER)
    assert tg.limit == web.limit
    assert tg.scope_key != web.scope_key


def test_business_scope_shared_across_channels():
    business_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    conv = str(uuid.uuid4())
    tg = next(
        s
        for s in build_rate_limit_scopes(
            tenant_id=tenant_id,
            business_id=business_id,
            channel="telegram",
            conversation_id=conv,
        )
        if s.scope_type == SCOPE_BUSINESS
    )
    web = next(
        s
        for s in build_rate_limit_scopes(
            tenant_id=tenant_id,
            business_id=business_id,
            channel="website_chat",
            conversation_id=conv,
        )
        if s.scope_type == SCOPE_BUSINESS
    )
    assert tg.scope_key == web.scope_key == business_id
