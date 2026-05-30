"""Tests for Instagram → n8n unified ingress dispatch."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.config import Settings
from app.services.instagram_ingress import NormalizedInstagramInboundMessage
from app.services.instagram_n8n_dispatch_service import (
    DISPATCH_LOG_FAILED,
    DISPATCH_LOG_SKIPPED_DISABLED,
    DISPATCH_LOG_SUCCEEDED,
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
