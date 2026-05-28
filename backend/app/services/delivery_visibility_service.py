"""Outbound delivery lifecycle persistence (E2.6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery_event import (
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_FAILED,
    DELIVERY_STATUS_PENDING,
    DELIVERY_STATUS_RETRYING,
    DELIVERY_STATUS_SKIPPED,
    DeliveryEvent,
)
from app.models.replay_event import (
    REPLAY_EVENT_ILLEGAL_TRANSITION,
    REPLAY_SOURCE_DELIVERY_PATCH,
)
from app.services.delivery_state_machine import is_delivery_transition_allowed
from app.services.replay_event_service import ReplayEventService

ERROR_MESSAGE_MAX_LENGTH = 500
LIST_DEFAULT_LIMIT = 20
LIST_MAX_LIMIT = 100


class DeliveryVisibilityService:
    def __init__(self, replay_event_service: ReplayEventService | None = None) -> None:
        self.replay_event_service = replay_event_service or ReplayEventService()

    async def get_by_id(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        delivery_id: uuid.UUID,
    ) -> DeliveryEvent | None:
        result = await session.execute(
            select(DeliveryEvent).where(
                DeliveryEvent.id == delivery_id,
                DeliveryEvent.tenant_id == tenant_id,
                DeliveryEvent.business_id == business_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_outbound_message_id(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        outbound_message_id: uuid.UUID,
    ) -> DeliveryEvent | None:
        result = await session.execute(
            select(DeliveryEvent).where(
                DeliveryEvent.tenant_id == tenant_id,
                DeliveryEvent.business_id == business_id,
                DeliveryEvent.outbound_message_id == outbound_message_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_conversation(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        status: str | None = None,
        channel: str | None = None,
        limit: int = LIST_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> list[DeliveryEvent]:
        bounded_limit = min(max(limit, 1), LIST_MAX_LIMIT)
        bounded_offset = max(offset, 0)
        conditions = [
            DeliveryEvent.tenant_id == tenant_id,
            DeliveryEvent.business_id == business_id,
            DeliveryEvent.conversation_id == conversation_id,
        ]
        if status is not None:
            conditions.append(DeliveryEvent.status == status)
        if channel is not None:
            conditions.append(DeliveryEvent.channel == channel)

        result = await session.execute(
            select(DeliveryEvent)
            .where(*conditions)
            .order_by(desc(DeliveryEvent.created_at))
            .limit(bounded_limit)
            .offset(bounded_offset)
        )
        return list(result.scalars().all())

    async def create_pending_for_outbound(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_id: uuid.UUID,
        conversation_id: uuid.UUID,
        outbound_message_id: uuid.UUID,
        channel: str,
        trace_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DeliveryEvent:
        existing = await self.get_by_outbound_message_id(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            outbound_message_id=outbound_message_id,
        )
        if existing is not None:
            return existing

        event = DeliveryEvent(
            tenant_id=tenant_id,
            business_id=business_id,
            flow_id=flow_id,
            conversation_id=conversation_id,
            trace_id=trace_id,
            outbound_message_id=outbound_message_id,
            channel=channel,
            status=DELIVERY_STATUS_PENDING,
            metadata_=metadata,
        )
        session.add(event)

        try:
            async with session.begin_nested():
                await session.flush()
        except IntegrityError:
            existing = await self.get_by_outbound_message_id(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                outbound_message_id=outbound_message_id,
            )
            if existing is None:
                raise
            return existing

        return event

    async def mark_delivered(
        self,
        session: AsyncSession,
        event: DeliveryEvent,
        *,
        provider_message_id: str | None = None,
        provider_status: str | None = None,
        metadata: dict[str, Any] | None = None,
        delivered_at: datetime | None = None,
    ) -> DeliveryEvent:
        if event.status == DELIVERY_STATUS_DELIVERED:
            return event
        event.status = DELIVERY_STATUS_DELIVERED
        event.delivered_at = delivered_at or datetime.utcnow()
        event.failed_at = None
        event.error_type = None
        event.error_message = None
        if provider_message_id is not None:
            event.provider_message_id = provider_message_id
        if provider_status is not None:
            event.provider_status = provider_status
        if metadata:
            event.metadata_ = _merge_metadata(event.metadata_, metadata)
        await session.flush()
        return event

    async def mark_failed(
        self,
        session: AsyncSession,
        event: DeliveryEvent,
        *,
        error_type: str,
        error_message: str,
        provider_status: str | None = None,
        metadata: dict[str, Any] | None = None,
        failed_at: datetime | None = None,
    ) -> DeliveryEvent:
        event.status = DELIVERY_STATUS_FAILED
        event.failed_at = failed_at or datetime.utcnow()
        event.error_type = _truncate(error_type, 100)
        event.error_message = _truncate(error_message, ERROR_MESSAGE_MAX_LENGTH)
        if provider_status is not None:
            event.provider_status = provider_status
        if metadata:
            event.metadata_ = _merge_metadata(event.metadata_, metadata)
        await session.flush()
        return event

    async def mark_skipped(
        self,
        session: AsyncSession,
        event: DeliveryEvent,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> DeliveryEvent:
        if event.status == DELIVERY_STATUS_DELIVERED:
            return event
        event.status = DELIVERY_STATUS_SKIPPED
        if metadata:
            event.metadata_ = _merge_metadata(event.metadata_, metadata)
        await session.flush()
        return event

    async def increment_retry(
        self,
        session: AsyncSession,
        event: DeliveryEvent,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> DeliveryEvent:
        event.retry_count = (event.retry_count or 0) + 1
        event.status = DELIVERY_STATUS_RETRYING
        if metadata:
            event.metadata_ = _merge_metadata(event.metadata_, metadata)
        await session.flush()
        return event

    async def report_status(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        delivery_id: uuid.UUID,
        status: str,
        provider_message_id: str | None = None,
        provider_status: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DeliveryEvent | None:
        event = await self.get_by_id(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            delivery_id=delivery_id,
        )
        if event is None:
            return None

        if not is_delivery_transition_allowed(event.status, status):
            if event.status != status:
                await self.replay_event_service.record(
                    session,
                    tenant_id=tenant_id,
                    business_id=business_id,
                    source=REPLAY_SOURCE_DELIVERY_PATCH,
                    event_type=REPLAY_EVENT_ILLEGAL_TRANSITION,
                    flow_id=event.flow_id,
                    conversation_id=event.conversation_id,
                    trace_id=event.trace_id,
                    delivery_id=event.id,
                    outbound_message_id=event.outbound_message_id,
                    metadata={
                        "from_status": event.status,
                        "to_status": status,
                    },
                )
            return event

        if status == DELIVERY_STATUS_DELIVERED:
            return await self.mark_delivered(
                session,
                event,
                provider_message_id=provider_message_id,
                provider_status=provider_status,
                metadata=metadata,
            )
        if status == DELIVERY_STATUS_FAILED:
            return await self.mark_failed(
                session,
                event,
                error_type=error_type or "DELIVERY_FAILED",
                error_message=error_message or "Delivery failed",
                provider_status=provider_status,
                metadata=metadata,
            )
        if status == DELIVERY_STATUS_SKIPPED:
            return await self.mark_skipped(session, event, metadata=metadata)
        if status == DELIVERY_STATUS_RETRYING:
            return await self.increment_retry(session, event, metadata=metadata)

        raise ValueError(f"Unsupported delivery status: {status}")


def _merge_metadata(
    existing: dict[str, Any] | None,
    updates: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(existing or {})
    merged.update(updates)
    return merged


def _truncate(value: str, max_length: int) -> str:
    normalized = value.strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3] + "..."
