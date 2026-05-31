"""Idempotency for Instagram outbound sends keyed by inbound external message id."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instagram_outbound_send import InstagramOutboundSend

logger = logging.getLogger(__name__)

LOG_ALREADY_SENT = "instagram_outbound_dedup_already_sent"


class InstagramOutboundDedupService:
    async def is_already_sent(
        self,
        session: AsyncSession,
        *,
        business_external_id: str,
        external_inbound_message_id: str,
    ) -> bool:
        business_id = business_external_id.strip()
        inbound_id = external_inbound_message_id.strip()
        if not business_id or not inbound_id:
            return False

        result = await session.execute(
            select(InstagramOutboundSend.id)
            .where(
                InstagramOutboundSend.business_external_id == business_id,
                InstagramOutboundSend.external_inbound_message_id == inbound_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def try_acquire_send_slot(
        self,
        session: AsyncSession,
        *,
        business_external_id: str,
        external_inbound_message_id: str,
    ) -> bool:
        """Reserve outbound slot before Meta call. Returns False if already sent."""
        business_id = business_external_id.strip()
        inbound_id = external_inbound_message_id.strip()
        if not business_id or not inbound_id:
            return False

        if await self.is_already_sent(
            session,
            business_external_id=business_id,
            external_inbound_message_id=inbound_id,
        ):
            logger.info(
                LOG_ALREADY_SENT,
                extra={
                    "business_id": business_id,
                    "external_inbound_message_id": inbound_id,
                },
            )
            return False

        stmt = (
            insert(InstagramOutboundSend)
            .values(
                id=uuid.uuid4(),
                business_external_id=business_id,
                external_inbound_message_id=inbound_id,
                provider_message_id=None,
            )
            .on_conflict_do_nothing(
                constraint="instagram_outbound_sends_business_inbound_unique",
            )
            .returning(InstagramOutboundSend.id)
        )
        result = await session.execute(stmt)
        acquired = result.scalar_one_or_none() is not None
        if not acquired:
            logger.info(
                LOG_ALREADY_SENT,
                extra={
                    "business_id": business_id,
                    "external_inbound_message_id": inbound_id,
                },
            )
        return acquired

    async def record_provider_message_id(
        self,
        session: AsyncSession,
        *,
        business_external_id: str,
        external_inbound_message_id: str,
        provider_message_id: str,
    ) -> None:
        business_id = business_external_id.strip()
        inbound_id = external_inbound_message_id.strip()
        provider_id = provider_message_id.strip()
        if not business_id or not inbound_id or not provider_id:
            return

        result = await session.execute(
            select(InstagramOutboundSend)
            .where(
                InstagramOutboundSend.business_external_id == business_id,
                InstagramOutboundSend.external_inbound_message_id == inbound_id,
            )
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        row.provider_message_id = provider_id
        await session.flush()

    async def release_send_slot(
        self,
        session: AsyncSession,
        *,
        business_external_id: str,
        external_inbound_message_id: str,
    ) -> None:
        """Remove reservation when Meta send fails so a later retry may proceed."""
        business_id = business_external_id.strip()
        inbound_id = external_inbound_message_id.strip()
        if not business_id or not inbound_id:
            return

        result = await session.execute(
            select(InstagramOutboundSend)
            .where(
                InstagramOutboundSend.business_external_id == business_id,
                InstagramOutboundSend.external_inbound_message_id == inbound_id,
                InstagramOutboundSend.provider_message_id.is_(None),
            )
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await session.delete(row)
            await session.flush()
