import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

FLOW_STATUS_ACTIVE = "active"
FLOW_STATUS_INACTIVE = "inactive"
FLOW_STATUS_ARCHIVED = "archived"


class Flow(Base):
    __tablename__ = "flows"
    __table_args__ = (
        UniqueConstraint("business_id", "flow_key", name="flows_business_flow_key_unique"),
        Index("flows_tenant_id_idx", "tenant_id"),
        Index("flows_business_id_idx", "business_id"),
        Index("flows_status_idx", "status"),
        Index(
            "flows_business_default_unique",
            "business_id",
            unique=True,
            postgresql_where=text("is_default = true"),
        ),
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
    flow_key: Mapped[str] = mapped_column(String(100), nullable=False)
    flow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=FLOW_STATUS_ACTIVE,
        server_default=FLOW_STATUS_ACTIVE,
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
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

    tenant: Mapped["Tenant"] = relationship(back_populates="flows")
    business: Mapped["Business"] = relationship(back_populates="flows")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="flow")
