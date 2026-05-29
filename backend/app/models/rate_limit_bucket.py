import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

SCOPE_TENANT = "tenant"
SCOPE_BUSINESS = "business"
SCOPE_ADAPTER = "adapter"
SCOPE_CONVERSATION = "conversation"

RATE_LIMIT_SCOPES = frozenset(
    {
        SCOPE_TENANT,
        SCOPE_BUSINESS,
        SCOPE_ADAPTER,
        SCOPE_CONVERSATION,
    }
)


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    __table_args__ = (
        Index(
            "rate_limit_buckets_scope_window_unique",
            "tenant_id",
            "business_id",
            "scope_type",
            "scope_key",
            "window_start",
            unique=True,
        ),
        Index(
            "rate_limit_buckets_business_scope_window_idx",
            "business_id",
            "scope_type",
            "window_start",
        ),
        Index("rate_limit_buckets_tenant_id_idx", "tenant_id"),
        Index("rate_limit_buckets_business_id_idx", "business_id"),
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
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(50))
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
    )
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
