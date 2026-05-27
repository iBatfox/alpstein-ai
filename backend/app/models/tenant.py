import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        Index("tenants_slug_idx", "slug"),
        Index("tenants_status_idx", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
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

    businesses: Mapped[list["Business"]] = relationship(back_populates="tenant")
    customers: Mapped[list["Customer"]] = relationship(back_populates="tenant")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="tenant")
    messages: Mapped[list["Message"]] = relationship(back_populates="tenant")
    business_profiles: Mapped[list["TenantBusinessProfile"]] = relationship(
        back_populates="tenant"
    )
    ai_profiles: Mapped[list["TenantAiProfile"]] = relationship(back_populates="tenant")
    knowledge_sources: Mapped[list["TenantKnowledgeSource"]] = relationship(
        back_populates="tenant"
    )
    channel_settings: Mapped[list["TenantChannelSetting"]] = relationship(
        back_populates="tenant"
    )
    prompt_runs: Mapped[list["PromptRun"]] = relationship(back_populates="tenant")
    leads: Mapped[list["Lead"]] = relationship(back_populates="tenant")
