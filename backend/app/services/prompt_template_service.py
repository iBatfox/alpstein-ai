from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_template import PromptTemplate


class PromptTemplateService:
    async def get_by_template_key(
        self,
        session: AsyncSession,
        template_key: str,
    ) -> PromptTemplate | None:
        result = await session.execute(
            select(PromptTemplate)
            .where(
                PromptTemplate.template_key == template_key,
                PromptTemplate.is_active.is_(True),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
