import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.business_context_builder import (
    MINI_APP_ALLOWED_USER_STATUS_ACTIVE,
    MINI_APP_ALLOWED_USER_STATUS_DISABLED,
    BusinessContextBuilderMiniAppAllowedUser,
)
from app.services.telegram_mini_app_access_service import (
    TelegramMiniAppAccessDeniedError,
    TelegramMiniAppAccessDisabledError,
    TelegramMiniAppAccessService,
)


def _allowed_user(status: str = MINI_APP_ALLOWED_USER_STATUS_ACTIVE):
    return BusinessContextBuilderMiniAppAllowedUser(
        id=uuid.uuid4(),
        telegram_user_id=777001,
        display_name="Allowed User",
        company_name="Alpstein Demo GmbH",
        status=status,
        notes=None,
        created_at=datetime(2026, 6, 8, 12, 0, 0),
        updated_at=datetime(2026, 6, 8, 12, 0, 0),
    )


def _session_returning(user):
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.anyio
async def test_verify_allowed_user_returns_active_allowlist_record():
    service = TelegramMiniAppAccessService()
    user = _allowed_user()
    session = _session_returning(user)

    result = await service.verify_allowed_user(session, telegram_user_id=777001)

    assert result is user
    session.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_verify_allowed_user_rejects_missing_allowlist_record():
    service = TelegramMiniAppAccessService()
    session = _session_returning(None)

    with pytest.raises(TelegramMiniAppAccessDeniedError):
        await service.verify_allowed_user(session, telegram_user_id=888001)


@pytest.mark.anyio
async def test_verify_allowed_user_rejects_disabled_allowlist_record():
    service = TelegramMiniAppAccessService()
    session = _session_returning(_allowed_user(MINI_APP_ALLOWED_USER_STATUS_DISABLED))

    with pytest.raises(TelegramMiniAppAccessDisabledError):
        await service.verify_allowed_user(session, telegram_user_id=777001)
