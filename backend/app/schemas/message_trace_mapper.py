"""Map MessageTrace ORM rows to public API schemas."""

from __future__ import annotations

import uuid
from typing import Any

from app.models.message_trace import MessageTrace
from app.schemas.message_trace import (
    MessageTraceMetadataResponse,
    MessageTraceResponse,
)


def message_trace_to_response(trace: MessageTrace) -> MessageTraceResponse:
    metadata = trace.metadata_ or {}
    correlation_id = _metadata_str(metadata, "correlation_id") or trace.external_trace_id
    return MessageTraceResponse(
        id=str(trace.id),
        tenant_id=str(trace.tenant_id),
        business_id=str(trace.business_id),
        flow_id=str(trace.flow_id),
        conversation_id=str(trace.conversation_id),
        inbound_message_id=str(trace.inbound_message_id),
        outbound_message_id=(
            str(trace.outbound_message_id) if trace.outbound_message_id else None
        ),
        channel=trace.channel,
        status=trace.status,  # type: ignore[arg-type]
        flow_key=trace.flow_key,
        external_conversation_id=trace.external_conversation_id,
        external_message_id=trace.external_message_id,
        idempotency_key=trace.idempotency_key,
        correlation_id=correlation_id,
        external_trace_id=trace.external_trace_id,
        langfuse_trace_id=trace.langfuse_trace_id,
        error_type=trace.error_type,
        error_message=trace.error_message,
        metadata=_map_metadata(metadata),
        created_at=trace.created_at,
        updated_at=trace.updated_at,
    )


def _map_metadata(metadata: dict[str, Any]) -> MessageTraceMetadataResponse | None:
    correlation_id = _metadata_str(metadata, "correlation_id")
    n8n_execution_id = _metadata_str(metadata, "n8n_execution_id")
    prompt_run_id = _metadata_str(metadata, "prompt_run_id")
    if not any((correlation_id, n8n_execution_id, prompt_run_id)):
        return None
    return MessageTraceMetadataResponse(
        correlation_id=correlation_id,
        n8n_execution_id=n8n_execution_id,
        prompt_run_id=prompt_run_id,
    )


def _metadata_str(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None
