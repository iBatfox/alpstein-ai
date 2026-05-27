import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, Time, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

LEAD_STATUS_NEW = "new"
LEAD_STATUS_IN_PROGRESS = "in_progress"
LEAD_STATUS_CONTACTED = "contacted"
LEAD_STATUS_CLOSED = "closed"
LEAD_STATUS_LOST = "lost"

LEAD_PRIORITY_LOW = "low"
LEAD_PRIORITY_NORMAL = "normal"
LEAD_PRIORITY_HIGH = "high"
LEAD_PRIORITY_URGENT = "urgent"


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("leads_tenant_id_idx", "tenant_id"),
        Index("leads_business_id_idx", "business_id"),
        Index("leads_customer_id_idx", "customer_id"),
        Index("leads_status_idx", "status"),
        Index("leads_created_at_idx", "created_at"),
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
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
        nullable=False,
    )
    service_requested: Mapped[str | None] = mapped_column(String(255))
    preferred_date: Mapped[date | None] = mapped_column(Date)
    preferred_time: Mapped[time | None] = mapped_column(Time)
    customer_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=LEAD_STATUS_NEW,
        server_default=LEAD_STATUS_NEW,
    )
    priority: Mapped[str | None] = mapped_column(
        String(50),
        default=LEAD_PRIORITY_NORMAL,
        server_default=LEAD_PRIORITY_NORMAL,
    )
    source_channel: Mapped[str | None] = mapped_column(String(50))
    ai_summary: Mapped[str | None] = mapped_column(Text)
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

    tenant: Mapped["Tenant"] = relationship(back_populates="leads")
    business: Mapped["Business"] = relationship(back_populates="leads")
    customer: Mapped["Customer"] = relationship(back_populates="leads")
    conversation: Mapped["Conversation"] = relationship(back_populates="leads")
