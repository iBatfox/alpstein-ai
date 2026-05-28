"""Read-only message trace API schemas (E2.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TraceStatus = Literal[
    "accepted",
    "processing",
    "completed",
    "skipped_duplicate",
    "failed",
]

FORBIDDEN_TRACE_RESPONSE_FIELDS = frozenset(
    {
        "final_prompt",
        "assembled_prompt",
        "system_prompt",
        "raw_payload",
        "ai_metadata",
        "operator_business_context",
        "openai",
        "api_key",
        "secret",
    }
)


class MessageTraceMetadataResponse(BaseModel):
    """Bounded trace metadata — no prompts or secrets."""

    model_config = ConfigDict(extra="forbid")

    correlation_id: str | None = None
    n8n_execution_id: str | None = None
    prompt_run_id: str | None = None


class MessageTraceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="message_trace_id")
    tenant_id: str
    business_id: str
    flow_id: str
    conversation_id: str
    inbound_message_id: str
    outbound_message_id: str | None = None
    channel: str
    status: TraceStatus
    flow_key: str | None = None
    external_conversation_id: str | None = None
    external_message_id: str | None = None
    idempotency_key: str | None = None
    correlation_id: str | None = None
    external_trace_id: str | None = None
    langfuse_trace_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    metadata: MessageTraceMetadataResponse | None = None
    created_at: datetime
    updated_at: datetime


class MessageTraceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MessageTraceResponse]
    limit: int
    offset: int


class MessageTraceSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: MessageTraceResponse


class MessageTraceListSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: MessageTraceListResponse
