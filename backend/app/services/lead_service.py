"""Lead persistence for MVP lead creation flow (T12.2)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import TenantContextError
from app.models.lead import (
    LEAD_PRIORITY_NORMAL,
    LEAD_STATUS_CONTACTED,
    LEAD_STATUS_IN_PROGRESS,
    LEAD_STATUS_NEW,
    Lead,
)

ACTIVE_LEAD_STATUSES = (
    LEAD_STATUS_NEW,
    LEAD_STATUS_IN_PROGRESS,
    LEAD_STATUS_CONTACTED,
)

_UNSET: Any = object()


class LeadService:
    async def find_active_lead(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        customer_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Lead | None:
        result = await session.execute(
            select(Lead)
            .where(
                Lead.tenant_id == tenant_id,
                Lead.business_id == business_id,
                Lead.customer_id == customer_id,
                Lead.conversation_id == conversation_id,
                Lead.status.in_(ACTIVE_LEAD_STATUSES),
            )
            .order_by(desc(Lead.updated_at), desc(Lead.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_lead(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        customer_id: uuid.UUID,
        conversation_id: uuid.UUID,
        source_channel: str,
        service_requested: str | None = None,
        preferred_date: date | None = None,
        preferred_time: time | None = None,
        customer_note: str | None = None,
        ai_summary: str | None = None,
    ) -> Lead:
        lead = Lead(
            tenant_id=tenant_id,
            business_id=business_id,
            customer_id=customer_id,
            conversation_id=conversation_id,
            source_channel=source_channel,
            status=LEAD_STATUS_NEW,
            priority=LEAD_PRIORITY_NORMAL,
            service_requested=service_requested,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            customer_note=customer_note,
            ai_summary=ai_summary,
        )
        session.add(lead)
        await session.flush()
        return lead

    async def update_lead(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        lead: Lead,
        ai_summary: str | None = _UNSET,
        customer_note: str | None = _UNSET,
        service_requested: str | None = _UNSET,
        preferred_date: date | None = _UNSET,
        preferred_time: time | None = _UNSET,
        priority: str | None = _UNSET,
        status: str | None = _UNSET,
    ) -> Lead:
        if lead.tenant_id != tenant_id:
            raise TenantContextError("lead does not belong to tenant")
        if lead.business_id != business_id:
            raise TenantContextError("lead does not belong to business")

        if ai_summary is not _UNSET:
            lead.ai_summary = ai_summary
        if customer_note is not _UNSET:
            lead.customer_note = customer_note
        if service_requested is not _UNSET:
            lead.service_requested = service_requested
        if preferred_date is not _UNSET:
            lead.preferred_date = preferred_date
        if preferred_time is not _UNSET:
            lead.preferred_time = preferred_time
        if priority is not _UNSET:
            lead.priority = priority
        if status is not _UNSET:
            lead.status = status

        lead.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await session.flush()
        return lead
