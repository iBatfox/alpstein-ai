"""Shared mocks for webhook + message trace tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.models.message_trace import TRACE_STATUS_ACCEPTED


def message_trace_service_mock(*, trace_id: uuid.UUID | None = None):
    trace = SimpleNamespace(
        id=trace_id or uuid.uuid4(),
        status=TRACE_STATUS_ACCEPTED,
    )
    service = MagicMock()
    service.record_inbound_turn = AsyncMock(return_value=trace)
    service.mark_processing = AsyncMock(return_value=trace)
    service.mark_completed = AsyncMock(return_value=trace)
    service.mark_skipped_duplicate = AsyncMock(return_value=trace)
    service.mark_failed = AsyncMock(return_value=trace)
    service.find_by_inbound_message_id = AsyncMock(return_value=None)
    return service
