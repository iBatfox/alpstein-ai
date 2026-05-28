"""Dead-letter persistence for exhausted retries (E3.2b)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dead_letter_event import (
    DL_EVENT_DELIVERY_EXHAUSTED,
    DL_EVENT_DELIVERY_TERMINAL_FAILURE,
    DL_EVENT_INBOUND_EXHAUSTED,
    DL_SCOPE_DELIVERY,
    DL_SCOPE_INBOUND,
    DeadLetterEvent,
)
from app.services.replay_event_service import sanitize_replay_metadata

LIST_DEFAULT_LIMIT = 20
LIST_MAX_LIMIT = 100
FAILURE_REASON_MAX_LENGTH = 500


class DeadLetterService:
    async def upsert_active(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        scope_type: str,
        scope_id: uuid.UUID,
        event_type: str,
        failure_reason: str,
        retry_count: int,
        flow_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        trace_id: uuid.UUID | None = None,
        delivery_id: uuid.UUID | None = None,
        inbound_message_id: uuid.UUID | None = None,
        outbound_message_id: uuid.UUID | None = None,
        error_type: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DeadLetterEvent:
        now = datetime.utcnow()
        existing = await self.get_active_by_scope(
            session,
            business_id=business_id,
            scope_type=scope_type,
            scope_id=scope_id,
        )
        if existing is not None:
            existing.event_type = event_type
            existing.failure_reason = _truncate(failure_reason, FAILURE_REASON_MAX_LENGTH)
            existing.error_type = error_type
            existing.retry_count = retry_count
            existing.last_seen_at = now
            if correlation_id is not None:
                existing.correlation_id = correlation_id
            if metadata:
                existing.metadata_ = sanitize_replay_metadata(metadata)
            await session.flush()
            return existing

        row = DeadLetterEvent(
            tenant_id=tenant_id,
            business_id=business_id,
            flow_id=flow_id,
            conversation_id=conversation_id,
            trace_id=trace_id,
            delivery_id=delivery_id,
            inbound_message_id=inbound_message_id,
            outbound_message_id=outbound_message_id,
            scope_type=scope_type,
            scope_id=scope_id,
            event_type=event_type,
            failure_reason=_truncate(failure_reason, FAILURE_REASON_MAX_LENGTH),
            error_type=error_type,
            retry_count=retry_count,
            correlation_id=correlation_id,
            metadata_=sanitize_replay_metadata(metadata),
            created_at=now,
            last_seen_at=now,
        )
        session.add(row)
        try:
            async with session.begin_nested():
                await session.flush()
        except IntegrityError:
            existing = await self.get_active_by_scope(
                session,
                business_id=business_id,
                scope_type=scope_type,
                scope_id=scope_id,
            )
            if existing is None:
                raise
            return await self.upsert_active(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                scope_type=scope_type,
                scope_id=scope_id,
                event_type=event_type,
                failure_reason=failure_reason,
                retry_count=retry_count,
                flow_id=flow_id,
                conversation_id=conversation_id,
                trace_id=trace_id,
                delivery_id=delivery_id,
                inbound_message_id=inbound_message_id,
                outbound_message_id=outbound_message_id,
                error_type=error_type,
                correlation_id=correlation_id,
                metadata=metadata,
            )
        return row

    async def record_delivery_exhausted(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        delivery_id: uuid.UUID,
        flow_id: uuid.UUID,
        conversation_id: uuid.UUID,
        trace_id: uuid.UUID | None,
        outbound_message_id: uuid.UUID,
        retry_count: int,
        error_type: str | None,
        failure_reason: str,
        terminal: bool = False,
    ) -> DeadLetterEvent:
        event_type = (
            DL_EVENT_DELIVERY_TERMINAL_FAILURE
            if terminal
            else DL_EVENT_DELIVERY_EXHAUSTED
        )
        return await self.upsert_active(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            scope_type=DL_SCOPE_DELIVERY,
            scope_id=delivery_id,
            event_type=event_type,
            failure_reason=failure_reason,
            retry_count=retry_count,
            flow_id=flow_id,
            conversation_id=conversation_id,
            trace_id=trace_id,
            delivery_id=delivery_id,
            outbound_message_id=outbound_message_id,
            error_type=error_type,
        )

    async def record_inbound_exhausted(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        lock_id: uuid.UUID,
        flow_id: uuid.UUID,
        conversation_id: uuid.UUID,
        inbound_message_id: uuid.UUID | None,
        trace_id: uuid.UUID | None,
        retry_count: int,
        correlation_id: str | None = None,
    ) -> DeadLetterEvent:
        return await self.upsert_active(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            scope_type=DL_SCOPE_INBOUND,
            scope_id=lock_id,
            event_type=DL_EVENT_INBOUND_EXHAUSTED,
            failure_reason="Inbound provider retries exhausted for idempotency scope",
            retry_count=retry_count,
            flow_id=flow_id,
            conversation_id=conversation_id,
            trace_id=trace_id,
            inbound_message_id=inbound_message_id,
            correlation_id=correlation_id,
        )

    async def get_active_by_scope(
        self,
        session: AsyncSession,
        *,
        business_id: uuid.UUID,
        scope_type: str,
        scope_id: uuid.UUID,
    ) -> DeadLetterEvent | None:
        result = await session.execute(
            select(DeadLetterEvent).where(
                DeadLetterEvent.business_id == business_id,
                DeadLetterEvent.scope_type == scope_type,
                DeadLetterEvent.scope_id == scope_id,
                DeadLetterEvent.resolved_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_events(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        trace_id: uuid.UUID | None = None,
        delivery_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        inbound_message_id: uuid.UUID | None = None,
        event_type: str | None = None,
        scope_type: str | None = None,
        limit: int = LIST_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> list[DeadLetterEvent]:
        bounded_limit = min(max(limit, 1), LIST_MAX_LIMIT)
        bounded_offset = max(offset, 0)
        conditions = [
            DeadLetterEvent.tenant_id == tenant_id,
            DeadLetterEvent.business_id == business_id,
        ]
        if trace_id is not None:
            conditions.append(DeadLetterEvent.trace_id == trace_id)
        if delivery_id is not None:
            conditions.append(DeadLetterEvent.delivery_id == delivery_id)
        if conversation_id is not None:
            conditions.append(DeadLetterEvent.conversation_id == conversation_id)
        if inbound_message_id is not None:
            conditions.append(DeadLetterEvent.inbound_message_id == inbound_message_id)
        if event_type is not None:
            conditions.append(DeadLetterEvent.event_type == event_type)
        if scope_type is not None:
            conditions.append(DeadLetterEvent.scope_type == scope_type)

        result = await session.execute(
            select(DeadLetterEvent)
            .where(*conditions)
            .order_by(desc(DeadLetterEvent.created_at))
            .limit(bounded_limit)
            .offset(bounded_offset)
        )
        return list(result.scalars().all())


def _truncate(value: str, max_length: int) -> str:
    normalized = value.strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3] + "..."
