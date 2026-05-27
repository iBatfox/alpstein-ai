import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_business_profile import TenantBusinessProfile


class TenantBusinessProfileService:
    async def get_for_business(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
    ) -> TenantBusinessProfile | None:
        result = await session.execute(
            select(TenantBusinessProfile)
            .where(
                TenantBusinessProfile.tenant_id == tenant_id,
                TenantBusinessProfile.business_id == business_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
