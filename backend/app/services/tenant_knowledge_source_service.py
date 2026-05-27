import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_knowledge_source import TenantKnowledgeSource


class TenantKnowledgeSourceService:
    async def list_active_for_business(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
    ) -> list[TenantKnowledgeSource]:
        result = await session.execute(
            select(TenantKnowledgeSource)
            .where(
                TenantKnowledgeSource.tenant_id == tenant_id,
                TenantKnowledgeSource.business_id == business_id,
                TenantKnowledgeSource.is_active.is_(True),
            )
            .order_by(TenantKnowledgeSource.created_at)
        )
        return list(result.scalars().all())
