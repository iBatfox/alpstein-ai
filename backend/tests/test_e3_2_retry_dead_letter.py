"""E3.2 — retry lifecycle and dead-letter behavior."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app
from app.models.dead_letter_event import (
    DL_EVENT_DELIVERY_EXHAUSTED,
    DL_SCOPE_DELIVERY,
    DeadLetterEvent,
)
from app.models.delivery_event import (
    DELIVERY_STATUS_DEAD_LETTER,
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_FAILED,
    DELIVERY_STATUS_PENDING,
    DELIVERY_STATUS_RETRYING,
    DeliveryEvent,
)
from app.models.replay_event import REPLAY_EVENT_RETRY_EXHAUSTED
from app.models.retry_attempt import RETRY_SCOPE_DELIVERY, RETRY_STATUS_FAILED, RetryAttempt
from app.services.dead_letter_service import DeadLetterService
from app.services.delivery_visibility_service import DeliveryVisibilityService
from app.services.retry_lifecycle_service import RetryLifecycleService
from app.services.retry_policy import delivery_max_retries

TEST_TOKEN = "e3-2-retry-dead-letter-test"
SETTINGS_MAX_3 = Settings(delivery_max_retries=3)


@pytest.fixture(autouse=True)
def configure_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings", SETTINGS_MAX_3)
    monkeypatch.setattr("app.services.retry_policy.settings", SETTINGS_MAX_3)
    monkeypatch.setattr("app.core.config.settings.n8n_backend_api_token", TEST_TOKEN)
    monkeypatch.setattr("app.api.webhook_auth.settings.n8n_backend_api_token", TEST_TOKEN)


def _delivery_event(*, status: str = DELIVERY_STATUS_PENDING, retry_count: int = 0) -> DeliveryEvent:
    now = datetime(2026, 5, 28, 12, 0, 0)
    return DeliveryEvent(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        trace_id=uuid.uuid4(),
        outbound_message_id=uuid.uuid4(),
        channel="telegram",
        status=status,
        retry_count=retry_count,
        created_at=now,
        updated_at=now,
    )


def _delivery_service() -> DeliveryVisibilityService:
    dead_letter = MagicMock()
    dead_letter.record_delivery_exhausted = AsyncMock()
    return DeliveryVisibilityService(
        replay_event_service=MagicMock(record=AsyncMock()),
        retry_lifecycle_service=RetryLifecycleService(),
        dead_letter_service=dead_letter,
    )


@pytest.mark.anyio
async def test_repeated_failed_patch_increments_and_dead_letters_at_max():
    service = _delivery_service()
    session = MagicMock()
    session.flush = AsyncMock()
    event = _delivery_event(status=DELIVERY_STATUS_PENDING)

    service.get_by_id = AsyncMock(return_value=event)  # type: ignore[method-assign]

    for expected_count in (1, 2, 3):
        result = await service.report_status(
            session,
            tenant_id=event.tenant_id,
            business_id=event.business_id,
            delivery_id=event.id,
            status=DELIVERY_STATUS_FAILED,
            error_type="telegram_send_failed",
            error_message=f"attempt {expected_count}",
        )
        assert result is not None
        assert result.retry_count == expected_count

    assert result.status == DELIVERY_STATUS_DEAD_LETTER
    service.replay_event_service.record.assert_awaited()
    last_replay = service.replay_event_service.record.await_args.kwargs
    assert last_replay["event_type"] == REPLAY_EVENT_RETRY_EXHAUSTED


@pytest.mark.anyio
async def test_fourth_failed_patch_is_idempotent_on_dead_letter():
    service = _delivery_service()
    session = MagicMock()
    session.flush = AsyncMock()
    event = _delivery_event(
        status=DELIVERY_STATUS_DEAD_LETTER,
        retry_count=delivery_max_retries(SETTINGS_MAX_3),
    )
    service.get_by_id = AsyncMock(return_value=event)  # type: ignore[method-assign]

    result = await service.report_status(
        session,
        tenant_id=event.tenant_id,
        business_id=event.business_id,
        delivery_id=event.id,
        status=DELIVERY_STATUS_FAILED,
        error_type="telegram_send_failed",
        error_message="late replay",
    )

    assert result.status == DELIVERY_STATUS_DEAD_LETTER
    assert result.retry_count == delivery_max_retries(SETTINGS_MAX_3)


@pytest.mark.anyio
async def test_terminal_error_type_dead_letters_on_first_failed():
    service = _delivery_service()
    session = MagicMock()
    session.flush = AsyncMock()
    event = _delivery_event(status=DELIVERY_STATUS_PENDING)
    service.get_by_id = AsyncMock(return_value=event)  # type: ignore[method-assign]

    result = await service.report_status(
        session,
        tenant_id=event.tenant_id,
        business_id=event.business_id,
        delivery_id=event.id,
        status=DELIVERY_STATUS_FAILED,
        error_type="chat_not_found",
        error_message="invalid chat",
    )

    assert result.status == DELIVERY_STATUS_DEAD_LETTER
    assert result.retry_count == 1


@pytest.mark.anyio
async def test_retrying_blocked_when_at_max():
    service = _delivery_service()
    session = MagicMock()
    session.flush = AsyncMock()
    event = _delivery_event(
        status=DELIVERY_STATUS_FAILED,
        retry_count=delivery_max_retries(SETTINGS_MAX_3),
    )
    service.get_by_id = AsyncMock(return_value=event)  # type: ignore[method-assign]

    result = await service.report_status(
        session,
        tenant_id=event.tenant_id,
        business_id=event.business_id,
        delivery_id=event.id,
        status=DELIVERY_STATUS_RETRYING,
    )

    assert result.status == DELIVERY_STATUS_DEAD_LETTER
    assert result.retry_count == delivery_max_retries(SETTINGS_MAX_3)


@pytest.mark.anyio
async def test_delivered_to_failed_remains_terminal():
    service = _delivery_service()
    session = MagicMock()
    session.flush = AsyncMock()
    now = datetime(2026, 5, 28, 12, 0, 0)
    event = _delivery_event(status=DELIVERY_STATUS_DELIVERED)
    event.delivered_at = now
    service.get_by_id = AsyncMock(return_value=event)  # type: ignore[method-assign]

    result = await service.report_status(
        session,
        tenant_id=event.tenant_id,
        business_id=event.business_id,
        delivery_id=event.id,
        status=DELIVERY_STATUS_FAILED,
    )

    assert result.status == DELIVERY_STATUS_DELIVERED


@pytest.mark.anyio
async def test_dead_letter_upsert_is_idempotent_per_scope():
    service = DeadLetterService()
    session = MagicMock()
    session.flush = AsyncMock()
    session.add = MagicMock()

    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    delivery_id = uuid.uuid4()

    existing = DeadLetterEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        scope_type=DL_SCOPE_DELIVERY,
        scope_id=delivery_id,
        event_type=DL_EVENT_DELIVERY_EXHAUSTED,
        failure_reason="first",
        retry_count=3,
        created_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
    )

    service.get_active_by_scope = AsyncMock(return_value=existing)  # type: ignore[method-assign]

    updated = await service.record_delivery_exhausted(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        delivery_id=delivery_id,
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        trace_id=uuid.uuid4(),
        outbound_message_id=uuid.uuid4(),
        retry_count=4,
        error_type="telegram_send_failed",
        failure_reason="second",
    )

    assert updated.id == existing.id
    assert updated.retry_count == 4
    session.add.assert_not_called()


@pytest.mark.anyio
async def test_retries_api_scoped_by_tenant_business():
    from app.api.routes import observability as observability_routes

    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    delivery_id = uuid.uuid4()
    attempt = RetryAttempt(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        scope_type=RETRY_SCOPE_DELIVERY,
        scope_id=delivery_id,
        attempt_number=1,
        status=RETRY_STATUS_FAILED,
        created_at=datetime.utcnow(),
    )

    service = MagicMock()
    service.list_attempts = AsyncMock(return_value=[attempt])
    observability_routes.retry_lifecycle_service = service

    session = MagicMock()

    async def _override() -> MagicMock:
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/observability/retries",
            params={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
                "delivery_id": str(delivery_id),
            },
            headers={"X-Alpstein-Webhook-Token": TEST_TOKEN},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["scope_id"] == str(delivery_id)
    assert "raw_payload" not in body["data"]["items"][0]


@pytest.mark.anyio
async def test_dead_letter_api_scoped_by_tenant_business():
    from app.api.routes import observability as observability_routes

    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    delivery_id = uuid.uuid4()
    now = datetime.utcnow()
    row = DeadLetterEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        scope_type=DL_SCOPE_DELIVERY,
        scope_id=delivery_id,
        delivery_id=delivery_id,
        event_type=DL_EVENT_DELIVERY_EXHAUSTED,
        failure_reason="exhausted",
        retry_count=3,
        created_at=now,
        last_seen_at=now,
    )

    service = MagicMock()
    service.list_events = AsyncMock(return_value=[row])
    observability_routes.dead_letter_service = service

    session = MagicMock()

    async def _override() -> MagicMock:
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/observability/dead-letter",
            params={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
                "delivery_id": str(delivery_id),
            },
            headers={"X-Alpstein-Webhook-Token": TEST_TOKEN},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["delivery_id"] == str(delivery_id)
