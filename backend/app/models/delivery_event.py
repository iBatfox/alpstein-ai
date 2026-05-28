import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DELIVERY_STATUS_PENDING = "pending"
DELIVERY_STATUS_DELIVERED = "delivered"
DELIVERY_STATUS_FAILED = "failed"
DELIVERY_STATUS_SKIPPED = "skipped"
DELIVERY_STATUS_RETRYING = "retrying"

DELIVERY_STATUSES = frozenset(
    {
        DELIVERY_STATUS_PENDING,
        DELIVERY_STATUS_DELIVERED,
        DELIVERY_STATUS_FAILED,
        DELIVERY_STATUS_SKIPPED,
        DELIVERY_STATUS_RETRYING,
    }
)


class DeliveryEvent(Base):
    __tablename__ = "delivery_events"
    __table_args__ = (
        Index(
            "delivery_events_outbound_message_id_unique",
            "outbound_message_id",
            unique=True,
        ),
        Index("delivery_events_trace_id_idx", "trace_id"),
        Index("delivery_events_tenant_id_idx", "tenant_id"),
        Index("delivery_events_business_id_idx", "business_id"),
        Index("delivery_events_conversation_id_idx", "conversation_id"),
        Index(
            "delivery_events_business_channel_status_idx",
            "business_id",
            "channel",
            "status",
        ),
        Index("delivery_events_created_at_idx", "created_at"),
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
    trace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message_traces.id"),
    )
    outbound_message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    provider_status: Mapped[str | None] = mapped_column(String(100))
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
