"""E2.6 — delivery visibility service tests."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.delivery_event import (
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_FAILED,
    DELIVERY_STATUS_PENDING,
    DELIVERY_STATUS_RETRYING,
    DeliveryEvent,
)
from app.services.delivery_visibility_service import DeliveryVisibilityService


def _event(
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    status: str = DELIVERY_STATUS_PENDING,
) -> DeliveryEvent:
    now = datetime(2026, 5, 28, 12, 0, 0)
    return DeliveryEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        trace_id=uuid.uuid4(),
        outbound_message_id=uuid.uuid4(),
        channel="telegram",
        status=status,
        retry_count=0,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_create_pending_returns_existing_without_insert():
    service = DeliveryVisibilityService()
    session = MagicMock()
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    existing = _event(tenant_id=tenant_id, business_id=business_id)

    with patch.object(
        service,
        "get_by_outbound_message_id",
        new_callable=AsyncMock,
        return_value=existing,
    ):
        result = await service.create_pending_for_outbound(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            flow_id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            outbound_message_id=existing.outbound_message_id,
            channel="telegram",
        )

    assert result is existing
    session.add.assert_not_called()


@pytest.mark.anyio
async def test_mark_delivered_sets_timestamp_and_clears_error():
    service = DeliveryVisibilityService()
    session = MagicMock()
    session.flush = AsyncMock()
    event = _event(
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        status=DELIVERY_STATUS_PENDING,
    )
    event.error_type = "OLD"
    event.error_message = "old"

    updated = await service.mark_delivered(
        session,
        event,
        provider_message_id="tg-99",
        provider_status="ok",
    )

    assert updated.status == DELIVERY_STATUS_DELIVERED
    assert updated.delivered_at is not None
    assert updated.failed_at is None
    assert updated.error_type is None
    assert updated.provider_message_id == "tg-99"


@pytest.mark.anyio
async def test_mark_failed_truncates_error_message():
    service = DeliveryVisibilityService()
    session = MagicMock()
    session.flush = AsyncMock()
    event = _event(tenant_id=uuid.uuid4(), business_id=uuid.uuid4())

    await service.mark_failed(
        session,
        event,
        error_type="TELEGRAM_API_ERROR",
        error_message="x" * 600,
    )

    assert event.status == DELIVERY_STATUS_FAILED
    assert event.failed_at is not None
    assert len(event.error_message or "") <= 500


@pytest.mark.anyio
async def test_increment_retry_sets_retrying_status():
    service = DeliveryVisibilityService()
    session = MagicMock()
    session.flush = AsyncMock()
    event = _event(tenant_id=uuid.uuid4(), business_id=uuid.uuid4())
    event.retry_count = 1

    await service.increment_retry(session, event)

    assert event.status == DELIVERY_STATUS_RETRYING
    assert event.retry_count == 2


@pytest.mark.anyio
async def test_report_status_returns_none_when_not_found():
    service = DeliveryVisibilityService()
    session = MagicMock()

    with patch.object(service, "get_by_id", new_callable=AsyncMock, return_value=None):
        result = await service.report_status(
            session,
            tenant_id=uuid.uuid4(),
            business_id=uuid.uuid4(),
            delivery_id=uuid.uuid4(),
            status=DELIVERY_STATUS_DELIVERED,
        )

    assert result is None
