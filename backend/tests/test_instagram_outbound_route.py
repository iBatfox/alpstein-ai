"""Tests for POST /api/v1/channels/instagram/send-message."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.instagram_client import InstagramApiError
from app.services.instagram_outbound_service import (
    INSTAGRAM_OUTBOUND_DUPLICATE_SKIPPED,
    InstagramOutboundDisabledError,
    InstagramOutboundSendResult,
    InstagramOutboundService,
)

TEST_WEBHOOK_TOKEN = "instagram-outbound-route-token"


def _auth_headers() -> dict[str, str]:
    return {"X-Alpstein-Webhook-Token": TEST_WEBHOOK_TOKEN}


def _valid_body(**overrides) -> dict:
    payload = {
        "business_id": "alpstein_ai_demo_001",
        "recipient_id": "17841400000000001",
        "message_text": "Thanks for your message.",
        "correlation_id": "corr-abc",
        "external_inbound_message_id": "mid.in.001",
    }
    payload.update(overrides)
    return payload


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
def mock_outbound_service(monkeypatch):
    service = MagicMock(spec=InstagramOutboundService)
    monkeypatch.setattr(
        "app.api.routes.instagram_channel.instagram_outbound_service",
        service,
    )
    return service


@pytest.mark.anyio
async def test_instagram_send_message_disabled(mock_outbound_service) -> None:
    mock_outbound_service.send_customer_reply = AsyncMock(
        side_effect=InstagramOutboundDisabledError(),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/channels/instagram/send-message",
            json=_valid_body(),
            headers=_auth_headers(),
        )

    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INSTAGRAM_OUTBOUND_DISABLED"


@pytest.mark.anyio
async def test_instagram_send_message_validation_empty_recipient() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/channels/instagram/send-message",
            json=_valid_body(recipient_id="   "),
            headers=_auth_headers(),
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_instagram_send_message_validation_missing_business_id() -> None:
    body = _valid_body()
    del body["business_id"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/channels/instagram/send-message",
            json=body,
            headers=_auth_headers(),
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_instagram_send_message_validation_message_too_long() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/channels/instagram/send-message",
            json=_valid_body(message_text="x" * 1001),
            headers=_auth_headers(),
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_instagram_send_message_validation_missing_external_inbound_id() -> None:
    body = _valid_body()
    del body["external_inbound_message_id"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/channels/instagram/send-message",
            json=body,
            headers=_auth_headers(),
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_instagram_send_message_success(mock_outbound_service) -> None:
    mock_outbound_service.send_customer_reply = AsyncMock(
        return_value=InstagramOutboundSendResult(
            provider_message_id="mid.sent.123",
            status="sent",
        ),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/channels/instagram/send-message",
            json=_valid_body(),
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == {
        "provider_message_id": "mid.sent.123",
        "status": "sent",
    }


@pytest.mark.anyio
async def test_instagram_send_message_skips_duplicate_outbound(mock_outbound_service) -> None:
    mock_outbound_service.send_customer_reply = AsyncMock(
        return_value=InstagramOutboundSendResult(
            provider_message_id=None,
            status="skipped",
            skip_code=INSTAGRAM_OUTBOUND_DUPLICATE_SKIPPED,
        ),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/channels/instagram/send-message",
            json=_valid_body(),
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "skipped"
    assert body["data"]["skip_code"] == INSTAGRAM_OUTBOUND_DUPLICATE_SKIPPED


@pytest.mark.anyio
async def test_instagram_send_message_meta_error(mock_outbound_service) -> None:
    mock_outbound_service.send_customer_reply = AsyncMock(
        side_effect=InstagramApiError("Unsupported post request."),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/channels/instagram/send-message",
            json=_valid_body(),
            headers=_auth_headers(),
        )

    assert response.status_code == 502
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "API_ERROR"


@pytest.mark.anyio
async def test_instagram_send_message_requires_token() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/channels/instagram/send-message",
            json=_valid_body(),
        )

    assert response.status_code == 401
