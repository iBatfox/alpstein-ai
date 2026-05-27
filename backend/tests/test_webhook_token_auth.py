import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.webhook_message_service import (
    WebhookMessageProcessResult,
    WebhookMessageService,
)

TEST_WEBHOOK_TOKEN = "test-webhook-token-secret"
INVALID_TOKEN = "not-the-configured-token"


def _valid_payload() -> dict:
    return {
        "business_id": "demo_barbershop_001",
        "channel": "whatsapp",
        "customer": {"phone": "+41790000000"},
        "message": {
            "text": "Hello",
            "external_message_id": "wamid.auth-test",
        },
    }


def _auth_headers(token: str | None = TEST_WEBHOOK_TOKEN) -> dict[str, str]:
    if token is None:
        return {}
    return {"X-Alpstein-Webhook-Token": token}


def _patch_server_webhook_token(
    monkeypatch: pytest.MonkeyPatch,
    token: str,
) -> None:
    monkeypatch.setattr(
        "app.core.config.settings.n8n_backend_api_token",
        token,
    )
    monkeypatch.setattr(
        "app.api.webhook_auth.settings.n8n_backend_api_token",
        token,
    )


@pytest.fixture(autouse=True)
def configure_webhook_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_server_webhook_token(monkeypatch, TEST_WEBHOOK_TOKEN)


@pytest.fixture
def mock_webhook_message_service(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    service = MagicMock(spec=WebhookMessageService)
    monkeypatch.setattr(
        "app.api.routes.webhook.webhook_message_service",
        service,
    )
    return service


@pytest.fixture
def mock_db_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def _override() -> MagicMock:
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override
    yield session
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_missing_token_returns_unauthorized(
    mock_webhook_message_service: MagicMock,
    mock_db_session: MagicMock,
):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(),
        )

    assert response.status_code == 401
    body = response.json()
    assert body == {
        "success": False,
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Webhook token is required",
        },
    }
    mock_webhook_message_service.process_incoming_message.assert_not_called()
    mock_db_session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_invalid_token_returns_unauthorized_without_leaking_secret(
    mock_webhook_message_service: MagicMock,
    mock_db_session: MagicMock,
):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(),
            headers=_auth_headers(INVALID_TOKEN),
        )

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "Invalid webhook token"
    assert TEST_WEBHOOK_TOKEN not in response.text
    assert INVALID_TOKEN not in response.text
    mock_webhook_message_service.process_incoming_message.assert_not_called()


@pytest.mark.anyio
async def test_valid_token_allows_webhook_processing(
    mock_webhook_message_service: MagicMock,
    mock_db_session: MagicMock,
):
    conversation = Conversation(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        channel="whatsapp",
        status="open",
    )
    message = Message(
        id=uuid.uuid4(),
        tenant_id=conversation.tenant_id,
        business_id=conversation.business_id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="whatsapp",
        message_text="Hello",
    )
    mock_webhook_message_service.process_incoming_message = AsyncMock(
        return_value=WebhookMessageProcessResult(
            conversation=conversation,
            message=message,
            is_duplicate=False,
            reply_to_customer="Authenticated reply",
            lead_created=False,
            notify_owner=False,
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(),
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json()["data"]["reply_to_customer"] == "Authenticated reply"
    mock_webhook_message_service.process_incoming_message.assert_awaited_once()
    mock_db_session.commit.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize("server_token", ["", "   "])
async def test_unset_server_api_token_returns_forbidden_without_leaking_tokens(
    server_token: str,
    monkeypatch: pytest.MonkeyPatch,
    mock_webhook_message_service: MagicMock,
    mock_db_session: MagicMock,
):
    _patch_server_webhook_token(monkeypatch, server_token)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(),
            headers=_auth_headers(TEST_WEBHOOK_TOKEN),
        )

    assert response.status_code == 403
    body = response.json()
    assert body == {
        "success": False,
        "error": {
            "code": "FORBIDDEN",
            "message": "Webhook authentication is not configured",
        },
    }
    assert TEST_WEBHOOK_TOKEN not in response.text
    mock_webhook_message_service.process_incoming_message.assert_not_called()
    mock_db_session.commit.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("client_token", ["", "   "])
async def test_empty_client_header_returns_unauthorized(
    client_token: str,
    mock_webhook_message_service: MagicMock,
    mock_db_session: MagicMock,
):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(),
            headers=_auth_headers(client_token),
        )

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "Webhook token is required"
    assert TEST_WEBHOOK_TOKEN not in response.text
    mock_webhook_message_service.process_incoming_message.assert_not_called()
    mock_db_session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_health_endpoint_works_without_webhook_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["success"] is True
