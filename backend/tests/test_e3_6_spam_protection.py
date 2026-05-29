"""E3.6 — spam protection enforcement and observability tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app
from app.models.spam_containment import SpamContainment
from app.models.spam_decision import DECISION_MARK_SUSPICIOUS, OUTCOME_APPLIED, SpamDecision
from app.models.spam_indicator_bucket import SCOPE_CONVERSATION
from app.services.spam_payload_fingerprint import compute_payload_hash
from app.services.spam_policy import (
    RULE_ADAPTER_FANOUT,
    RULE_CONVERSATION_BURST,
    RULE_PAYLOAD_REPEAT,
    RULE_REPLAY_STORM,
    RULE_RETRY_ABUSE,
    spam_policy_config,
)
from app.services.spam_protection_service import (
    SpamContainedError,
    SpamProtectionService,
    SpamThrottledError,
)
from app.services.webhook_message_service import WebhookMessageService
from tests.test_webhook_message_ai_wiring import _default_flow, _flow_service_mock, _request
from tests.test_webhook_message_service import _lead_service_mock
from tests.webhook_test_helpers import (
    delivery_visibility_service_mock,
    inbound_processing_lock_service_mock,
    message_trace_service_mock,
)

TEST_TOKEN = "e3-6-spam-test"


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


def _low_threshold_settings(**overrides) -> Settings:
    base = dict(
        spam_protection_enabled=True,
        spam_production_safe_mode=True,
        spam_rule_payload_repeat_threshold=2,
        spam_rule_conversation_burst_threshold=999,
        spam_rule_adapter_fanout_threshold=999,
        spam_rule_retry_abuse_threshold=999,
        spam_rule_replay_storm_threshold=999,
    )
    base.update(overrides)
    return Settings(**base)


@pytest.mark.anyio
async def test_spam_disabled_skips_evaluation():
    service = SpamProtectionService(Settings(spam_protection_enabled=False))
    session = MagicMock()
    await service.evaluate_ingress_request(
        session,
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        channel="telegram",
        conversation_id=uuid.uuid4(),
        message_text="spam spam spam",
    )
    session.execute.assert_not_called()


@pytest.mark.anyio
async def test_production_safe_mode_marks_suspicious_without_blocking(monkeypatch: pytest.MonkeyPatch):
    service = SpamProtectionService(_low_threshold_settings())
    session = MagicMock()
    session.flush = AsyncMock()

    recorded: list[SpamDecision] = []

    async def _record(**kwargs) -> SpamDecision:
        row = SpamDecision(
            id=uuid.uuid4(),
            tenant_id=kwargs["tenant_id"],
            business_id=kwargs["business_id"],
            rule_id=kwargs["rule_id"],
            scope_type=kwargs["scope_type"],
            scope_key=kwargs["scope_key"],
            channel=kwargs["channel"],
            conversation_id=kwargs["conversation_id"],
            decision=kwargs["decision"],
            outcome=kwargs["outcome"],
            observed_count=kwargs["observed_count"],
            threshold=kwargs["threshold"],
            window_seconds=kwargs["window_seconds"],
            containment_id=kwargs["containment_id"],
            correlation_id=kwargs["correlation_id"],
            metadata_=kwargs["metadata"],
            created_at=datetime.utcnow(),
        )
        recorded.append(row)
        return row

    monkeypatch.setattr(service, "_record_decision_isolated", AsyncMock(side_effect=_record))
    monkeypatch.setattr(service, "_find_active_containment", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_increment_bucket", AsyncMock(return_value=2))
    monkeypatch.setattr(service, "_count_adapter_fanout_buckets", AsyncMock(return_value=0))
    monkeypatch.setattr(service, "_count_replay_events", AsyncMock(return_value=0))
    monkeypatch.setattr(service, "_count_replay_ignored_for_channel", AsyncMock(return_value=0))

    await service.evaluate_ingress_request(
        session,
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        channel="telegram",
        conversation_id=uuid.uuid4(),
        message_text="same text",
        correlation_id="corr-1",
    )

    assert recorded
    assert recorded[0].decision == DECISION_MARK_SUSPICIOUS
    assert recorded[0].outcome == OUTCOME_APPLIED
    assert "message_text" not in str(recorded[0].metadata_ or {})


@pytest.mark.anyio
async def test_blocking_mode_raises_when_production_safe_off(monkeypatch: pytest.MonkeyPatch):
    service = SpamProtectionService(
        _low_threshold_settings(
            spam_production_safe_mode=False,
            spam_rule_payload_repeat_action="throttle",
        )
    )
    session = MagicMock()
    session.flush = AsyncMock()
    monkeypatch.setattr(service, "_find_active_containment", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_increment_bucket", AsyncMock(return_value=2))
    monkeypatch.setattr(service, "_count_adapter_fanout_buckets", AsyncMock(return_value=0))
    monkeypatch.setattr(service, "_count_replay_events", AsyncMock(return_value=0))
    monkeypatch.setattr(service, "_count_replay_ignored_for_channel", AsyncMock(return_value=0))
    monkeypatch.setattr(service, "_record_decision_isolated", AsyncMock())
    monkeypatch.setattr(service, "_apply_containment", AsyncMock(
        return_value=SpamContainment(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            business_id=uuid.uuid4(),
            rule_id=RULE_PAYLOAD_REPEAT,
            scope_type=SCOPE_CONVERSATION,
            scope_key="scope",
            channel="telegram",
            conversation_id=uuid.uuid4(),
            action="throttle",
            expires_at=datetime.utcnow() + timedelta(seconds=300),
            released_at=None,
            correlation_id=None,
            metadata_={"observed_count": 2, "threshold": 2, "window_seconds": 300},
            created_at=datetime.utcnow(),
        )
    ))

    with pytest.raises(SpamThrottledError):
        await service.evaluate_ingress_request(
            session,
            tenant_id=uuid.uuid4(),
            business_id=uuid.uuid4(),
            channel="telegram",
            conversation_id=uuid.uuid4(),
            message_text="same text",
        )


@pytest.mark.anyio
async def test_list_containments_filters_expired_in_service_logic():
    service = SpamProtectionService(Settings(spam_protection_enabled=True))
    now = datetime.utcnow()
    active = SpamContainment(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        rule_id=RULE_PAYLOAD_REPEAT,
        scope_type=SCOPE_CONVERSATION,
        scope_key="scope",
        channel="telegram",
        conversation_id=uuid.uuid4(),
        action="throttle",
        expires_at=now + timedelta(seconds=60),
        released_at=None,
        correlation_id=None,
        metadata_={},
        created_at=now,
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [active]
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    rows = await service.list_containments(
        session,
        tenant_id=active.tenant_id,
        business_id=active.business_id,
        active_only=True,
    )
    assert rows == [active]


@pytest.mark.anyio
async def test_webhook_returns_429_on_spam_throttled(db_session: MagicMock, monkeypatch: pytest.MonkeyPatch):
    service = MagicMock(spec=WebhookMessageService)
    service.process_incoming_message = AsyncMock(
        side_effect=SpamThrottledError(
            SimpleNamespace(
                to_error_metadata=lambda: {
                    "rule_id": RULE_PAYLOAD_REPEAT,
                    "decision": "throttle",
                }
            )
        )
    )
    monkeypatch.setattr("app.api.routes.webhook.webhook_message_service", service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json={
                "business_id": "demo_barbershop_001",
                "channel": "telegram",
                "customer": {"phone": "+41790000000"},
                "message": {"text": "hello"},
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "SPAM_THROTTLED"


@pytest.mark.anyio
async def test_list_spam_decisions_is_tenant_scoped(db_session: MagicMock, monkeypatch: pytest.MonkeyPatch):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    row = SpamDecision(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        rule_id=RULE_PAYLOAD_REPEAT,
        scope_type=SCOPE_CONVERSATION,
        scope_key="scope",
        channel="telegram",
        conversation_id=uuid.uuid4(),
        decision=DECISION_MARK_SUSPICIOUS,
        outcome=OUTCOME_APPLIED,
        observed_count=3,
        threshold=2,
        window_seconds=300,
        containment_id=None,
        correlation_id="corr",
        metadata_={"payload_hash_prefix": "abc123"},
        created_at=datetime.utcnow(),
    )
    monkeypatch.setattr(
        "app.api.routes.observability.spam_protection_service.list_decisions",
        AsyncMock(return_value=[row]),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/observability/spam-decisions",
            params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["items"][0]["rule_id"] == RULE_PAYLOAD_REPEAT
    assert "message_text" not in str(body)


@pytest.mark.anyio
async def test_duplicate_inbound_skips_spam_evaluation():
    from app.models.business import Business
    from app.models.customer import Customer
    from app.models.message import Message
    from app.models.message_trace import MessageTrace
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
    conversation = MagicMock(id=uuid.uuid4(), channel="telegram", status="open")
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
    spam = MagicMock(spec=SpamProtectionService)
    spam.evaluate_ingress_request = AsyncMock()
    rate_limit = MagicMock()
    rate_limit.consume_ingress_request = AsyncMock()

    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=MagicMock(
            save_incoming_customer_message=AsyncMock(
                return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=True)
            )
        ),
        lead_service=_lead_service_mock(business, customer, conversation),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        spam_protection_service=spam,
        rate_limit_service=rate_limit,
        ai_reply_coordinator=MagicMock(execute_for_incoming_message=AsyncMock()),
    )
    service.message_trace_service.record_inbound_turn = AsyncMock(return_value=trace)
    service.message_trace_service.record_duplicate_retry = AsyncMock(return_value=trace)
    service.message_service.find_last_outgoing_ai_message = AsyncMock(return_value=incoming)

    session = MagicMock()
    session.flush = AsyncMock()
    await service.process_incoming_message(
        session,
        _request(channel="telegram", message={"text": "Hi", "external_message_id": "ext:dup"}),
    )

    spam.evaluate_ingress_request.assert_not_awaited()
    rate_limit.consume_ingress_request.assert_not_awaited()


def _rule(rule_id: str):
    return next(rule for rule in spam_policy_config().rules if rule.rule_id == rule_id)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("rule_id", "mock_attr", "mock_return", "message_text"),
    [
        (RULE_PAYLOAD_REPEAT, "_increment_bucket", 3, "repeat me"),
        (RULE_CONVERSATION_BURST, "_increment_bucket", 20, "unique message"),
        (RULE_ADAPTER_FANOUT, "_count_adapter_fanout_buckets", 55, "fanout msg"),
        (RULE_RETRY_ABUSE, "_count_replay_events", 12, "retry msg"),
        (RULE_REPLAY_STORM, "_count_replay_ignored_for_channel", 25, "storm msg"),
    ],
)
async def test_rule_detection_observes_threshold_signal(
    rule_id: str,
    mock_attr: str,
    mock_return: int,
    message_text: str,
):
    service = SpamProtectionService(Settings(spam_protection_enabled=True))
    session = MagicMock()
    rule = _rule(rule_id)
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    conversation_id = uuid.uuid4()

    if mock_attr == "_increment_bucket":
        setattr(service, mock_attr, AsyncMock(return_value=mock_return))
        if rule_id == RULE_ADAPTER_FANOUT:
            service._count_adapter_fanout_buckets = AsyncMock(return_value=mock_return)
    else:
        setattr(service, mock_attr, AsyncMock(return_value=mock_return))
        service._increment_bucket = AsyncMock(return_value=1)

    result = await service._evaluate_rule(
        session,
        rule=rule,
        tenant_id=tenant_id,
        business_id=business_id,
        channel="telegram",
        conversation_id=conversation_id,
        payload_hash=compute_payload_hash(message_text),
        now=datetime.utcnow(),
    )

    assert result is not None
    assert result.observed_count == mock_return
    assert result.rule.rule_id == rule_id
    if rule_id == RULE_PAYLOAD_REPEAT:
        assert "payload_hash_prefix" in result.metadata
        assert message_text not in str(result.metadata)
