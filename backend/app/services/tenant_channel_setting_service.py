import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_channel_setting import TenantChannelSetting


class TenantChannelSettingService:
    async def get_for_channel(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
    ) -> TenantChannelSetting | None:
        result = await session.execute(
            select(TenantChannelSetting)
            .where(
                TenantChannelSetting.tenant_id == tenant_id,
                TenantChannelSetting.business_id == business_id,
                TenantChannelSetting.channel == channel,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
