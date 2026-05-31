"""Tests for Instagram outbound service (kill switch, dedup, logging)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.schemas.instagram_outbound import InstagramSendMessageRequest
from app.services.instagram_client import (
    InstagramApiError,
    InstagramGraphClient,
    InstagramSendResult,
)
from app.services.instagram_outbound_service import (
    INSTAGRAM_OUTBOUND_DUPLICATE_SKIPPED,
    InstagramOutboundDisabledError,
    InstagramOutboundService,
)


def _request(**overrides) -> InstagramSendMessageRequest:
    payload = {
        "business_id": "alpstein_ai_demo_001",
        "recipient_id": "17841400000000001",
        "message_text": "Hello from Alpstein",
        "correlation_id": "corr-123",
        "external_inbound_message_id": "mid.in.001",
    }
    payload.update(overrides)
    return InstagramSendMessageRequest(**payload)


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_dedup() -> MagicMock:
    dedup = MagicMock()
    dedup.try_acquire_send_slot = AsyncMock(return_value=True)
    dedup.record_provider_message_id = AsyncMock()
    dedup.release_send_slot = AsyncMock()
    return dedup


@pytest.mark.anyio
async def test_outbound_service_disabled(mock_session: MagicMock) -> None:
    service = InstagramOutboundService(
        app_settings=Settings(instagram_outbound_enabled=False),
    )

    with pytest.raises(InstagramOutboundDisabledError):
        await service.send_customer_reply(mock_session, _request())


@pytest.mark.anyio
async def test_outbound_service_success(
    mock_session: MagicMock,
    mock_dedup: MagicMock,
) -> None:
    class StubClient(InstagramGraphClient):
        def send_message(self, recipient_id: str, text: str, messaging_type: str = "RESPONSE"):
            assert recipient_id == "17841400000000001"
            assert text == "Hello from Alpstein"
            assert messaging_type == "RESPONSE"
            return InstagramSendResult(
                recipient_id=recipient_id,
                message_id="mid.sent.999",
            )

    service = InstagramOutboundService(
        app_settings=Settings(instagram_outbound_enabled=True),
        graph_client=StubClient(app_settings=Settings(instagram_outbound_enabled=True)),
        dedup_service=mock_dedup,
    )

    result = await service.send_customer_reply(mock_session, _request())

    assert result.provider_message_id == "mid.sent.999"
    assert result.status == "sent"
    mock_dedup.try_acquire_send_slot.assert_awaited_once()
    mock_dedup.record_provider_message_id.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_outbound_service_skips_duplicate_inbound(
    mock_session: MagicMock,
    mock_dedup: MagicMock,
) -> None:
    mock_dedup.try_acquire_send_slot = AsyncMock(return_value=False)

    service = InstagramOutboundService(
        app_settings=Settings(instagram_outbound_enabled=True),
        dedup_service=mock_dedup,
    )

    result = await service.send_customer_reply(mock_session, _request())

    assert result.status == "skipped"
    assert result.skip_code == INSTAGRAM_OUTBOUND_DUPLICATE_SKIPPED
    assert result.provider_message_id is None
    mock_session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_outbound_service_propagates_client_error(
    mock_session: MagicMock,
    mock_dedup: MagicMock,
) -> None:
    class FailingClient(InstagramGraphClient):
        def send_message(self, recipient_id: str, text: str, messaging_type: str = "RESPONSE"):
            raise InstagramApiError("Meta rejected send")

    service = InstagramOutboundService(
        app_settings=Settings(instagram_outbound_enabled=True),
        graph_client=FailingClient(app_settings=Settings(instagram_outbound_enabled=True)),
        dedup_service=mock_dedup,
    )

    with pytest.raises(InstagramApiError):
        await service.send_customer_reply(mock_session, _request())

    mock_dedup.release_send_slot.assert_awaited_once()
