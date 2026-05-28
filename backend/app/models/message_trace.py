import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

TRACE_STATUS_ACCEPTED = "accepted"
TRACE_STATUS_PROCESSING = "processing"
TRACE_STATUS_COMPLETED = "completed"
TRACE_STATUS_SKIPPED_DUPLICATE = "skipped_duplicate"
TRACE_STATUS_FAILED = "failed"

TRACE_STATUSES = frozenset(
    {
        TRACE_STATUS_ACCEPTED,
        TRACE_STATUS_PROCESSING,
        TRACE_STATUS_COMPLETED,
        TRACE_STATUS_SKIPPED_DUPLICATE,
        TRACE_STATUS_FAILED,
    }
)


class MessageTrace(Base):
    __tablename__ = "message_traces"
    __table_args__ = (
        Index(
            "message_traces_inbound_message_id_unique",
            "inbound_message_id",
            unique=True,
        ),
        Index("message_traces_tenant_id_idx", "tenant_id"),
        Index("message_traces_business_id_idx", "business_id"),
        Index("message_traces_flow_id_idx", "flow_id"),
        Index("message_traces_conversation_id_idx", "conversation_id"),
        Index("message_traces_status_idx", "status"),
        Index("message_traces_flow_id_created_at_idx", "flow_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
    )
    flow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flows.id"),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
        nullable=False,
    )
    inbound_message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id"),
        nullable=False,
    )
    outbound_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id"),
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    external_trace_id: Mapped[str | None] = mapped_column(String(255))
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(255))
    flow_key: Mapped[str | None] = mapped_column(String(100))
    external_conversation_id: Mapped[str | None] = mapped_column(String(255))
    external_message_id: Mapped[str | None] = mapped_column(String(255))
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
