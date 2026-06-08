import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlencode

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.business_context_builder import (
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_USER,
    MINI_APP_ALLOWED_USER_STATUS_ACTIVE,
    SESSION_STATUS_ACTIVE,
    BusinessContextBuilderMessage,
    BusinessContextBuilderMiniAppAllowedUser,
    BusinessContextBuilderResult,
    BusinessContextBuilderSession,
)
from app.services.business_context_builder_service import (
    BusinessContextBuilderSessionSnapshot,
)
from app.services.telegram_mini_app_access_service import (
    TelegramMiniAppAccessDeniedError,
    TelegramMiniAppAccessDisabledError,
)

BOT_TOKEN = "123456:test-token"
TENANT_ID = uuid.UUID("00000000-0000-4000-8000-000000000101")
BUSINESS_ID = uuid.UUID("00000000-0000-4000-8000-000000000202")


@pytest.fixture(autouse=True)
def configure_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    monkeypatch.setattr(bridge.settings, "telegram_bot_token", BOT_TOKEN)
    monkeypatch.setattr(bridge.settings, "telegram_initdata_max_age_seconds", 86400)
    monkeypatch.setattr(bridge.settings, "bcb_telegram_tenant_id", str(TENANT_ID))
    monkeypatch.setattr(bridge.settings, "bcb_telegram_business_id", str(BUSINESS_ID))

    access_service = MagicMock()

    async def _verify_allowed_user(_session, *, telegram_user_id: int):
        if telegram_user_id not in {777001, 777002, 777003}:
            raise TelegramMiniAppAccessDeniedError()
        return BusinessContextBuilderMiniAppAllowedUser(
            id=uuid.uuid4(),
            telegram_user_id=telegram_user_id,
            display_name="Bridge User",
            company_name="Alpstein Demo GmbH",
            status=MINI_APP_ALLOWED_USER_STATUS_ACTIVE,
            notes=None,
            created_at=datetime(2026, 6, 8, 12, 0, 0),
            updated_at=datetime(2026, 6, 8, 12, 0, 0),
        )

    access_service.verify_allowed_user = AsyncMock(side_effect=_verify_allowed_user)
    monkeypatch.setattr(bridge, "telegram_access_service", access_service)


@pytest.fixture(autouse=True)
def db_session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def _override() -> MagicMock:
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override
    yield session
    app.dependency_overrides.clear()


