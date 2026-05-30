"""Tests for Instagram outbound service (kill switch + logging)."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.schemas.instagram_outbound import InstagramSendMessageRequest
from app.services.instagram_client import (
    InstagramApiError,
    InstagramGraphClient,
    InstagramSendResult,
)
from app.services.instagram_outbound_service import (
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


def test_outbound_service_disabled() -> None:
    service = InstagramOutboundService(
        app_settings=Settings(instagram_outbound_enabled=False),
    )

    with pytest.raises(InstagramOutboundDisabledError):
        service.send_customer_reply(_request())


def test_outbound_service_success() -> None:
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
    )

    result = service.send_customer_reply(_request())

    assert result.provider_message_id == "mid.sent.999"
    assert result.status == "sent"


def test_outbound_service_propagates_client_error() -> None:
    class FailingClient(InstagramGraphClient):
        def send_message(self, recipient_id: str, text: str, messaging_type: str = "RESPONSE"):
            raise InstagramApiError("Meta rejected send")

    service = InstagramOutboundService(
        app_settings=Settings(instagram_outbound_enabled=True),
        graph_client=FailingClient(app_settings=Settings(instagram_outbound_enabled=True)),
    )

    with pytest.raises(InstagramApiError):
        service.send_customer_reply(_request())
