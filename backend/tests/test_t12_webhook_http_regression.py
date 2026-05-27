"""T12.7 — HTTP-level regression tests for webhook lead/notification integration."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.exceptions import TenantContextError
from app.main import app
from app.models.business import Business
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.lead import LEAD_PRIORITY_NORMAL, LEAD_STATUS_NEW, Lead
from app.models.message import Message
from app.schemas.webhook_response import FORBIDDEN_WEBHOOK_RESPONSE_FIELDS
from app.services.ai_gateway._openai import OpenAIChatCompletionResponse
from app.services.message_service import IncomingMessageSaveResult
from tests.test_ai_gateway_service import MockOpenAIChatClient
from tests.test_t11_ai_webhook_integration import _build_stack

TEST_WEBHOOK_TOKEN = "t12-http-regression-token"


def _valid_payload(**overrides) -> dict:
    payload = {
        "business_id": "demo_barbershop_001",
        "channel": "whatsapp",
        "customer": {"phone": "+41790000000"},
        "message": {
            "text": "I'd like a haircut next week please.",
            "external_message_id": "wamid.http-regression-001",
        },
    }
    if "message" in overrides and isinstance(overrides["message"], dict):
        payload["message"] = {**payload["message"], **overrides.pop("message")}
    payload.update(overrides)
    return payload


def _auth_headers() -> dict[str, str]:
    return {"X-Alpstein-Webhook-Token": TEST_WEBHOOK_TOKEN}


@pytest.fixture(autouse=True)
def configure_webhook_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.config.settings.n8n_backend_api_token",
        TEST_WEBHOOK_TOKEN,
    )
    monkeypatch.setattr(
        "app.api.webhook_auth.settings.n8n_backend_api_token",
        TEST_WEBHOOK_TOKEN,
    )


@pytest.fixture
def http_db_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    session = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def _override() -> MagicMock:
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override
    yield session
    app.dependency_overrides.clear()


def _install_route_service(monkeypatch: pytest.MonkeyPatch, stack) -> None:
    from app.db.session import get_db_session

    stack.session.commit = AsyncMock()
    stack.session.rollback = AsyncMock()

    async def _override() -> MagicMock:
        yield stack.session

    app.dependency_overrides[get_db_session] = _override
    monkeypatch.setattr(
        "app.api.routes.webhook.webhook_message_service",
        stack.webhook_service,
    )


def _assert_envelope_shape(body: dict) -> None:
    assert body["success"] is True
    data = body["data"]
    assert "reply_to_customer" in data
    assert "lead_created" in data
    assert "lead_updated" in data
    assert "notify_owner" in data
    assert "conversation" in data
    assert "message" in data
    assert "id" in data["conversation"]
    assert "status" in data["conversation"]
    assert "id" in data["message"]
    assert "is_duplicate" in data["message"]


def _assert_no_internal_fields(body: dict) -> None:
    serialized = json.dumps(body).lower()
    for forbidden in FORBIDDEN_WEBHOOK_RESPONSE_FIELDS:
        assert forbidden not in serialized


@pytest.mark.anyio
async def test_http_new_lead_success_envelope(
    monkeypatch: pytest.MonkeyPatch,
    http_db_session: MagicMock,
):
    ai_text = "Tomorrow at 10:00 works."
    stack = _build_stack(
        gateway_client=MockOpenAIChatClient(
            response=OpenAIChatCompletionResponse(
                content=ai_text,
                model="gpt-4o-mini",
                input_tokens=10,
                output_tokens=5,
            ),
        ),
    )
    _install_route_service(monkeypatch, stack)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(),
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    _assert_envelope_shape(body)
    _assert_no_internal_fields(body)
    data = body["data"]
    assert data["reply_to_customer"] == ai_text
    assert data["lead_created"] is True
    assert data["lead_updated"] is False
    assert data["notify_owner"] is True
    assert data["lead"] is not None
    assert data["notification"] is not None
    assert data["notification"]["notification_type"] == "new_lead"
    assert data["notification"]["should_notify_owner"] is True
    assert data["notify_owner"] == data["notification"]["should_notify_owner"]
    assert not (data["lead_created"] and data["lead_updated"])
    stack.session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_http_duplicate_skips_lead_and_notification(
    monkeypatch: pytest.MonkeyPatch,
    http_db_session: MagicMock,
):
    last_outgoing = Message(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        sender_type="ai",
        direction="outgoing",
        channel="whatsapp",
        message_text="Prior AI reply only once.",
    )
    stack = _build_stack(
        gateway_client=MockOpenAIChatClient(
            response=OpenAIChatCompletionResponse(
                content="Should not run",
                model="gpt-4o-mini",
                input_tokens=1,
                output_tokens=1,
            ),
        ),
        is_duplicate=True,
        last_outgoing=last_outgoing,
    )
    _install_route_service(monkeypatch, stack)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(
                message={
                    "text": "duplicate",
                    "external_message_id": "wamid.duplicate-http",
                },
            ),
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["message"]["is_duplicate"] is True
    assert data["lead_created"] is False
    assert data["lead_updated"] is False
    assert data["notify_owner"] is False
    assert "notification" not in data
    assert data["reply_to_customer"] == "Prior AI reply only once."
    stack.lead_service.find_active_lead.assert_not_awaited()
    stack.lead_service.create_lead.assert_not_awaited()
    assert stack.outgoing_messages() == []


@pytest.mark.anyio
async def test_http_ai_failure_returns_fallback_and_ai_failure_notification(
    monkeypatch: pytest.MonkeyPatch,
    http_db_session: MagicMock,
):
    stack = _build_stack(
        gateway_client=MockOpenAIChatClient(
            error=httpx.TimeoutException("timed out"),
        ),
        fallback_response="HTTP fallback for owner alert.",
    )
    _install_route_service(monkeypatch, stack)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(
                message={
                    "text": "Book next week?",
                    "external_message_id": "wamid.ai-failure-http",
                },
            ),
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["reply_to_customer"] == "HTTP fallback for owner alert."
    assert data["lead_created"] is True
    assert data["lead_updated"] is False
    assert data["notify_owner"] is True
    assert data["notification"]["notification_type"] == "ai_failure"
    assert len(stack.outgoing_messages()) == 1


@pytest.mark.anyio
async def test_http_tenant_context_error_returns_validation_envelope(
    monkeypatch: pytest.MonkeyPatch,
    http_db_session: MagicMock,
):
    business = Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id="demo_barbershop_001",
        name="Demo",
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        customer_id=uuid.uuid4(),
        channel="whatsapp",
        status="open",
    )
    mismatched_customer = Customer(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=business.id,
        phone="+41790000000",
        source_channel="whatsapp",
    )
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="whatsapp",
        message_text="Hello",
    )

    from app.services.webhook_message_service import WebhookMessageService

    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business),
        ),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=mismatched_customer),
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation),
        ),
        message_service=MagicMock(
            save_incoming_customer_message=AsyncMock(
                return_value=IncomingMessageSaveResult(
                    message=incoming,
                    is_duplicate=False,
                )
            ),
        ),
    )
    monkeypatch.setattr("app.api.routes.webhook.webhook_message_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(),
            headers=_auth_headers(),
        )

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "success": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Tenant context is inconsistent",
        },
    }
    http_db_session.rollback.assert_awaited_once()
    http_db_session.commit.assert_not_awaited()
    assert str(business.id) not in json.dumps(body)
    assert str(mismatched_customer.id) not in json.dumps(body)


@pytest.mark.anyio
async def test_http_tenant_context_error_via_service_exception_mapping(
    monkeypatch: pytest.MonkeyPatch,
    http_db_session: MagicMock,
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
    mock_service = MagicMock()
    mock_service.process_incoming_message = AsyncMock(
        side_effect=TenantContextError("customer does not belong to tenant"),
    )
    monkeypatch.setattr("app.api.routes.webhook.webhook_message_service", mock_service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(),
            headers=_auth_headers(),
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "customer does not belong" not in response.text


@pytest.mark.anyio
async def test_http_routine_follow_up_omits_notification_object(
    monkeypatch: pytest.MonkeyPatch,
    http_db_session: MagicMock,
):
    stack = _build_stack(
        gateway_client=MockOpenAIChatClient(
            response=OpenAIChatCompletionResponse(
                content="Tuesday works.",
                model="gpt-4o-mini",
                input_tokens=5,
                output_tokens=3,
            ),
        ),
    )
    active_lead = Lead(
        id=uuid.uuid4(),
        tenant_id=stack.business.tenant_id,
        business_id=stack.business.id,
        customer_id=stack.customer.id,
        conversation_id=stack.conversation.id,
        status="in_progress",
        priority=LEAD_PRIORITY_NORMAL,
        source_channel="whatsapp",
    )
    lead_service = MagicMock()
    lead_service.find_active_lead = AsyncMock(return_value=active_lead)
    lead_service.create_lead = AsyncMock()
    lead_service.update_lead = AsyncMock(
        side_effect=lambda session, *, lead, **kw: lead
    )
    stack.lead_service = lead_service
    stack.webhook_service.lead_service = lead_service
    _install_route_service(monkeypatch, stack)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_valid_payload(
                message={
                    "text": "Tuesday afternoon is fine for me.",
                    "external_message_id": "wamid.follow-up-http",
                },
            ),
            headers=_auth_headers(),
        )

    data = response.json()["data"]
    assert data["lead_created"] is False
    assert data["lead_updated"] is True
    assert data["notify_owner"] is False
    assert "notification" not in data
    assert "lead" in data
