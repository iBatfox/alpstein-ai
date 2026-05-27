import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TenantAiProfile(Base):
    __tablename__ = "tenant_ai_profiles"

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
    profile_name: Mapped[str | None] = mapped_column(String(255))
    tone: Mapped[str | None] = mapped_column(String(100))
    response_style: Mapped[str | None] = mapped_column(String(100))
    language: Mapped[str | None] = mapped_column(String(20))
    ask_for_name: Mapped[bool | None] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )
    ask_for_phone: Mapped[bool | None] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )
    ask_for_email: Mapped[bool | None] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    handoff_enabled: Mapped[bool | None] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )
    handoff_keywords: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    forbidden_promises: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    fallback_response: Mapped[str | None] = mapped_column(Text)
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

    tenant: Mapped["Tenant"] = relationship(back_populates="ai_profiles")
    business: Mapped["Business"] = relationship(back_populates="ai_profiles")
