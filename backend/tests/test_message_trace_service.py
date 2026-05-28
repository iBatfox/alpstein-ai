"""E2.4 — message trace persistence tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.message_trace import (
    TRACE_STATUS_ACCEPTED,
    TRACE_STATUS_COMPLETED,
    TRACE_STATUS_FAILED,
    TRACE_STATUS_PROCESSING,
    TRACE_STATUS_SKIPPED_DUPLICATE,
    MessageTrace,
)
from app.services.message_trace_service import MessageTraceService, build_trace_metadata


@pytest.mark.anyio
async def test_get_or_create_for_inbound_creates_trace():
    service = MessageTraceService()
    session = MagicMock()
    nested = AsyncMock()
    nested.__aenter__ = AsyncMock(return_value=None)
    nested.__aexit__ = AsyncMock(return_value=None)
    session.begin_nested.return_value = nested
    session.flush = AsyncMock()

    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    flow_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    inbound_message_id = uuid.uuid4()

    with patch.object(
        service,
        "find_by_inbound_message_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        trace = await service.get_or_create_for_inbound(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            flow_id=flow_id,
            conversation_id=conversation_id,
            inbound_message_id=inbound_message_id,
            channel="telegram",
            flow_key="default",
            external_trace_id="corr-123",
        )

    assert isinstance(trace, MessageTrace)
    assert trace.status == TRACE_STATUS_ACCEPTED
    assert trace.inbound_message_id == inbound_message_id
    session.add.assert_called_once()


@pytest.mark.anyio
async def test_record_inbound_turn_duplicate_marks_skipped_without_create():
    service = MessageTraceService()
    existing = MessageTrace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        inbound_message_id=uuid.uuid4(),
        channel="telegram",
        status=TRACE_STATUS_COMPLETED,
    )
    session = MagicMock()
    session.flush = AsyncMock()

    with patch.object(
        service,
        "find_by_inbound_message_id",
        new_callable=AsyncMock,
        return_value=existing,
    ):
        result = await service.record_inbound_turn(
            session,
            tenant_id=existing.tenant_id,
            business_id=existing.business_id,
            flow_id=existing.flow_id,
            conversation_id=existing.conversation_id,
            inbound_message_id=existing.inbound_message_id,
            channel="telegram",
            is_duplicate=True,
        )

    assert result is existing
    assert result.status == TRACE_STATUS_COMPLETED
    session.add.assert_not_called()


@pytest.mark.anyio
async def test_mark_completed_links_outbound_and_observability_ids():
    service = MessageTraceService()
    trace = MessageTrace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        inbound_message_id=uuid.uuid4(),
        channel="website_chat",
        status=TRACE_STATUS_PROCESSING,
    )
    session = MagicMock()
    session.flush = AsyncMock()
    outbound_id = uuid.uuid4()

    updated = await service.mark_completed(
        session,
        trace,
        outbound_message_id=outbound_id,
        external_trace_id="corr-uuid",
        langfuse_trace_id="lf-trace-1",
        trace_metadata=build_trace_metadata(
            correlation_id=uuid.uuid4(),
            n8n_execution_id="exec-1",
        ),
    )

    assert updated.status == TRACE_STATUS_COMPLETED
    assert updated.outbound_message_id == outbound_id
    assert updated.external_trace_id == "corr-uuid"
    assert updated.langfuse_trace_id == "lf-trace-1"
    assert updated.metadata_["n8n_execution_id"] == "exec-1"


@pytest.mark.anyio
async def test_mark_failed_persists_truncated_error():
    service = MessageTraceService()
    trace = MessageTrace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        inbound_message_id=uuid.uuid4(),
        channel="telegram",
        status=TRACE_STATUS_PROCESSING,
    )
    session = MagicMock()
    session.flush = AsyncMock()

    await service.mark_failed(
        session,
        trace,
        error_type="RuntimeError",
        error_message="x" * 600,
    )

    assert trace.status == TRACE_STATUS_FAILED
    assert trace.error_type == "RuntimeError"
    assert len(trace.error_message or "") <= 500


@pytest.mark.anyio
async def test_get_or_create_retries_on_integrity_error():
    service = MessageTraceService()
    existing = MessageTrace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        inbound_message_id=uuid.uuid4(),
        channel="telegram",
        status=TRACE_STATUS_ACCEPTED,
    )
    session = MagicMock()
    nested = AsyncMock()
    nested.__aenter__ = AsyncMock(side_effect=IntegrityError("dup", {}, Exception()))
    nested.__aexit__ = AsyncMock(return_value=None)
    session.begin_nested.return_value = nested
    session.flush = AsyncMock()

    with patch.object(
        service,
        "find_by_inbound_message_id",
        new_callable=AsyncMock,
        side_effect=[None, existing],
    ):
        trace = await service.get_or_create_for_inbound(
            session,
            tenant_id=existing.tenant_id,
            business_id=existing.business_id,
            flow_id=existing.flow_id,
            conversation_id=existing.conversation_id,
            inbound_message_id=existing.inbound_message_id,
            channel="telegram",
        )

    assert trace is existing
