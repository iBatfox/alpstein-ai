"""Instagram duplicate re-ingress: outbound allowed flag + Telegram unchanged."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.models.business import Business
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.webhook_response import serialize_webhook_message_success
from app.services.webhook_message_service import WebhookMessageService


@pytest.mark.anyio
async def test_instagram_outbound_allowed_true_when_not_yet_sent(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.webhook_message_service.settings",
        Settings(instagram_outbound_enabled=True),
    )
    dedup = MagicMock()
    dedup.is_already_sent = AsyncMock(return_value=False)
    service = WebhookMessageService(instagram_outbound_dedup_service=dedup)
    session = MagicMock()

    allowed = await service._instagram_outbound_allowed_for_response(
        session,
        channel="instagram",
        business_external_id="alpstein_ai_demo_001",
        external_message_id="mid.in.001",
        reply_to_customer="Thanks for your DM",
    )

    assert allowed is True
    dedup.is_already_sent.assert_awaited_once()


@pytest.mark.anyio
async def test_instagram_outbound_allowed_false_when_already_sent(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.webhook_message_service.settings",
        Settings(instagram_outbound_enabled=True),
    )
    dedup = MagicMock()
    dedup.is_already_sent = AsyncMock(return_value=True)
    service = WebhookMessageService(instagram_outbound_dedup_service=dedup)

    allowed = await service._instagram_outbound_allowed_for_response(
        MagicMock(),
        channel="instagram",
        business_external_id="alpstein_ai_demo_001",
        external_message_id="mid.in.001",
        reply_to_customer="Thanks for your DM",
    )

    assert allowed is False


@pytest.mark.anyio
async def test_telegram_channel_returns_none_for_outbound_allowed(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.webhook_message_service.settings",
        Settings(instagram_outbound_enabled=True),
    )
    service = WebhookMessageService(instagram_outbound_dedup_service=MagicMock())

    allowed = await service._instagram_outbound_allowed_for_response(
        MagicMock(),
        channel="telegram",
        business_external_id="alpstein_ai_demo_001",
        external_message_id="tg-1",
        reply_to_customer="Hi",
    )

    assert allowed is None


def test_webhook_response_includes_instagram_outbound_allowed_for_duplicate_reingress() -> None:
    payload = serialize_webhook_message_success(
        reply_to_customer="AI reply for duplicate re-ingress",
        lead_created=False,
        notify_owner=False,
        conversation_id=str(uuid.uuid4()),
        conversation_status="open",
        message_id=str(uuid.uuid4()),
        is_duplicate=True,
        flow_id=str(uuid.uuid4()),
        flow_key="default",
        instagram_outbound_allowed=True,
    )

    assert payload["data"]["message"]["is_duplicate"] is True
    assert payload["data"]["instagram_outbound_allowed"] is True


def test_webhook_response_omits_instagram_outbound_allowed_for_non_instagram() -> None:
    payload = serialize_webhook_message_success(
        reply_to_customer="Telegram reply",
        lead_created=False,
        notify_owner=False,
        conversation_id=str(uuid.uuid4()),
        conversation_status="open",
        message_id=str(uuid.uuid4()),
        is_duplicate=True,
        flow_id=str(uuid.uuid4()),
        flow_key="default",
        instagram_outbound_allowed=None,
    )

    assert payload["data"]["message"]["is_duplicate"] is True
    assert "instagram_outbound_allowed" not in payload["data"]


@pytest.mark.anyio
async def test_duplicate_instagram_webhook_route_exposes_outbound_allowed(
    monkeypatch,
) -> None:
    """Duplicate instagram POST /webhook/message still signals n8n may send outbound."""
    from httpx import ASGITransport, AsyncClient

    from app.api.routes import webhook as webhook_route
    from app.db.session import get_db_session
    from app.main import app
    from app.models.flow import Flow
    from app.services.webhook_message_service import WebhookMessageProcessResult

    TEST_TOKEN = "ig-reingress-token"
    monkeypatch.setattr("app.core.config.settings.n8n_backend_api_token", TEST_TOKEN)
    monkeypatch.setattr("app.api.webhook_auth.settings.n8n_backend_api_token", TEST_TOKEN)

    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    conversation = Conversation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=uuid.uuid4(),
        channel="instagram",
        status="open",
    )
    message = Message(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="instagram",
        message_text="Привет",
        external_message_id="mid.ig.duplicate.001",
    )
    flow = Flow(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        flow_key="default",
        flow_name="Default",
        status="active",
        is_default=True,
    )

    mock_service = MagicMock()
    mock_service.process_incoming_message = AsyncMock(
        return_value=WebhookMessageProcessResult(
            conversation=conversation,
            message=message,
            flow=flow,
            is_duplicate=True,
            reply_to_customer="Danke für deine Nachricht",
            lead_created=False,
            notify_owner=False,
            instagram_outbound_allowed=True,
        )
    )
    monkeypatch.setattr(webhook_route, "webhook_message_service", mock_service)

    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    async def _override_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = _override_db

    payload = {
        "business_id": "alpstein_ai_demo_001",
        "channel": "instagram",
        "customer": {
            "phone": "+41000000000",
            "external_customer_id": "17841400000000001",
        },
        "message": {
            "text": "Привет",
            "external_message_id": "mid.ig.duplicate.001",
        },
    }

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/webhook/message",
                json=payload,
                headers={"X-Alpstein-Webhook-Token": TEST_TOKEN},
            )

        body = response.json()
        assert response.status_code == 200
        assert body["data"]["message"]["is_duplicate"] is True
        assert body["data"]["instagram_outbound_allowed"] is True
    finally:
        app.dependency_overrides.clear()