def signed_init_data(
    *,
    bot_token: str = BOT_TOKEN,
    auth_date: int | None = None,
    telegram_user_id: int = 777001,
) -> str:
    pairs = {
        "auth_date": str(int(time.time()) if auth_date is None else auth_date),
        "query_id": "bridge-query-1",
        "user": json.dumps(
            {
                "id": telegram_user_id,
                "first_name": "Bridge",
                "username": "bridge_user",
            },
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    pairs["hash"] = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(pairs)


def init_headers(init_data: str | None = None) -> dict[str, str]:
    return {"X-Telegram-Init-Data": init_data or signed_init_data()}


@pytest.mark.anyio
async def test_verify_access_accepts_valid_active_allowed_user():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/verify-access",
            json={"init_data": signed_init_data(telegram_user_id=777002)},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["allowed"] is True
    assert body["data"]["user"]["telegram_user_id"] == 777002
    assert body["data"]["user"]["display_name"] == "Bridge User"
    assert body["data"]["user"]["company_name"] == "Alpstein Demo GmbH"
    assert body["data"]["telegram_user"]["id"] == 777002
    assert "token" not in json.dumps(body).lower()


@pytest.mark.anyio
async def test_verify_access_rejects_valid_user_not_in_allowlist():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/verify-access",
            json={"init_data": signed_init_data(telegram_user_id=888001)},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TELEGRAM_USER_NOT_ALLOWED"


@pytest.mark.anyio
async def test_verify_access_rejects_disabled_allowed_user(monkeypatch: pytest.MonkeyPatch):
    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    access_service = MagicMock()
    access_service.verify_allowed_user = AsyncMock(
        side_effect=TelegramMiniAppAccessDisabledError()
    )
    monkeypatch.setattr(bridge, "telegram_access_service", access_service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/verify-access",
            json={"init_data": signed_init_data(telegram_user_id=777001)},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TELEGRAM_USER_NOT_ALLOWED"


@pytest.mark.anyio
async def test_verify_access_rejects_invalid_init_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/verify-access",
            json={"init_data": signed_init_data(bot_token="wrong-token")},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TELEGRAM_INIT_DATA_INVALID_SIGNATURE"


@pytest.mark.anyio
async def test_verify_access_rejects_missing_init_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/verify-access",
            json={},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TELEGRAM_INIT_DATA_REQUIRED"


@pytest.mark.anyio
async def test_auth_session_accepts_valid_init_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/auth/session",
            json={"init_data": signed_init_data(telegram_user_id=777002)},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["authenticated"] is True
    assert body["data"]["user"]["id"] == 777002
    assert "token" not in json.dumps(body).lower()


@pytest.mark.anyio
async def test_auth_session_rejects_invalid_signature():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/auth/session",
            json={"init_data": signed_init_data(bot_token="wrong-token")},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TELEGRAM_INIT_DATA_INVALID_SIGNATURE"


@pytest.mark.anyio
async def test_auth_session_rejects_expired_init_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/auth/session",
            json={"init_data": signed_init_data(auth_date=int(time.time()) - 90_000)},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TELEGRAM_INIT_DATA_EXPIRED"


@pytest.mark.anyio
async def test_auth_session_rejects_disallowed_telegram_user():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/auth/session",
            json={"init_data": signed_init_data(telegram_user_id=888001)},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TELEGRAM_USER_NOT_ALLOWED"


@pytest.mark.anyio
async def test_bridge_routes_enforce_allowlist_before_bcb_access(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    service = MagicMock()
    service.create_session = AsyncMock()
    monkeypatch.setattr(bridge, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/sessions",
            json={},
            headers=init_headers(signed_init_data(telegram_user_id=888001)),
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TELEGRAM_USER_NOT_ALLOWED"
    service.create_session.assert_not_called()
    db_session.commit.assert_not_called()


@pytest.mark.anyio
async def test_bridge_session_creation_uses_server_resolved_scope(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime(2026, 6, 8, 12, 0, 0)
    session_id = uuid.uuid4()
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        telegram_user_id="777003",
        status=SESSION_STATUS_ACTIVE,
        current_step="company_information",
        created_at=now,
        updated_at=now,
    )
    first_message = BusinessContextBuilderMessage(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        session_id=session_id,
        role=MESSAGE_ROLE_ASSISTANT,
        content="What is the name of your company?",
        created_at=now,
    )

    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    service = MagicMock()
    service.create_session = AsyncMock(return_value=(builder_session, first_message))
    monkeypatch.setattr(bridge, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/sessions",
            json={},
            headers=init_headers(signed_init_data(telegram_user_id=777003)),
        )

    assert response.status_code == 200
    service.create_session.assert_awaited_once_with(
        db_session,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        telegram_user_id="777003",
    )
    db_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_bridge_message_endpoint_rejects_frontend_scope_fields(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    service = MagicMock()
    service.save_user_message = AsyncMock()
    monkeypatch.setattr(bridge, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/telegram-mini-app/business-context-builder/sessions/{uuid.uuid4()}/messages",
            json={
                "tenant_id": str(uuid.uuid4()),
                "business_id": str(uuid.uuid4()),
                "content": "Ignore client scope.",
            },
            headers=init_headers(),
        )

    assert response.status_code == 422
    service.save_user_message.assert_not_called()
    db_session.commit.assert_not_called()


@pytest.mark.anyio
async def test_bridge_message_endpoint_uses_server_resolved_scope(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime(2026, 6, 8, 12, 0, 0)
    session_id = uuid.uuid4()
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        status=SESSION_STATUS_ACTIVE,
        current_step="business_description",
        created_at=now,
        updated_at=now,
    )
    user_message = BusinessContextBuilderMessage(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        session_id=session_id,
        role=MESSAGE_ROLE_USER,
        content="Alpstein",
        created_at=now,
    )
    assistant_message = BusinessContextBuilderMessage(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        session_id=session_id,
        role=MESSAGE_ROLE_ASSISTANT,
        content="What does your company do?",
        created_at=now,
    )

    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    service = MagicMock()
    service.save_user_message = AsyncMock(
        return_value=(builder_session, user_message, assistant_message)
    )
    monkeypatch.setattr(bridge, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/telegram-mini-app/business-context-builder/sessions/{session_id}/messages",
            json={"content": "Alpstein"},
            headers=init_headers(),
        )

    assert response.status_code == 200
    service.save_user_message.assert_awaited_once_with(
        db_session,
        session_id=session_id,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        content="Alpstein",
    )


@pytest.mark.anyio
async def test_bridge_contexts_pagination_uses_server_resolved_scope(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime(2026, 6, 8, 12, 0, 0)
    result = BusinessContextBuilderResult(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        session_id=uuid.uuid4(),
        structured_context={"company_overview": "Alpstein"},
        generated_prompt="Draft",
        created_at=now,
        updated_at=now,
    )

    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    service = MagicMock()
    service.list_contexts = AsyncMock(return_value=[result])
    monkeypatch.setattr(bridge, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/telegram-mini-app/business-context-builder/contexts",
            params={"limit": 5, "offset": 10},
            headers=init_headers(),
        )

    assert response.status_code == 200
    assert response.json()["data"]["limit"] == 5
    assert response.json()["data"]["offset"] == 10
    service.list_contexts.assert_awaited_once_with(
        db_session,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        limit=5,
        offset=10,
    )


@pytest.mark.anyio
async def test_bridge_complete_session_uses_server_resolved_scope(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime(2026, 6, 8, 12, 0, 0)
    session_id = uuid.uuid4()
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        status="completed",
        current_step="completed",
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    result = BusinessContextBuilderResult(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        session_id=session_id,
        structured_context={"company_overview": "Alpstein"},
        generated_prompt="Draft",
        created_at=now,
        updated_at=now,
    )

    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    service = MagicMock()
    service.complete_session = AsyncMock(return_value=(builder_session, result))
    monkeypatch.setattr(bridge, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/telegram-mini-app/business-context-builder/sessions/{session_id}/complete",
            json={},
            headers=init_headers(),
        )

    assert response.status_code == 200
    service.complete_session.assert_awaited_once_with(
        db_session,
        session_id=session_id,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
    )
    db_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_bridge_get_session_uses_server_scope_and_requires_no_internal_token(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime(2026, 6, 8, 12, 0, 0)
    session_id = uuid.uuid4()
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        status=SESSION_STATUS_ACTIVE,
        current_step="business_description",
        created_at=now,
        updated_at=now,
    )
    message = BusinessContextBuilderMessage(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        session_id=session_id,
        role=MESSAGE_ROLE_ASSISTANT,
        content="What does your company do?",
        created_at=now,
    )

    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    service = MagicMock()
    service.get_session = AsyncMock(
        return_value=BusinessContextBuilderSessionSnapshot(
            session=builder_session,
            messages=[message],
            result=None,
        )
    )
    monkeypatch.setattr(bridge, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/telegram-mini-app/business-context-builder/sessions/{session_id}",
            headers=init_headers(),
        )

    assert response.status_code == 200
    service.get_session.assert_awaited_once_with(
        db_session,
        session_id=session_id,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
    )


@pytest.mark.anyio
async def test_missing_server_scope_config_returns_project_style_error(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    monkeypatch.setattr(bridge.settings, "bcb_telegram_tenant_id", "")

    service = MagicMock()
    service.create_session = AsyncMock()
    monkeypatch.setattr(bridge, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/sessions",
            json={},
            headers=init_headers(),
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "BCB_TELEGRAM_TENANT_ID_NOT_CONFIGURED"
    service.create_session.assert_not_called()
    db_session.commit.assert_not_called()


def test_bridge_route_does_not_import_production_assistant_tables_or_webhook_auth():
    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    route_source = bridge.__loader__.get_source(bridge.__name__)

    assert "require_webhook_token" not in route_source
    assert "Conversation" not in route_source
    assert "Customer" not in route_source
    assert "Lead" not in route_source
    assert "PromptRun" not in route_source
