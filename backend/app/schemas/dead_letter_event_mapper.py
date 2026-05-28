from app.models.dead_letter_event import DeadLetterEvent
from app.schemas.dead_letter_event import DeadLetterEventResponse


def dead_letter_event_to_response(event: DeadLetterEvent) -> DeadLetterEventResponse:
    return DeadLetterEventResponse(
        id=str(event.id),
        tenant_id=str(event.tenant_id),
        business_id=str(event.business_id),
        flow_id=str(event.flow_id) if event.flow_id else None,
        conversation_id=str(event.conversation_id) if event.conversation_id else None,
        trace_id=str(event.trace_id) if event.trace_id else None,
        delivery_id=str(event.delivery_id) if event.delivery_id else None,
        inbound_message_id=str(event.inbound_message_id) if event.inbound_message_id else None,
        outbound_message_id=(
            str(event.outbound_message_id) if event.outbound_message_id else None
        ),
        scope_type=event.scope_type,
        scope_id=str(event.scope_id),
        event_type=event.event_type,
        failure_reason=event.failure_reason,
        error_type=event.error_type,
        retry_count=event.retry_count,
        correlation_id=event.correlation_id,
        metadata=event.metadata_,
        resolved_at=event.resolved_at,
        created_at=event.created_at,
        last_seen_at=event.last_seen_at,
    )
