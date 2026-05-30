"""Resolve tenant/business for an Instagram source account (IG user id)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.tenant_channel_setting import TenantChannelSetting

INSTAGRAM_CHANNEL = "instagram"
INSTAGRAM_SOURCE_ACCOUNT_METADATA_KEY = "source_account_id"


@dataclass(frozen=True)
class ResolvedInstagramAccount:
    tenant_id: uuid.UUID
    business_id: uuid.UUID
    business_external_id: str
    source_account_id: str


class InstagramAccountResolverService:
    async def resolve_by_source_account_id(
        self,
        session: AsyncSession,
        source_account_id: str,
    ) -> ResolvedInstagramAccount | None:
        normalized_account_id = source_account_id.strip()
        if not normalized_account_id:
            return None

        result = await session.execute(
            select(Business, TenantChannelSetting)
            .join(
                TenantChannelSetting,
                TenantChannelSetting.business_id == Business.id,
            )
            .where(
                TenantChannelSetting.tenant_id == Business.tenant_id,
                TenantChannelSetting.channel == INSTAGRAM_CHANNEL,
                TenantChannelSetting.metadata_[
                    INSTAGRAM_SOURCE_ACCOUNT_METADATA_KEY
                ].astext
                == normalized_account_id,
            )
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None

        business, _setting = row
        return ResolvedInstagramAccount(
            tenant_id=business.tenant_id,
            business_id=business.id,
            business_external_id=business.external_id,
            source_account_id=normalized_account_id,
        )
