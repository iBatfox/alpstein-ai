"""Meta WhatsApp Cloud API webhook verification and raw intake."""

from __future__ import annotations

import logging
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db_session
from app.main import app
from app.services.instagram_ingress import (
    InstagramIngressPersistOutcome,
    InstagramIngressProcessResult,
    InstagramIngressService,
    SKIP_REASON_MISSING_ACCOUNT_MAPPING,
    reset_instagram_ingress_services_for_tests,
)

TEST_VERIFY_TOKEN = "meta-test-verify-token"


@pytest.fixture(autouse=True)
def configure_meta_verify_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.meta_verify_token", TEST_VERIFY_TOKEN)
    monkeypatch.setattr(
        "app.api.routes.meta_webhook.settings.meta_verify_token",
        TEST_VERIFY_TOKEN,
    )


@pytest.fixture(autouse=True)
def mock_instagram_persistence(monkeypatch: pytest.MonkeyPatch):
    """Mock DB session and default successful Instagram persistence for route tests."""
    from app.api.routes import meta_webhook as route

    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def _override_db():
        yield session

    app.dependency_overrides[get_db_session] = _override_db

    persistence = reset_instagram_ingress_services_for_tests()
    ingress_service = InstagramIngressService()
    dispatch = MagicMock()
    dispatch.dispatch_persisted_message = AsyncMock(return_value=True)
    monkeypatch.setattr(route, "get_instagram_n8n_dispatch_service", lambda: dispatch)

    async def _process_webhook(_session, body):
        parsed = ingress_service.parse_meta_webhook(body)
        outcomes = []
        for message in parsed.messages:
            outcomes.append(
                InstagramIngressPersistOutcome(
                    normalized=message,
                    persisted=True,
                    is_duplicate=False,
                    skipped=False,
                    internal_message_id=uuid.uuid4(),
                )
            )
        return InstagramIngressProcessResult(tuple(outcomes))

    persistence.process_webhook = AsyncMock(side_effect=_process_webhook)
    monkeypatch.setattr(route, "get_instagram_ingress_persistence_service", lambda: persistence)

    yield persistence

    app.dependency_overrides.clear()


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
async def test_meta_webhook_post_accepts_instagram_payload() -> None:
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "IG_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "instagram",
                            "messages": [
                                {
                                    "from": "17841400000000000",
                                    "id": "mid.instagram.test-inbound",
                                    "timestamp": "1520383572",
                                    "type": "text",
                                    "text": {"body": "Instagram DM test"},
                                }
                            ],
                        },
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
async def test_meta_webhook_post_parses_real_instagram_dm_shape(
    caplog: pytest.LogCaptureFixture,
) -> None:
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "0",
                "time": 123,
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "sender": {"id": "SENDER_ID"},
                            "recipient": {"id": "RECIPIENT_ID"},
                            "timestamp": 123,
                            "message": {
                                "mid": "MID_REAL_001",
                                "text": "hello real dm",
                            },
                        },
                    }
                ],
            }
        ],
    }

    caplog.set_level(logging.INFO, logger="app.api.routes.meta_webhook")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/meta", json=payload)

    assert response.status_code == 200
    accepted = [record for record in caplog.records if record.getMessage() == "instagram ingress accepted"]
    assert len(accepted) == 1
    assert accepted[0].message_id == "MID_REAL_001"
    assert accepted[0].external_user_id == "SENDER_ID"
    shape_lines = [
        record.getMessage()
        for record in caplog.records
        if "instagram payload shape" in record.getMessage()
    ]
    assert shape_lines == []


