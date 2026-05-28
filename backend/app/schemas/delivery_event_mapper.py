"""Map DeliveryEvent ORM rows to public API schemas."""

from __future__ import annotations

from app.models.delivery_event import DeliveryEvent
from app.schemas.delivery_event import DeliveryEventResponse


def delivery_event_to_response(event: DeliveryEvent) -> DeliveryEventResponse:
    return DeliveryEventResponse(
        id=str(event.id),
        tenant_id=str(event.tenant_id),
        business_id=str(event.business_id),
        flow_id=str(event.flow_id),
        conversation_id=str(event.conversation_id),
        trace_id=str(event.trace_id) if event.trace_id is not None else None,
        outbound_message_id=str(event.outbound_message_id),
        channel=event.channel,
        status=event.status,  # type: ignore[arg-type]
        provider_message_id=event.provider_message_id,
        provider_status=event.provider_status,
        retry_count=event.retry_count or 0,
        error_type=event.error_type,
        error_message=event.error_message,
        created_at=event.created_at,
        updated_at=event.updated_at,
        delivered_at=event.delivered_at,
        failed_at=event.failed_at,
    )
