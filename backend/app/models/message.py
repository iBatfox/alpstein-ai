import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("messages_tenant_id_idx", "tenant_id"),
        Index("messages_business_id_idx", "business_id"),
        Index("messages_conversation_id_idx", "conversation_id"),
        Index("messages_created_at_idx", "created_at"),
        Index("messages_external_message_id_idx", "external_message_id"),
        Index(
            "messages_incoming_conversation_external_unique",
            "business_id",
            "conversation_id",
            "external_message_id",
            unique=True,
            postgresql_where=text(
                "external_message_id IS NOT NULL "
                "AND sender_type = 'customer' "
                "AND direction = 'incoming'"
            ),
        ),
        Index(
            "messages_incoming_conversation_idempotency_unique",
            "business_id",
            "conversation_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "idempotency_key IS NOT NULL "
                "AND sender_type = 'customer' "
                "AND direction = 'incoming'"
            ),
        ),
        Index(
            "messages_idempotency_key_idx",
            "idempotency_key",
            postgresql_where=text("idempotency_key IS NOT NULL"),
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
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
        nullable=False,
    )
    sender_type: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="text",
        server_default="text",
    )
    external_message_id: Mapped[str | None] = mapped_column(String(255))
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ai_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="messages")
    business: Mapped["Business"] = relationship(back_populates="messages")
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    prompt_runs: Mapped[list["PromptRun"]] = relationship(back_populates="message")
