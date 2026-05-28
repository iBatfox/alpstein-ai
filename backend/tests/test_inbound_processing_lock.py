"""E3.1a — inbound processing lock tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.inbound_processing_lock import (
    LOCK_STATUS_COMPLETED,
    LOCK_STATUS_PROCESSING,
    InboundProcessingLock,
)
from app.services.inbound_processing_lock_service import InboundProcessingLockService


@pytest.mark.anyio
async def test_second_owner_gets_conflict_while_processing():
    service = InboundProcessingLockService(lease_seconds=600)
    session = MagicMock()
    session.flush = AsyncMock()

    now = datetime.utcnow()
    existing = InboundProcessingLock(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        channel="telegram",
        idempotency_key="ext:tg:1:1",
        status=LOCK_STATUS_PROCESSING,
        owner_correlation_id=str(uuid.uuid4()),
        replay_count=0,
        first_seen_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(seconds=600),
    )

    service.get_by_scope = AsyncMock(return_value=existing)  # type: ignore[method-assign]
    second = await service.acquire_processing_owner(
        session,
        tenant_id=existing.tenant_id,
        business_id=existing.business_id,
        flow_id=existing.flow_id,
        conversation_id=existing.conversation_id,
        channel="telegram",
        idempotency_key=existing.idempotency_key,
        owner_correlation_id=str(uuid.uuid4()),
    )
    assert second.acquired is False
    assert second.conflict is True
    assert existing.replay_count == 1


@pytest.mark.anyio
async def test_same_owner_reentrant_acquire_extends_lease():
    service = InboundProcessingLockService(lease_seconds=600)
    session = MagicMock()
    session.flush = AsyncMock()

    owner = str(uuid.uuid4())
    now = datetime.utcnow()
    existing = InboundProcessingLock(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        channel="telegram",
        idempotency_key="ext:tg:2:2",
        status=LOCK_STATUS_PROCESSING,
        owner_correlation_id=owner,
        replay_count=0,
        first_seen_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(seconds=60),
    )

    service.get_by_scope = AsyncMock(return_value=existing)  # type: ignore[method-assign]
    result = await service.acquire_processing_owner(
        session,
        tenant_id=existing.tenant_id,
        business_id=existing.business_id,
        flow_id=existing.flow_id,
        conversation_id=existing.conversation_id,
        channel="telegram",
        idempotency_key=existing.idempotency_key,
        owner_correlation_id=owner,
    )
    assert result.acquired is True
    assert result.conflict is False
    assert existing.expires_at > now


@pytest.mark.anyio
async def test_completed_lock_blocks_new_acquire():
    service = InboundProcessingLockService()
    session = MagicMock()
    session.flush = AsyncMock()
    now = datetime.utcnow()
    existing = InboundProcessingLock(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        flow_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        channel="website_chat",
        idempotency_key="hash:abc",
        status=LOCK_STATUS_COMPLETED,
        owner_correlation_id=str(uuid.uuid4()),
        replay_count=0,
        first_seen_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(seconds=60),
    )
    service.get_by_scope = AsyncMock(return_value=existing)  # type: ignore[method-assign]

    result = await service.acquire_processing_owner(
        session,
        tenant_id=existing.tenant_id,
        business_id=existing.business_id,
        flow_id=existing.flow_id,
        conversation_id=existing.conversation_id,
        channel="website_chat",
        idempotency_key=existing.idempotency_key,
        owner_correlation_id=str(uuid.uuid4()),
    )
    assert result.acquired is False
    assert result.conflict is True
