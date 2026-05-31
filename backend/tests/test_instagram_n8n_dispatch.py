"""Tests for Instagram → n8n unified ingress dispatch."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.config import Settings
from app.services.instagram_client import (
    InstagramApiError,
    InstagramUserProfile,
)
from app.services.instagram_ingress import NormalizedInstagramInboundMessage
from app.services.instagram_n8n_dispatch_service import (
    DISPATCH_LOG_FAILED,
    DISPATCH_LOG_SKIPPED_DISABLED,
    DISPATCH_LOG_SUCCEEDED,
    PROFILE_ENRICHMENT_LOG_FAILED,
    PROFILE_ENRICHMENT_LOG_STARTED,
    PROFILE_ENRICHMENT_LOG_SUCCEEDED,
    InstagramN8nDispatchContext,
    InstagramN8nDispatchService,
    build_instagram_n8n_event_payload,
)


def _normalized_message(**overrides) -> NormalizedInstagramInboundMessage:
    base = {
        "platform": "instagram",
        "external_user_id": "17841400000000001",
        "external_chat_id": "17841400000000001",
        "message_id": "mid.instagram.test.001",
        "message_text": "hello from instagram",
        "direction": "inbound",
        "received_at": datetime(2026, 5, 30, 20, 9, 15, tzinfo=UTC).replace(tzinfo=None),
        "raw_event_type": "changes.value.message",
        "source_account_id": "27717448494529916",
    }
    base.update(overrides)
    return NormalizedInstagramInboundMessage(**base)


def _context(**overrides) -> InstagramN8nDispatchContext:
    base = {
        "tenant_id": uuid.uuid4(),
        "business_external_id": "demo_alpstein_001",
        "internal_message_id": uuid.uuid4(),
        "normalized": _normalized_message(),
    }
    base.update(overrides)
    return InstagramN8nDispatchContext(**base)


def test_build_instagram_n8n_event_payload_shape() -> None:
    context = _context(correlation_id=uuid.UUID("11111111-1111-4111-8111-111111111111"))
    payload = build_instagram_n8n_event_payload(context)

    assert payload["correlation_id"] == "11111111-1111-4111-8111-111111111111"
    assert payload["business_id"] == "demo_alpstein_001"
    assert payload["channel"] == "instagram"
    assert payload["customer"]["external_customer_id"] == "17841400000000001"
    assert payload["message"]["external_message_id"] == "mid.instagram.test.001"
    assert payload["message"]["external_conversation_id"] == "ig:17841400000000001"
    assert payload["instagram_context"]["instagram_account_id"] == "27717448494529916"
    assert payload["message"]["text"] == "hello from instagram"


def test_build_instagram_n8n_event_payload_uses_profile() -> None:
    context = _context(correlation_id=uuid.UUID("11111111-1111-4111-8111-111111111111"))

    payload = build_instagram_n8n_event_payload(
        context,
        profile=InstagramUserProfile(
            id="17841400000000001",
            username="ibatfox",
            name="Ivan Bataiev-Lykhvar",
            profile_pic="https://example.test/profile.jpg",
        ),
    )

    assert payload["instagram_context"]["instagram_user_id"] == "17841400000000001"
    assert payload["instagram_context"]["instagram_username"] == "ibatfox"
    assert payload["instagram_context"]["instagram_display_name"] == "Ivan Bataiev-Lykhvar"
    assert payload["instagram_context"]["instagram_account_id"] == "27717448494529916"
    assert payload["customer"]["name"] == "Ivan Bataiev-Lykhvar"
    assert payload["customer"]["external_customer_id"] == "17841400000000001"


def test_build_instagram_n8n_event_payload_profile_fallback() -> None:
    payload = build_instagram_n8n_event_payload(_context())

    assert payload["instagram_context"]["instagram_username"] is None
    assert payload["instagram_context"]["instagram_display_name"] is None
    assert payload["customer"]["name"] is None


@pytest.mark.anyio
async def test_dispatch_skipped_when_disabled(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO", logger="app.services.instagram_n8n_dispatch_service")
    service = InstagramN8nDispatchService(
        app_settings=Settings(instagram_n8n_ingress_enabled=False),
    )

    result = await service.dispatch_persisted_message(_context())

    assert result is False
    assert any(
        record.getMessage() == DISPATCH_LOG_SKIPPED_DISABLED for record in caplog.records
    )


@pytest.mark.anyio
async def test_dispatch_succeeds_when_enabled() -> None:
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    client = MagicMock()
    client.post = AsyncMock(return_value=response)

    service = InstagramN8nDispatchService(
        app_settings=Settings(
            instagram_n8n_ingress_enabled=True,
            instagram_n8n_ingress_webhook_url="http://n8n:5678/webhook/test",
        ),
        http_client=client,
    )

    result = await service.dispatch_persisted_message(_context())

    assert result is True
    client.post.assert_awaited_once()
    args, kwargs = client.post.await_args
    assert args[0] == "http://n8n:5678/webhook/test"
    assert kwargs["json"]["channel"] == "instagram"


@pytest.mark.anyio
async def test_dispatch_enriches_instagram_profile_when_enabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="app.services.instagram_n8n_dispatch_service")
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    profile_client = MagicMock()
    profile_client.get_user_profile.return_value = InstagramUserProfile(
        id="17841400000000001",
        username="ibatfox",
        name="Ivan Bataiev-Lykhvar",
    )

    service = InstagramN8nDispatchService(
        app_settings=Settings(
            instagram_access_token="test-token",
            instagram_n8n_ingress_enabled=True,
            instagram_n8n_ingress_webhook_url="http://n8n:5678/webhook/test",
        ),
        http_client=client,
        profile_client=profile_client,
    )

    result = await service.dispatch_persisted_message(_context())

    assert result is True
    profile_client.get_user_profile.assert_called_once_with("17841400000000001")
    _args, kwargs = client.post.await_args
    payload = kwargs["json"]
    assert payload["customer"]["name"] == "Ivan Bataiev-Lykhvar"
    assert payload["instagram_context"]["instagram_username"] == "ibatfox"
    assert payload["instagram_context"]["instagram_display_name"] == "Ivan Bataiev-Lykhvar"
    assert any(
        record.getMessage().startswith(PROFILE_ENRICHMENT_LOG_STARTED)
        and getattr(record, "external_user_id") == "17841400000000001"
        for record in caplog.records
    )
    assert any(
        record.getMessage().startswith(PROFILE_ENRICHMENT_LOG_SUCCEEDED)
        and getattr(record, "profile_id") == "17841400000000001"
        and getattr(record, "has_username") is True
        and getattr(record, "has_display_name") is True
        for record in caplog.records
    )


@pytest.mark.anyio
async def test_dispatch_profile_fetch_failure_falls_back(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("WARNING", logger="app.services.instagram_n8n_dispatch_service")
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    profile_client = MagicMock()
    profile_client.get_user_profile.side_effect = InstagramApiError(
        "Application does not have permission",
    )

    service = InstagramN8nDispatchService(
        app_settings=Settings(
            instagram_access_token="test-token",
            instagram_n8n_ingress_enabled=True,
            instagram_n8n_ingress_webhook_url="http://n8n:5678/webhook/test",
        ),
        http_client=client,
        profile_client=profile_client,
    )

    result = await service.dispatch_persisted_message(_context())

    assert result is True
    _args, kwargs = client.post.await_args
    assert kwargs["json"]["customer"]["name"] is None
    assert any(
        record.getMessage().startswith(PROFILE_ENRICHMENT_LOG_FAILED)
        and getattr(record, "error_code") == "API_ERROR"
        and "Application does not have permission" in getattr(record, "error_message")
        for record in caplog.records
    )


@pytest.mark.anyio
async def test_dispatch_failure_is_non_fatal(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("WARNING", logger="app.services.instagram_n8n_dispatch_service")
    client = MagicMock()
    client.post = AsyncMock(
        side_effect=httpx.ConnectError("connection refused"),
    )
    service = InstagramN8nDispatchService(
        app_settings=Settings(instagram_n8n_ingress_enabled=True),
        http_client=client,
    )

    result = await service.dispatch_persisted_message(_context())

    assert result is False
    assert any(record.getMessage() == DISPATCH_LOG_FAILED for record in caplog.records)
