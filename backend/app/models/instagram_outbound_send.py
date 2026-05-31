"""Registry of Instagram outbound sends per inbound Meta message id (idempotency)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InstagramOutboundSend(Base):
    __tablename__ = "instagram_outbound_sends"
    __table_args__ = (
        UniqueConstraint(
            "business_external_id",
            "external_inbound_message_id",
            name="instagram_outbound_sends_business_inbound_unique",
        ),
        Index("instagram_outbound_sends_created_at_idx", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    business_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_inbound_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
