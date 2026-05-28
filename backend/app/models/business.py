import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Business(Base):
    __tablename__ = "businesses"
    __table_args__ = (
        Index("businesses_tenant_id_idx", "tenant_id"),
        Index("businesses_external_id_idx", "external_id"),
        Index("businesses_status_idx", "status"),
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
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_type: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    working_hours: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    language: Mapped[str | None] = mapped_column(
        String(20),
        default="de",
        server_default="de",
    )
    timezone: Mapped[str | None] = mapped_column(
        String(100),
        default="Europe/Zurich",
        server_default="Europe/Zurich",
    )
    ai_prompt: Mapped[str | None] = mapped_column(Text)
    ai_tone: Mapped[str | None] = mapped_column(String(100))
    ai_language: Mapped[str | None] = mapped_column(String(20))
    storage_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="shared",
        server_default="shared",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        server_default="active",
    )
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

    tenant: Mapped["Tenant"] = relationship(back_populates="businesses")
    customers: Mapped[list["Customer"]] = relationship(back_populates="business")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="business")
    messages: Mapped[list["Message"]] = relationship(back_populates="business")
    business_profiles: Mapped[list["TenantBusinessProfile"]] = relationship(
        back_populates="business"
    )
    ai_profiles: Mapped[list["TenantAiProfile"]] = relationship(back_populates="business")
    knowledge_sources: Mapped[list["TenantKnowledgeSource"]] = relationship(
        back_populates="business"
    )
    channel_settings: Mapped[list["TenantChannelSetting"]] = relationship(
        back_populates="business"
    )
    prompt_runs: Mapped[list["PromptRun"]] = relationship(back_populates="business")
    leads: Mapped[list["Lead"]] = relationship(back_populates="business")
    flows: Mapped[list["Flow"]] = relationship(back_populates="business")
