"""Single-owner processing lock per inbound idempotency scope (E3.1a)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inbound_processing_lock import (
    LOCK_STATUS_COMPLETED,
    LOCK_STATUS_FAILED,
    LOCK_STATUS_PROCESSING,
    InboundProcessingLock,
)

DEFAULT_LEASE_SECONDS = 900


@dataclass(frozen=True)
class ProcessingLockAcquireResult:
    acquired: bool
    conflict: bool
    lock: InboundProcessingLock | None = None


class InboundProcessingLockService:
    def __init__(self, *, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> None:
        self.lease_seconds = lease_seconds

    async def get_by_scope(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        idempotency_key: str,
    ) -> InboundProcessingLock | None:
        result = await session.execute(
            select(InboundProcessingLock).where(
                InboundProcessingLock.tenant_id == tenant_id,
                InboundProcessingLock.business_id == business_id,
                InboundProcessingLock.conversation_id == conversation_id,
                InboundProcessingLock.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def acquire_processing_owner(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_id: uuid.UUID,
        conversation_id: uuid.UUID,
        channel: str,
        idempotency_key: str,
        owner_correlation_id: str,
        external_message_id: str | None = None,
    ) -> ProcessingLockAcquireResult:
        if not idempotency_key:
            raise ValueError("idempotency_key is required for processing lock")

        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.lease_seconds)
        owner = str(owner_correlation_id)

        existing = await self.get_by_scope(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            conversation_id=conversation_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return self._resolve_existing_lock(
                session,
                existing,
                owner_correlation_id=owner,
                now=now,
                expires_at=expires_at,
            )

        lock = InboundProcessingLock(
            tenant_id=tenant_id,
            business_id=business_id,
            flow_id=flow_id,
            conversation_id=conversation_id,
            channel=channel,
            idempotency_key=idempotency_key,
            external_message_id=external_message_id,
            status=LOCK_STATUS_PROCESSING,
            owner_correlation_id=owner,
            replay_count=0,
            first_seen_at=now,
            last_seen_at=now,
            expires_at=expires_at,
        )
        session.add(lock)

        try:
            async with session.begin_nested():
                await session.flush()
        except IntegrityError:
            existing = await self.get_by_scope(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                conversation_id=conversation_id,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            return self._resolve_existing_lock(
                session,
                existing,
                owner_correlation_id=owner,
                now=now,
                expires_at=expires_at,
            )

        return ProcessingLockAcquireResult(acquired=True, conflict=False, lock=lock)

    async def release(
        self,
        session: AsyncSession,
        lock: InboundProcessingLock,
        *,
        status: str,
    ) -> InboundProcessingLock:
        if status not in {LOCK_STATUS_COMPLETED, LOCK_STATUS_FAILED}:
            raise ValueError(f"Unsupported lock release status: {status}")
        lock.status = status
        lock.last_seen_at = datetime.utcnow()
        await session.flush()
        return lock

    async def record_replay_attempt(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        idempotency_key: str,
    ) -> None:
        lock = await self.get_by_scope(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            conversation_id=conversation_id,
            idempotency_key=idempotency_key,
        )
        if lock is None:
            return
        lock.replay_count = (lock.replay_count or 0) + 1
        lock.last_seen_at = datetime.utcnow()
        await session.flush()

    def _resolve_existing_lock(
        self,
        session: AsyncSession,
        lock: InboundProcessingLock,
        *,
        owner_correlation_id: str,
        now: datetime,
        expires_at: datetime,
    ) -> ProcessingLockAcquireResult:
        lock.replay_count = (lock.replay_count or 0) + 1
        lock.last_seen_at = now

        if lock.status == LOCK_STATUS_PROCESSING:
            if lock.expires_at < now:
                lock.owner_correlation_id = owner_correlation_id
                lock.expires_at = expires_at
                lock.status = LOCK_STATUS_PROCESSING
                return ProcessingLockAcquireResult(
                    acquired=True,
                    conflict=False,
                    lock=lock,
                )
            if lock.owner_correlation_id == owner_correlation_id:
                lock.expires_at = expires_at
                return ProcessingLockAcquireResult(
                    acquired=True,
                    conflict=False,
                    lock=lock,
                )
            return ProcessingLockAcquireResult(acquired=False, conflict=True, lock=lock)

        if lock.status == LOCK_STATUS_COMPLETED:
            return ProcessingLockAcquireResult(acquired=False, conflict=True, lock=lock)

        if lock.status == LOCK_STATUS_FAILED:
            lock.status = LOCK_STATUS_PROCESSING
            lock.owner_correlation_id = owner_correlation_id
            lock.expires_at = expires_at
            return ProcessingLockAcquireResult(acquired=True, conflict=False, lock=lock)

        return ProcessingLockAcquireResult(acquired=False, conflict=True, lock=lock)
