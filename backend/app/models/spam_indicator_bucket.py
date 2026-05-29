import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

SCOPE_CONVERSATION = "conversation"
SCOPE_ADAPTER = "adapter"
SCOPE_BUSINESS = "business"


class SpamIndicatorBucket(Base):
    __tablename__ = "spam_indicator_buckets"
    __table_args__ = (
        Index(
            "spam_indicator_buckets_unique",
            "tenant_id",
            "business_id",
            "rule_id",
            "scope_type",
            "scope_key",
            "window_start",
            unique=True,
        ),
        Index(
            "spam_indicator_buckets_business_rule_window_idx",
            "business_id",
            "rule_id",
            "window_start",
        ),
        Index("spam_indicator_buckets_tenant_id_idx", "tenant_id"),
        Index("spam_indicator_buckets_business_id_idx", "business_id"),
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
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(50))
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
    )
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
