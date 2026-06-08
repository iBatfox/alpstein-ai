import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    BigInteger,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

BUSINESS_CONTEXT_BUILDER_SCHEMA = "business_context_builder"

SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_COMPLETED = "completed"
SESSION_STATUS_CANCELLED = "cancelled"

MESSAGE_ROLE_ASSISTANT = "assistant"
MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_SYSTEM = "system"

MINI_APP_ALLOWED_USER_STATUS_ACTIVE = "active"
MINI_APP_ALLOWED_USER_STATUS_DISABLED = "disabled"


class BusinessContextBuilderSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="business_context_builder_sessions_status_check",
        ),
        Index(
            "bcb_sessions_tenant_id_idx",
            "tenant_id",
        ),
        Index(
            "bcb_sessions_business_id_idx",
            "business_id",
        ),
        Index(
            "bcb_sessions_tenant_business_idx",
            "tenant_id",
            "business_id",
        ),
        Index(
            "bcb_sessions_tenant_business_status_idx",
            "tenant_id",
            "business_id",
            "status",
        ),
        {"schema": BUSINESS_CONTEXT_BUILDER_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    telegram_user_id: Mapped[str | None] = mapped_column(Text)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SESSION_STATUS_ACTIVE,
        server_default=SESSION_STATUS_ACTIVE,
    )
    current_step: Mapped[str | None] = mapped_column(String(100))
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
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))

    messages: Mapped[list["BusinessContextBuilderMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    result: Mapped["BusinessContextBuilderResult | None"] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )


class BusinessContextBuilderMiniAppAllowedUser(Base):
    __tablename__ = "mini_app_allowed_users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="business_context_builder_mini_app_allowed_users_status_check",
        ),
        UniqueConstraint(
            "telegram_user_id",
            name="bcb_mini_app_allowed_users_telegram_user_id_unique",
        ),
        Index(
            "bcb_mini_app_allowed_users_telegram_user_id_idx",
            "telegram_user_id",
        ),
        Index(
            "bcb_mini_app_allowed_users_status_idx",
            "status",
        ),
        Index(
            "bcb_mini_app_allowed_users_business_id_idx",
            "alpstein_business_id",
        ),
        {"schema": BUSINESS_CONTEXT_BUILDER_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    alpstein_business_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MINI_APP_ALLOWED_USER_STATUS_ACTIVE,
        server_default=MINI_APP_ALLOWED_USER_STATUS_ACTIVE,
    )
    notes: Mapped[str | None] = mapped_column(Text)
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


class BusinessContextBuilderBusinessIntegration(Base):
    __tablename__ = "business_integrations"
    __table_args__ = (
        Index(
            "bcb_business_integrations_business_id_idx",
            "alpstein_business_id",
        ),
        Index(
            "bcb_business_integrations_business_status_idx",
            "alpstein_business_id",
            "status",
        ),
        Index(
            "bcb_business_integrations_channel_type_idx",
            "channel_type",
        ),
        {"schema": BUSINESS_CONTEXT_BUILDER_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    alpstein_business_id: Mapped[str] = mapped_column(Text, nullable=False)
    channel_type: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    external_channel_id: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(Text)
    workflow_name: Mapped[str | None] = mapped_column(Text)
    workflow_id: Mapped[str | None] = mapped_column(Text)
    backend_route: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
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


class BusinessContextBuilderMessage(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('assistant', 'user', 'system')",
            name="business_context_builder_messages_role_check",
        ),
        Index(
            "bcb_messages_tenant_id_idx",
            "tenant_id",
        ),
        Index(
            "bcb_messages_business_id_idx",
            "business_id",
        ),
        Index(
            "bcb_messages_tenant_business_session_idx",
            "tenant_id",
            "business_id",
            "session_id",
        ),
        Index(
            "bcb_messages_session_created_at_idx",
            "session_id",
            "created_at",
        ),
        {"schema": BUSINESS_CONTEXT_BUILDER_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{BUSINESS_CONTEXT_BUILDER_SCHEMA}.sessions.id"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped[BusinessContextBuilderSession] = relationship(
        back_populates="messages",
    )


class BusinessContextBuilderResult(Base):
    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            name="business_context_builder_results_session_id_unique",
        ),
        Index(
            "bcb_results_tenant_id_idx",
            "tenant_id",
        ),
        Index(
            "bcb_results_business_id_idx",
            "business_id",
        ),
        Index(
            "bcb_results_tenant_business_idx",
            "tenant_id",
            "business_id",
        ),
        Index(
            "bcb_results_tenant_business_created_at_idx",
            "tenant_id",
            "business_id",
            "created_at",
        ),
        {"schema": BUSINESS_CONTEXT_BUILDER_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{BUSINESS_CONTEXT_BUILDER_SCHEMA}.sessions.id"),
        nullable=False,
    )
    structured_context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    generated_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    context_file_path: Mapped[str | None] = mapped_column(Text)
    context_file_url: Mapped[str | None] = mapped_column(Text)
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

    session: Mapped[BusinessContextBuilderSession] = relationship(
        back_populates="result",
    )
