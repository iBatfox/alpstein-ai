import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.exceptions import BusinessNotFoundError
from app.main import app
from app.models.business import Business
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.services.webhook_message_service import (
    DUPLICATE_SAFE_ACKNOWLEDGMENT,
    WebhookMessageProcessResult,
    WebhookMessageService,
)

TEST_WEBHOOK_TOKEN = "integration-route-token"


def _valid_payload(**overrides) -> dict:
    payload = {
        "business_id": "demo_barbershop_001",
        "channel": "whatsapp",
        "customer": {"phone": "+41790000000"},
        "message": {
            "text": "Hello",
            "external_message_id": "wamid.example",
        },
    }
    payload.update(overrides)
    return payload


def _auth_headers() -> dict[str, str]:
    return {"X-Alpstein-Webhook-Token": TEST_WEBHOOK_TOKEN}


@pytest.fixture(autouse=True)
def configure_webhook_token(monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.n8n_backend_api_token",
        TEST_WEBHOOK_TOKEN,
    )
    monkeypatch.setattr(
        "app.api.webhook_auth.settings.n8n_backend_api_token",
        TEST_WEBHOOK_TOKEN,
    )


@pytest.fixture
def mock_webhook_message_service(monkeypatch):
    service = MagicMock(spec=WebhookMessageService)
    monkeypatch.setattr(
        "app.api.routes.webhook.webhook_message_service",
        service,
    )
    return service


@pytest.fixture
def mock_db_session(monkeypatch):
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def _override():
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override
    yield session
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_webhook_message_valid_payload_returns_success(
    mock_webhook_message_service: MagicMock,
    mock_db_session: MagicMock,
):
    business_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    message_id = uuid.uuid4()
    business = Business(
        id=business_id,
        tenant_id=tenant_id,
        external_id="demo_barbershop_001",
        name="Demo",
    )
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        phone="+41790000000",
        source_channel="whatsapp",
    )
    conversation = Conversation(
        id=conversation_id,
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer.id,
        channel="whatsapp",
        status="open",
    )
    message = Message(
        id=message_id,
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
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
            reply_to_customer=DUPLICATE_SAFE_ACKNOWLEDGMENT,
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
    body = response.json()
    assert body == {
        "success": True,
        "data": {
            "reply_to_customer": DUPLICATE_SAFE_ACKNOWLEDGMENT,
            "lead_created": False,
            "lead_updated": False,
            "notify_owner": False,
            "conversation": {
                "id": str(conversation_id),
                "status": "open",
            },
            "message": {
                "id": str(message_id),
                "is_duplicate": False,
            },
        },
    }
    mock_db_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_webhook_message_business_not_found_returns_error_envelope(
    mock_webhook_message_service: MagicMock,
    mock_db_session: MagicMock,
):
    mock_webhook_message_service.process_incoming_message = AsyncMock(
        side_effect=BusinessNotFoundError()
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(),
            headers=_auth_headers(),
        )

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {
            "code": "BUSINESS_NOT_FOUND",
            "message": "Business not found",
        },
    }
    mock_db_session.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_webhook_message_duplicate_returns_is_duplicate_true(
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
            is_duplicate=True,
            reply_to_customer=DUPLICATE_SAFE_ACKNOWLEDGMENT,
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

    assert response.json()["data"]["message"]["is_duplicate"] is True


@pytest.mark.anyio
async def test_webhook_message_has_no_ai_lead_or_notification_side_effects(
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
            reply_to_customer=DUPLICATE_SAFE_ACKNOWLEDGMENT,
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

    data = response.json()["data"]
    assert data["lead_created"] is False
    assert data["notify_owner"] is False
    assert data["reply_to_customer"] == DUPLICATE_SAFE_ACKNOWLEDGMENT
    assert "lead" not in data


@pytest.mark.anyio
async def test_webhook_message_passes_customer_resolution_to_service(
    mock_webhook_message_service: MagicMock,
    mock_db_session: MagicMock,
):
    mock_webhook_message_service.process_incoming_message = AsyncMock(
        side_effect=BusinessNotFoundError()
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(customer={"phone": "+41791111111"}),
            headers=_auth_headers(),
        )

    request = mock_webhook_message_service.process_incoming_message.await_args.args[1]
    assert request.customer.phone == "+41791111111"


@pytest.mark.anyio
async def test_webhook_message_reusable_conversation_status_in_response(
    mock_webhook_message_service: MagicMock,
    mock_db_session: MagicMock,
):
    conversation = Conversation(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        channel="whatsapp",
        status="waiting_for_customer",
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
            reply_to_customer=DUPLICATE_SAFE_ACKNOWLEDGMENT,
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

    assert response.json()["data"]["conversation"]["status"] == "waiting_for_customer"


@pytest.mark.anyio
async def test_webhook_message_new_open_conversation_after_non_reusable_status(
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
            reply_to_customer=DUPLICATE_SAFE_ACKNOWLEDGMENT,
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

    assert response.json()["data"]["conversation"]["status"] == "open"


@pytest.mark.anyio
async def test_webhook_message_passes_correlation_id_to_service(
    mock_webhook_message_service: MagicMock,
    mock_db_session: MagicMock,
):
    correlation_id = uuid.uuid4()
    n8n_execution_id = "n8n-exec-42"
    mock_webhook_message_service.process_incoming_message = AsyncMock(
        return_value=WebhookMessageProcessResult(
            conversation=Conversation(
                id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                business_id=uuid.uuid4(),
                customer_id=uuid.uuid4(),
                channel="whatsapp",
                status="open",
            ),
            message=Message(
                id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                business_id=uuid.uuid4(),
                conversation_id=uuid.uuid4(),
                sender_type="customer",
                direction="incoming",
                channel="whatsapp",
                message_text="Hello",
            ),
            is_duplicate=False,
            reply_to_customer="OK",
            lead_created=False,
            notify_owner=False,
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(),
            headers={
                **_auth_headers(),
                "X-Correlation-Id": str(correlation_id),
                "X-N8n-Execution-Id": n8n_execution_id,
            },
        )

    assert response.status_code == 200
    kwargs = mock_webhook_message_service.process_incoming_message.await_args.kwargs
    observability = kwargs["observability"]
    assert observability.correlation_id == correlation_id
    assert observability.n8n_execution_id == n8n_execution_id


@pytest.mark.anyio
async def test_webhook_message_invalid_correlation_id_returns_validation_error(
    mock_webhook_message_service: MagicMock,
    mock_db_session: MagicMock,
):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(),
            headers={**_auth_headers(), "X-Correlation-Id": "not-a-uuid"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    mock_webhook_message_service.process_incoming_message.assert_not_called()
