import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TenantChannelSetting(Base):
    __tablename__ = "tenant_channel_settings"

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
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    response_style: Mapped[str | None] = mapped_column(String(100))
    max_response_length: Mapped[int | None] = mapped_column(Integer)
    allow_emojis: Mapped[bool | None] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    allow_links: Mapped[bool | None] = mapped_column(
        Boolean,
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

    tenant: Mapped["Tenant"] = relationship(back_populates="channel_settings")
    business: Mapped["Business"] = relationship(back_populates="channel_settings")
