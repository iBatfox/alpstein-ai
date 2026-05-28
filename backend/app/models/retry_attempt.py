import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

RETRY_SCOPE_DELIVERY = "delivery"
RETRY_SCOPE_INBOUND = "inbound"

RETRY_STATUS_RETRYING = "retrying"
RETRY_STATUS_FAILED = "failed"
RETRY_STATUS_EXHAUSTED = "exhausted"


class RetryAttempt(Base):
    __tablename__ = "retry_attempts"
    __table_args__ = (
        Index(
            "retry_attempts_scope_idx",
            "business_id",
            "scope_type",
            "scope_id",
            "created_at",
        ),
        Index(
            "retry_attempts_conversation_idx",
            "business_id",
            "conversation_id",
            "created_at",
        ),
        Index("retry_attempts_trace_id_idx", "trace_id"),
        Index("retry_attempts_tenant_id_idx", "tenant_id"),
        Index("retry_attempts_business_id_idx", "business_id"),
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
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    trace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
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
