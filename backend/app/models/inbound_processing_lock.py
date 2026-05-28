import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

LOCK_STATUS_PROCESSING = "processing"
LOCK_STATUS_COMPLETED = "completed"
LOCK_STATUS_FAILED = "failed"

LOCK_STATUSES = frozenset(
    {
        LOCK_STATUS_PROCESSING,
        LOCK_STATUS_COMPLETED,
        LOCK_STATUS_FAILED,
    }
)


class InboundProcessingLock(Base):
    __tablename__ = "inbound_processing_locks"
    __table_args__ = (
        Index(
            "inbound_processing_locks_scope_unique",
            "business_id",
            "conversation_id",
            "idempotency_key",
            unique=True,
        ),
        Index("inbound_processing_locks_tenant_id_idx", "tenant_id"),
        Index("inbound_processing_locks_business_id_idx", "business_id"),
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
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    external_message_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_correlation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    replay_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
