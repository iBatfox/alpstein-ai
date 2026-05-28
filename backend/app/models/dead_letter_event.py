import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DL_SCOPE_DELIVERY = "delivery"
DL_SCOPE_INBOUND = "inbound"

DL_EVENT_DELIVERY_EXHAUSTED = "delivery_exhausted"
DL_EVENT_DELIVERY_TERMINAL_FAILURE = "delivery_terminal_failure"
DL_EVENT_INBOUND_EXHAUSTED = "inbound_exhausted"


class DeadLetterEvent(Base):
    __tablename__ = "dead_letter_events"
    __table_args__ = (
        Index(
            "dead_letter_events_active_scope_unique",
            "business_id",
            "scope_type",
            "scope_id",
            unique=True,
            postgresql_where=text("resolved_at IS NULL"),
        ),
        Index(
            "dead_letter_events_business_conversation_idx",
            "business_id",
            "conversation_id",
            "created_at",
        ),
        Index("dead_letter_events_delivery_id_idx", "delivery_id"),
        Index("dead_letter_events_trace_id_idx", "trace_id"),
        Index("dead_letter_events_tenant_id_idx", "tenant_id"),
        Index("dead_letter_events_business_id_idx", "business_id"),
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
    flow_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    trace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    delivery_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    inbound_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    outbound_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    error_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correlation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
