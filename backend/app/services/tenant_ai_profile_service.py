import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_ai_profile import TenantAiProfile


class TenantAiProfileService:
    async def get_for_business(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
    ) -> TenantAiProfile | None:
        result = await session.execute(
            select(TenantAiProfile)
            .where(
                TenantAiProfile.tenant_id == tenant_id,
                TenantAiProfile.business_id == business_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
