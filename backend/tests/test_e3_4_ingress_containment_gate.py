"""E3.4c — optional ingress containment gate tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app
from app.schemas.webhook import NormalizedWebhookMessageRequest
from app.services.webhook_message_service import WebhookMessageService

TEST_TOKEN = "e3-4-ingress-gate-test"


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


def _webhook_body(channel: str = "telegram") -> dict:
    return {
        "business_id": "demo_barbershop_001",
        "channel": channel,
        "customer": {"phone": "+41790000000"},
        "message": {"text": "hello"},
    }


@pytest.mark.anyio
async def test_gate_disabled_allows_webhook(db_session: MagicMock, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.core.config.settings", Settings(ingress_containment_enabled=False))
    service = MagicMock(spec=WebhookMessageService)
    service.process_incoming_message = AsyncMock()
    service.process_incoming_message.return_value = MagicMock(
        reply_to_customer="ok",
        lead_created=False,
        lead_updated=False,
        notify_owner=False,
        conversation=MagicMock(id=uuid.uuid4(), status="open"),
        message=MagicMock(id=uuid.uuid4()),
        flow=MagicMock(id=uuid.uuid4(), flow_key="default"),
        is_duplicate=False,
        lead=None,
        notification=None,
    )
    monkeypatch.setattr("app.api.routes.webhook.webhook_message_service", service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhook/message",
            json=_webhook_body("telegram"),
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    service.process_incoming_message.assert_awaited_once()


@pytest.mark.anyio
async def test_gate_blocks_only_contained_adapter(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "app.core.config.settings",
        Settings(ingress_containment_enabled=True, n8n_backend_api_token=TEST_TOKEN),
    )
    service = MagicMock(spec=WebhookMessageService)

    async def _process(session, body, *, observability=None):
        if body.channel.value == "telegram":
            from app.exceptions import AdapterIngressContainedError

            raise AdapterIngressContainedError(body.channel.value)
        return MagicMock(
            reply_to_customer="ok",
            lead_created=False,
            lead_updated=False,
            notify_owner=False,
            conversation=MagicMock(id=uuid.uuid4(), status="open"),
            message=MagicMock(id=uuid.uuid4()),
            flow=MagicMock(id=uuid.uuid4(), flow_key="default"),
            is_duplicate=False,
            lead=None,
            notification=None,
        )

    service.process_incoming_message = AsyncMock(side_effect=_process)
    monkeypatch.setattr("app.api.routes.webhook.webhook_message_service", service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        blocked = await client.post(
            "/api/v1/webhook/message",
            json=_webhook_body("telegram"),
            headers=_auth_headers(),
        )
        allowed = await client.post(
            "/api/v1/webhook/message",
            json=_webhook_body("website_chat"),
            headers=_auth_headers(),
        )

    assert blocked.status_code == 503
    assert blocked.json()["error"]["code"] == "ADAPTER_INGRESS_CONTAINED"
    assert allowed.status_code == 200
