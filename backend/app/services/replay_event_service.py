"""Persist retry/replay observability events (E3.1c)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.replay_event import ReplayEvent

LIST_DEFAULT_LIMIT = 20
LIST_MAX_LIMIT = 100

FORBIDDEN_REPLAY_METADATA_KEYS = frozenset(
    {
        "raw_payload",
        "provider_payload",
        "api_key",
        "secret",
        "bot_token",
        "password",
    }
)


class ReplayEventService:
    async def record(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        source: str,
        event_type: str,
        flow_id: uuid.UUID | None = None,
        conversation_id: uuid.UUID | None = None,
        trace_id: uuid.UUID | None = None,
        delivery_id: uuid.UUID | None = None,
        inbound_message_id: uuid.UUID | None = None,
        outbound_message_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
        external_message_id: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ReplayEvent:
        event = ReplayEvent(
            tenant_id=tenant_id,
            business_id=business_id,
            flow_id=flow_id,
            conversation_id=conversation_id,
            trace_id=trace_id,
            delivery_id=delivery_id,
            inbound_message_id=inbound_message_id,
            outbound_message_id=outbound_message_id,
            source=source,
            event_type=event_type,
            idempotency_key=idempotency_key,
            external_message_id=external_message_id,
            correlation_id=correlation_id,
            metadata_=sanitize_replay_metadata(metadata),
            created_at=datetime.utcnow(),
        )
        session.add(event)
        await session.flush()
        return event

    async def get_by_id(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        replay_id: uuid.UUID,
    ) -> ReplayEvent | None:
        result = await session.execute(
            select(ReplayEvent).where(
                ReplayEvent.id == replay_id,
                ReplayEvent.tenant_id == tenant_id,
                ReplayEvent.business_id == business_id,
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
        idempotency_key: str | None = None,
        event_type: str | None = None,
        limit: int = LIST_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> list[ReplayEvent]:
        bounded_limit = min(max(limit, 1), LIST_MAX_LIMIT)
        bounded_offset = max(offset, 0)
        conditions = [
            ReplayEvent.tenant_id == tenant_id,
            ReplayEvent.business_id == business_id,
        ]
        if trace_id is not None:
            conditions.append(ReplayEvent.trace_id == trace_id)
        if delivery_id is not None:
            conditions.append(ReplayEvent.delivery_id == delivery_id)
        if conversation_id is not None:
            conditions.append(ReplayEvent.conversation_id == conversation_id)
        if idempotency_key is not None:
            conditions.append(ReplayEvent.idempotency_key == idempotency_key)
        if event_type is not None:
            conditions.append(ReplayEvent.event_type == event_type)

        result = await session.execute(
            select(ReplayEvent)
            .where(*conditions)
            .order_by(desc(ReplayEvent.created_at))
            .limit(bounded_limit)
            .offset(bounded_offset)
        )
        return list(result.scalars().all())


def sanitize_replay_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    return {
        key: value
        for key, value in metadata.items()
        if key not in FORBIDDEN_REPLAY_METADATA_KEYS
    }
