"""Meta WhatsApp Cloud API webhook verification and raw intake."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

TEST_VERIFY_TOKEN = "meta-test-verify-token"


@pytest.fixture(autouse=True)
def configure_meta_verify_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.meta_verify_token", TEST_VERIFY_TOKEN)
    monkeypatch.setattr(
        "app.api.routes.meta_webhook.settings.meta_verify_token",
        TEST_VERIFY_TOKEN,
    )


@pytest.mark.anyio
async def test_meta_webhook_verification_success() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/webhooks/meta",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": TEST_VERIFY_TOKEN,
                "hub.challenge": "1158201444",
            },
        )

    assert response.status_code == 200
    assert response.text == "1158201444"
    assert "text/plain" in response.headers.get("content-type", "")


@pytest.mark.anyio
async def test_meta_webhook_verification_wrong_token() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/webhooks/meta",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "1158201444",
            },
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_meta_webhook_verification_wrong_mode() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/webhooks/meta",
            params={
                "hub.mode": "unsubscribe",
                "hub.verify_token": TEST_VERIFY_TOKEN,
                "hub.challenge": "1158201444",
            },
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_meta_webhook_verification_missing_configured_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.config.settings.meta_verify_token", "")
    monkeypatch.setattr("app.api.routes.meta_webhook.settings.meta_verify_token", "")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/webhooks/meta",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": TEST_VERIFY_TOKEN,
                "hub.challenge": "1158201444",
            },
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_meta_webhook_post_accepts_valid_payload() -> None:
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550001111",
                                "phone_number_id": "PHONE_NUMBER_ID",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": "15551234567",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "id": "wamid.test-inbound-001",
                                    "timestamp": "1520383572",
                                    "text": {"body": "Hello"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/meta", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "received"}


@pytest.mark.anyio
async def test_meta_webhook_post_rejects_empty_body() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhooks/meta",
            content="",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_meta_webhook_post_rejects_invalid_json() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhooks/meta",
            content="{not-json",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_meta_webhook_post_rejects_non_object_json() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/meta", json=["not", "an", "object"])

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
