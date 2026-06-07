import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.business_context_builder import (
    MESSAGE_ROLE_ASSISTANT,
    SESSION_STATUS_IN_PROGRESS,
    BusinessContextBuilderMessage,
    BusinessContextBuilderSession,
)

TEST_TOKEN = "bcb-api-test-token"


@pytest.fixture(autouse=True)
def configure_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.n8n_backend_api_token", TEST_TOKEN)
    monkeypatch.setattr("app.api.webhook_auth.settings.n8n_backend_api_token", TEST_TOKEN)


@pytest.fixture
def db_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def _override() -> MagicMock:
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override
    yield session
    app.dependency_overrides.clear()


def _auth_headers() -> dict[str, str]:
    return {"X-Alpstein-Webhook-Token": TEST_TOKEN}


@pytest.mark.anyio
async def test_create_business_context_builder_session_route(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session_id = uuid.uuid4()
    message_id = uuid.uuid4()
    now = datetime(2026, 6, 8, 12, 0, 0)
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        status=SESSION_STATUS_IN_PROGRESS,
        current_step="company_information",
        created_at=now,
        updated_at=now,
    )
    first_message = BusinessContextBuilderMessage(
        id=message_id,
        tenant_id=tenant_id,
        business_id=business_id,
        session_id=session_id,
        role=MESSAGE_ROLE_ASSISTANT,
        content="Hello. I will help you create a draft Business Context.",
        created_at=now,
    )

    from app.api.routes import business_context_builder as bcb_routes

    service = MagicMock()
    service.create_session = AsyncMock(return_value=(builder_session, first_message))
    monkeypatch.setattr(bcb_routes, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/business-context-builder/sessions",
            json={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["session"]["id"] == str(session_id)
    assert body["data"]["message"]["id"] == str(message_id)
    assert body["data"]["message"]["role"] == MESSAGE_ROLE_ASSISTANT
    db_session.commit.assert_awaited_once()
    service.create_session.assert_awaited_once()


@pytest.mark.anyio
async def test_business_context_builder_requires_auth(db_session: MagicMock):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/business-context-builder/sessions/{uuid.uuid4()}",
            params={
                "tenant_id": str(uuid.uuid4()),
                "business_id": str(uuid.uuid4()),
            },
        )

    assert response.status_code == 401