@pytest.mark.anyio
async def test_meta_webhook_post_skipped_instagram_without_mapping(
    mock_instagram_persistence,
    caplog: pytest.LogCaptureFixture,
) -> None:
    ingress_service = InstagramIngressService()
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "0",
                "time": 123,
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "sender": {"id": "SENDER_ID"},
                            "recipient": {"id": "RECIPIENT_ID"},
                            "timestamp": 123,
                            "message": {
                                "mid": "MID_SKIP_001",
                                "text": "hello skipped",
                            },
                        },
                    }
                ],
            }
        ],
    }
    parsed = ingress_service.parse_meta_webhook(payload)
    assert len(parsed.messages) == 1

    async def _skipped_process(_session, body):
        messages = ingress_service.parse_meta_webhook(body).messages
        return InstagramIngressProcessResult(
            (
                InstagramIngressPersistOutcome(
                    normalized=messages[0],
                    persisted=False,
                    is_duplicate=False,
                    skipped=True,
                    skip_reason=SKIP_REASON_MISSING_ACCOUNT_MAPPING,
                ),
            )
        )

    mock_instagram_persistence.process_webhook = AsyncMock(side_effect=_skipped_process)

    caplog.set_level(logging.WARNING, logger="app.services.instagram_ingress")
    caplog.set_level(logging.INFO, logger="app.api.routes.meta_webhook")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/meta", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "received"}
    accepted = [record for record in caplog.records if record.getMessage() == "instagram ingress accepted"]
    assert accepted == []


@pytest.mark.anyio
async def test_meta_webhook_post_duplicate_instagram_ignored(
    mock_instagram_persistence,
    caplog: pytest.LogCaptureFixture,
) -> None:
    ingress_service = InstagramIngressService()
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "0",
                "time": 123,
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "sender": {"id": "SENDER_ID"},
                            "timestamp": 123,
                            "message": {
                                "mid": "MID_DUP_001",
                                "text": "duplicate dm",
                            },
                        },
                    }
                ],
            }
        ],
    }
    parsed = ingress_service.parse_meta_webhook(payload)
    assert len(parsed.messages) == 1

    async def _duplicate_process(_session, body):
        messages = ingress_service.parse_meta_webhook(body).messages
        return InstagramIngressProcessResult(
            (
                InstagramIngressPersistOutcome(
                    normalized=messages[0],
                    persisted=True,
                    is_duplicate=True,
                    skipped=False,
                    internal_message_id=uuid.uuid4(),
                ),
            )
        )

    mock_instagram_persistence.process_webhook = AsyncMock(side_effect=_duplicate_process)

    caplog.set_level(logging.INFO, logger="app.api.routes.meta_webhook")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/meta", json=payload)

    assert response.status_code == 200
    duplicate_logs = [
        record for record in caplog.records if record.getMessage() == "instagram ingress duplicate ignored"
    ]
    assert len(duplicate_logs) == 1
    assert duplicate_logs[0].message_ids == ["MID_DUP_001"]


@pytest.mark.anyio
async def test_meta_webhook_post_logs_instagram_ignored_for_non_message_event(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.config.settings.instagram_user_id", "27717448494529916")
    monkeypatch.setattr(
        "app.api.routes.meta_webhook.settings.instagram_user_id",
        "27717448494529916",
    )
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "IG_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "field": "messaging_seen",
                        "value": {
                            "sender": {"id": "17841400000000000"},
                            "timestamp": 1520383572,
                        },
                    }
                ],
            }
        ],
    }

    caplog.set_level(logging.INFO, logger="app.api.routes.meta_webhook")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/meta", json=payload)

    assert response.status_code == 200
    ignored = [
        record for record in caplog.records if record.getMessage() == "instagram ingress ignored"
    ]
    assert len(ignored) == 1
    assert ignored[0].ignored_reason == "non_message_change_field"
    assert ignored[0].change_fields == ["messaging_seen"]
    assert ignored[0].source_account_id == "27717448494529916"
    accepted = [record for record in caplog.records if record.getMessage() == "instagram ingress accepted"]
    assert accepted == []


@pytest.mark.anyio
async def test_meta_webhook_post_logs_instagram_payload_shape_when_unparsed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "IG_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "sender": {"id": "17841400000000000"},
                            "timestamp": 1520383572,
                        },
                    }
                ],
            }
        ],
    }

    caplog.set_level(logging.INFO, logger="app.api.routes.meta_webhook")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/meta", json=payload)

    assert response.status_code == 200
    shape_lines = [
        record.getMessage()
        for record in caplog.records
        if "instagram payload shape" in record.getMessage()
    ]
    assert len(shape_lines) == 1
    assert '"field":"messages"' in shape_lines[0]
    assert "secret" not in shape_lines[0]


@pytest.mark.anyio
async def test_meta_webhook_post_rejects_non_object_json() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/meta", json=["not", "an", "object"])

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
