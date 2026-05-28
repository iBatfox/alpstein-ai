import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

REPLAY_SOURCE_WEBHOOK = "webhook"
REPLAY_SOURCE_DELIVERY_PATCH = "delivery_patch"

REPLAY_EVENT_DUPLICATE_RETRY = "duplicate_retry"
REPLAY_EVENT_REPLAY_DETECTED = "replay_detected"
REPLAY_EVENT_REPLAY_IGNORED = "replay_ignored"
REPLAY_EVENT_ILLEGAL_TRANSITION = "illegal_transition"
REPLAY_EVENT_RETRY_EXHAUSTED = "retry_exhausted"


class ReplayEvent(Base):
    __tablename__ = "replay_events"
    __table_args__ = (
        Index(
            "replay_events_business_conversation_created_idx",
            "business_id",
            "conversation_id",
            "created_at",
        ),
        Index(
            "replay_events_business_idempotency_created_idx",
            "business_id",
            "idempotency_key",
            "created_at",
        ),
        Index("replay_events_trace_id_idx", "trace_id"),
        Index("replay_events_delivery_id_idx", "delivery_id"),
        Index("replay_events_event_type_created_idx", "event_type", "created_at"),
        Index("replay_events_tenant_id_idx", "tenant_id"),
        Index("replay_events_business_id_idx", "business_id"),
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
    flow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    trace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
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
    source: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
