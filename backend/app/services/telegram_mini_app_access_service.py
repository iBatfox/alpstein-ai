from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_context_builder import (
    MINI_APP_ALLOWED_USER_STATUS_ACTIVE,
    BusinessContextBuilderBusinessIntegration,
    BusinessContextBuilderMiniAppAllowedUser,
)


class TelegramMiniAppAccessDeniedError(Exception):
    """Raised when a validated Telegram user is not allowed to use the Mini App."""


class TelegramMiniAppAccessDisabledError(Exception):
    """Raised when a validated Telegram user exists but is disabled."""


class TelegramMiniAppAccessService:
    async def verify_allowed_user(
        self,
        session: AsyncSession,
        *,
        telegram_user_id: int,
    ) -> BusinessContextBuilderMiniAppAllowedUser:
        result = await session.execute(
            select(BusinessContextBuilderMiniAppAllowedUser).where(
                BusinessContextBuilderMiniAppAllowedUser.telegram_user_id
                == telegram_user_id
            )
        )
        allowed_user = result.scalar_one_or_none()
        if allowed_user is None:
            raise TelegramMiniAppAccessDeniedError()
        if allowed_user.status != MINI_APP_ALLOWED_USER_STATUS_ACTIVE:
            raise TelegramMiniAppAccessDisabledError()
        return allowed_user

    async def list_integrations(
        self,
        session: AsyncSession,
        *,
        alpstein_business_id: str | None,
    ) -> list[BusinessContextBuilderBusinessIntegration]:
        clean_business_id = (alpstein_business_id or "").strip()
        if not clean_business_id:
            return []

        result = await session.execute(
            select(BusinessContextBuilderBusinessIntegration)
            .where(
                BusinessContextBuilderBusinessIntegration.alpstein_business_id
                == clean_business_id
            )
            .order_by(
                BusinessContextBuilderBusinessIntegration.channel_type,
                BusinessContextBuilderBusinessIntegration.display_name,
            )
        )
        return list(result.scalars().all())
