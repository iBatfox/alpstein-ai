"""Tests for Instagram DM ingress normalization."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.config import Settings
from app.services.instagram_ingress import InstagramIngressService

REAL_CHANGE_VALUE_PAYLOAD = {
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

LEGACY_MESSAGING_PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "messaging": [
                {
                    "sender": {"id": "111"},
                    "recipient": {"id": "222"},
                    "timestamp": 1520383572,
                    "message": {"mid": "mid.legacy.001", "text": "Hi there"},
                }
            ],
        }
    ],
}

CLOUD_API_MESSAGES_PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "changes": [
                {
                    "field": "messages",
                    "value": {
                        "messaging_product": "instagram",
                        "messages": [
                            {
                                "from": "1234567890",
                                "id": "mid.instagram.inbound.001",
                                "timestamp": "1520383572",
                                "type": "text",
                                "text": {"body": "Hello from Instagram"},
                            }
                        ],
                    },
                }
            ],
        }
    ],
}


@pytest.fixture
def ingress_service() -> InstagramIngressService:
    return InstagramIngressService(
        app_settings=Settings(instagram_user_id="IG_SOURCE_ACCOUNT"),
    )


def test_ingress_normalizes_changes_value_message(ingress_service: InstagramIngressService) -> None:
    result = ingress_service.parse_meta_webhook(REAL_CHANGE_VALUE_PAYLOAD)

    assert len(result.messages) == 1
    message = result.messages[0]
    assert message.platform == "instagram"
    assert message.external_user_id == "SENDER_ID"
    assert message.external_chat_id == "SENDER_ID"
    assert message.message_id == "MID_REAL_001"
    assert message.message_text == "hello real dm"
    assert message.direction == "inbound"
    assert message.raw_event_type == "changes.value.message"
    assert message.source_account_id == "IG_SOURCE_ACCOUNT"
    assert message.received_at == datetime.fromtimestamp(123, tz=UTC).replace(tzinfo=None)


def test_ingress_normalizes_legacy_messaging(ingress_service: InstagramIngressService) -> None:
    result = ingress_service.parse_meta_webhook(LEGACY_MESSAGING_PAYLOAD)

    assert len(result.messages) == 1
    message = result.messages[0]
    assert message.message_id == "mid.legacy.001"
    assert message.message_text == "Hi there"
    assert message.raw_event_type == "entry.messaging"


def test_ingress_normalizes_cloud_api_messages_array(
    ingress_service: InstagramIngressService,
) -> None:
    result = ingress_service.parse_meta_webhook(CLOUD_API_MESSAGES_PAYLOAD)

    assert len(result.messages) == 1
    message = result.messages[0]
    assert message.message_id == "mid.instagram.inbound.001"
    assert message.message_text == "Hello from Instagram"
    assert message.raw_event_type == "changes.value.messages"


def test_ingress_uses_fallback_message_id_without_mid(
    ingress_service: InstagramIngressService,
) -> None:
    payload = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "sender": {"id": "17841400000000000"},
                            "recipient": {"id": "17841499999999999"},
                            "timestamp": 1520383572,
                            "message": {"text": "test123", "is_deleted": False},
                        },
                    }
                ],
            }
        ],
    }

    result = ingress_service.parse_meta_webhook(payload)

    assert len(result.messages) == 1
    assert result.messages[0].message_id == "instagram:17841400000000000:1520383572"


def test_ingress_ignores_echo(ingress_service: InstagramIngressService) -> None:
    payload = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "sender": {"id": "SENDER_ID"},
                            "message": {
                                "mid": "MID_ECHO",
                                "text": "echo outbound",
                                "is_echo": True,
                            },
                        },
                    }
                ],
            }
        ],
    }

    result = ingress_service.parse_meta_webhook(payload)
    assert result.messages == ()


def test_ingress_ignores_read_seen_delivery(ingress_service: InstagramIngressService) -> None:
    payload = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {"field": "messaging_seen", "value": {"sender": {"id": "1"}}},
                    {"field": "read", "value": {"sender": {"id": "1"}}},
                    {"field": "delivery", "value": {"sender": {"id": "1"}}},
                ],
                "messaging": [
                    {
                        "sender": {"id": "111"},
                        "recipient": {"id": "222"},
                        "read": {"watermark": 123},
                    },
                    {
                        "sender": {"id": "111"},
                        "recipient": {"id": "222"},
                        "delivery": {"mids": ["mid.delivery"], "watermark": 123},
                    },
                ],
            }
        ],
    }

    result = ingress_service.parse_meta_webhook(payload)
    assert result.messages == ()


def test_ingress_ignores_deleted_message(ingress_service: InstagramIngressService) -> None:
    payload = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "sender": {"id": "SENDER_ID"},
                            "message": {
                                "mid": "MID_DELETED",
                                "text": "removed",
                                "is_deleted": True,
                            },
                        },
                    }
                ],
            }
        ],
    }

    result = ingress_service.parse_meta_webhook(payload)
    assert result.messages == ()


def test_ingress_ignores_messages_without_text(ingress_service: InstagramIngressService) -> None:
    payload = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "sender": {"id": "SENDER_ID"},
                            "message": {
                                "mid": "MID_ATTACHMENT",
                                "attachments": [{"type": "image"}],
                            },
                        },
                    }
                ],
            }
        ],
    }

    result = ingress_service.parse_meta_webhook(payload)
    assert result.messages == ()


def test_ingress_ignores_non_instagram_object(ingress_service: InstagramIngressService) -> None:
    result = ingress_service.parse_meta_webhook(
        {"object": "whatsapp_business_account", "entry": []},
    )
    assert result.messages == ()
