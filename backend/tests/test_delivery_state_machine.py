"""E3.1b — delivery terminal state machine tests."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.delivery_event import (
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_FAILED,
    DELIVERY_STATUS_PENDING,
    DELIVERY_STATUS_RETRYING,
    DeliveryEvent,
)
from app.services.delivery_state_machine import is_delivery_transition_allowed
from app.services.delivery_visibility_service import DeliveryVisibilityService


def test_delivered_to_failed_transition_forbidden():
    assert is_delivery_transition_allowed(DELIVERY_STATUS_DELIVERED, DELIVERY_STATUS_FAILED) is False


def test_pending_to_delivered_allowed():
    assert is_delivery_transition_allowed(DELIVERY_STATUS_PENDING, DELIVERY_STATUS_DELIVERED) is True


def test_failed_to_delivered_forbidden():
    assert is_delivery_transition_allowed(DELIVERY_STATUS_FAILED, DELIVERY_STATUS_DELIVERED) is False


def test_failed_to_retrying_allowed():
    assert is_delivery_transition_allowed(DELIVERY_STATUS_FAILED, DELIVERY_STATUS_RETRYING) is True


@pytest.mark.anyio
async def test_report_status_delivered_to_failed_is_noop():
    replay_service = MagicMock()
    replay_service.record = AsyncMock()
    service = DeliveryVisibilityService(replay_event_service=replay_service)
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

    service.get_by_id = AsyncMock(return_value=event)  # type: ignore[method-assign]

    result = await service.report_status(
        session,
        tenant_id=event.tenant_id,
        business_id=event.business_id,
        delivery_id=event.id,
        status=DELIVERY_STATUS_FAILED,
        error_type="TELEGRAM_API_ERROR",
        error_message="late failure replay",
    )

    assert result is event
    assert result.status == DELIVERY_STATUS_DELIVERED
    session.flush.assert_not_awaited()
    replay_service.record.assert_awaited_once()


@pytest.mark.anyio
async def test_report_status_delivered_to_delivered_idempotent():
    replay_service = MagicMock()
    replay_service.record = AsyncMock()
    service = DeliveryVisibilityService(replay_event_service=replay_service)
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
        provider_message_id="tg-1",
        retry_count=0,
        delivered_at=now,
        created_at=now,
        updated_at=now,
    )
    service.get_by_id = AsyncMock(return_value=event)  # type: ignore[method-assign]

    result = await service.report_status(
        session,
        tenant_id=event.tenant_id,
        business_id=event.business_id,
        delivery_id=event.id,
        status=DELIVERY_STATUS_DELIVERED,
        provider_message_id="tg-1",
    )

    assert result.status == DELIVERY_STATUS_DELIVERED
    session.flush.assert_not_awaited()
