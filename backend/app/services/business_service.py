from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessNotFoundError
from app.models.business import Business


class BusinessService:
    async def get_by_external_id(
        self,
        session: AsyncSession,
        external_id: str,
    ) -> Business:
        result = await session.execute(
            select(Business).where(Business.external_id == external_id).limit(1)
        )
        business = result.scalar_one_or_none()
        if business is None:
            raise BusinessNotFoundError()
        return business
