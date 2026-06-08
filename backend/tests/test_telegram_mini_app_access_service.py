import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.business_context_builder import (
    MINI_APP_ALLOWED_USER_STATUS_ACTIVE,
    MINI_APP_ALLOWED_USER_STATUS_DISABLED,
    BusinessContextBuilderBusinessIntegration,
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
        alpstein_business_id="alpstein-ai",
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


@pytest.mark.anyio
async def test_list_integrations_filters_by_alpstein_business_id():
    service = TelegramMiniAppAccessService()
    integration = BusinessContextBuilderBusinessIntegration(
        id=uuid.uuid4(),
        alpstein_business_id="alpstein-ai",
        channel_type="telegram",
        display_name="Telegram Bot 1",
        status="connected",
        external_channel_id="telegram_bot_1",
        provider="telegram",
        workflow_name="Telegram ingress",
        workflow_id="workflow-1",
        backend_route="/api/v1/webhook/telegram",
        notes=None,
        created_at=datetime(2026, 6, 8, 12, 0, 0),
        updated_at=datetime(2026, 6, 8, 12, 0, 0),
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [integration]
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    integrations = await service.list_integrations(
        session,
        alpstein_business_id="alpstein-ai",
    )

    assert integrations == [integration]
    statement = session.execute.await_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "business_context_builder.business_integrations" in compiled
    assert "alpstein-ai" in compiled
    assert "other-business" not in compiled


@pytest.mark.anyio
async def test_list_integrations_returns_empty_for_missing_business_id():
    service = TelegramMiniAppAccessService()
    session = MagicMock()
    session.execute = AsyncMock()

    integrations = await service.list_integrations(session, alpstein_business_id=None)

    assert integrations == []
    session.execute.assert_not_called()
