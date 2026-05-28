"""Map ReplayEvent ORM rows to API responses."""

from __future__ import annotations

from app.models.replay_event import ReplayEvent
from app.schemas.replay_event import ReplayEventResponse


def replay_event_to_response(event: ReplayEvent) -> ReplayEventResponse:
    return ReplayEventResponse(
        id=str(event.id),
        tenant_id=str(event.tenant_id),
        business_id=str(event.business_id),
        flow_id=str(event.flow_id) if event.flow_id else None,
        conversation_id=str(event.conversation_id) if event.conversation_id else None,
        trace_id=str(event.trace_id) if event.trace_id else None,
        delivery_id=str(event.delivery_id) if event.delivery_id else None,
        inbound_message_id=(
            str(event.inbound_message_id) if event.inbound_message_id else None
        ),
        outbound_message_id=(
            str(event.outbound_message_id) if event.outbound_message_id else None
        ),
        source=event.source,
        event_type=event.event_type,
        idempotency_key=event.idempotency_key,
        external_message_id=event.external_message_id,
        correlation_id=event.correlation_id,
        metadata=event.metadata_,
        created_at=event.created_at,
    )
