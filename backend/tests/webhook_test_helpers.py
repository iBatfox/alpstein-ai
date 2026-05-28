"""Shared mocks for webhook + message trace tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.models.delivery_event import DELIVERY_STATUS_PENDING, DeliveryEvent
from app.models.message_trace import TRACE_STATUS_ACCEPTED
from app.services.inbound_processing_lock_service import ProcessingLockAcquireResult


def delivery_visibility_service_mock(
    *,
    delivery_id: uuid.UUID | None = None,
    outbound_message_id: uuid.UUID | None = None,
) -> MagicMock:
    resolved_outbound_id = outbound_message_id or uuid.uuid4()
    event = DeliveryEvent(
        id=delivery_id or uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        trace_id=uuid.uuid4(),
        outbound_message_id=resolved_outbound_id,
        channel="telegram",
        status=DELIVERY_STATUS_PENDING,
    )
    service = MagicMock()
    service.create_pending_for_outbound = AsyncMock(return_value=event)
    return service


def inbound_processing_lock_service_mock() -> MagicMock:
    lock = MagicMock()
    lock.replay_count = 0
    lock.id = uuid.uuid4()
    lock.idempotency_key = "ext:test"
    service = MagicMock()
    service.acquire_processing_owner = AsyncMock(
        return_value=ProcessingLockAcquireResult(
            acquired=True,
            conflict=False,
            lock=lock,
        )
    )
    service.release = AsyncMock(return_value=lock)
    service.record_replay_attempt = AsyncMock(return_value=lock)
    return service


def message_trace_service_mock(*, trace_id: uuid.UUID | None = None):
    trace = SimpleNamespace(
        id=trace_id or uuid.uuid4(),
        status=TRACE_STATUS_ACCEPTED,
    )

    async def _mark_completed(_session, active_trace, **_kwargs):
        active_trace.status = "completed"
        return active_trace

    async def _mark_skipped(_session, active_trace):
        active_trace.status = "skipped_duplicate"
        return active_trace

    async def _record_duplicate_retry(_session, active_trace):
        if active_trace.status in ("completed", "processing", "accepted"):
            return active_trace
        active_trace.status = "skipped_duplicate"
        return active_trace

    service = MagicMock()
    service.record_inbound_turn = AsyncMock(return_value=trace)
    service.mark_processing = AsyncMock(return_value=trace)
    service.mark_completed = AsyncMock(side_effect=_mark_completed)
    service.mark_skipped_duplicate = AsyncMock(side_effect=_mark_skipped)
    service.record_duplicate_retry = AsyncMock(side_effect=_record_duplicate_retry)
    service.mark_failed = AsyncMock(return_value=trace)
    service.find_by_inbound_message_id = AsyncMock(return_value=None)
    return service
