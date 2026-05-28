"""Operational retry attempt logging and limits (E3.2a)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retry_attempt import (
    RETRY_SCOPE_DELIVERY,
    RETRY_SCOPE_INBOUND,
    RETRY_STATUS_EXHAUSTED,
    RETRY_STATUS_FAILED,
    RETRY_STATUS_RETRYING,
    RetryAttempt,
)
from app.services.replay_event_service import sanitize_replay_metadata
from app.services.retry_policy import (
    delivery_max_retries,
    inbound_provider_retry_max,
)

LIST_DEFAULT_LIMIT = 20
LIST_MAX_LIMIT = 100
ERROR_MESSAGE_MAX_LENGTH = 500


class RetryLifecycleService:
    async def next_delivery_attempt_number(
        self,
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        delivery_id: uuid.UUID,
    ) -> int:
        result = await session.execute(
            select(func.max(RetryAttempt.attempt_number)).where(
                RetryAttempt.business_id == business_id,
                RetryAttempt.scope_type == RETRY_SCOPE_DELIVERY,
                RetryAttempt.scope_id == delivery_id,
            )
        )
        current = result.scalar_one_or_none()
        return (current or 0) + 1

    async def record_delivery_attempt(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        delivery_id: uuid.UUID,
        status: str,
        attempt_number: int | None = None,
        trace_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RetryAttempt:
        resolved_attempt = attempt_number
        if resolved_attempt is None:
            resolved_attempt = await self.next_delivery_attempt_number(
                session,
                business_id=business_id,
                delivery_id=delivery_id,
            )
        attempt = RetryAttempt(
            tenant_id=tenant_id,
            business_id=business_id,
            scope_type=RETRY_SCOPE_DELIVERY,
            scope_id=delivery_id,
            trace_id=trace_id,
            conversation_id=conversation_id,
            attempt_number=resolved_attempt,
            status=status,
            error_type=error_type,
            error_message=_truncate(error_message, ERROR_MESSAGE_MAX_LENGTH),
            correlation_id=correlation_id,
            metadata_=sanitize_replay_metadata(metadata),
            created_at=datetime.utcnow(),
        )
        session.add(attempt)
        await session.flush()
        return attempt

    async def record_inbound_attempt(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        lock_id: uuid.UUID,
        attempt_number: int,
        status: str,
        trace_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RetryAttempt:
        attempt = RetryAttempt(
            tenant_id=tenant_id,
            business_id=business_id,
            scope_type=RETRY_SCOPE_INBOUND,
            scope_id=lock_id,
            trace_id=trace_id,
            conversation_id=conversation_id,
            attempt_number=attempt_number,
            status=status,
            correlation_id=correlation_id,
            metadata_=sanitize_replay_metadata(metadata),
            created_at=datetime.utcnow(),
        )
        session.add(attempt)
        await session.flush()
        return attempt

    async def list_attempts(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        trace_id: uuid.UUID | None = None,
        delivery_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        scope_type: str | None = None,
        status: str | None = None,
        limit: int = LIST_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> list[RetryAttempt]:
        bounded_limit = min(max(limit, 1), LIST_MAX_LIMIT)
        bounded_offset = max(offset, 0)
        conditions = [
            RetryAttempt.tenant_id == tenant_id,
            RetryAttempt.business_id == business_id,
        ]
        if trace_id is not None:
            conditions.append(RetryAttempt.trace_id == trace_id)
        if delivery_id is not None:
            conditions.append(RetryAttempt.scope_type == RETRY_SCOPE_DELIVERY)
            conditions.append(RetryAttempt.scope_id == delivery_id)
        if conversation_id is not None:
            conditions.append(RetryAttempt.conversation_id == conversation_id)
        if scope_type is not None:
            conditions.append(RetryAttempt.scope_type == scope_type)
        if status is not None:
            conditions.append(RetryAttempt.status == status)

        result = await session.execute(
            select(RetryAttempt)
            .where(*conditions)
            .order_by(desc(RetryAttempt.created_at))
            .limit(bounded_limit)
            .offset(bounded_offset)
        )
        return list(result.scalars().all())

    def delivery_max_retries(self) -> int:
        return delivery_max_retries()

    def inbound_provider_retry_max(self) -> int:
        return inbound_provider_retry_max()


def _truncate(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3] + "..."
