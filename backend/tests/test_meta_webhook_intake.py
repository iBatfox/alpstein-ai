"""Unit tests for Meta webhook safe log extraction."""

from app.services.meta_webhook_intake import (
    extract_instagram_inbound_messages,
    instagram_ingress_ignored_log_extra,
    instagram_payload_shape_diagnostic,
    meta_webhook_log_context,
    safe_message_text_for_log,
)


def test_meta_webhook_log_context_extracts_safe_fields() -> None:
    body = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [{"id": "wamid.abc123"}],
                        },
                    }
                ],
            }
        ],
    }

    context = meta_webhook_log_context(body)

    assert context["object"] == "whatsapp_business_account"
    assert context["entry_count"] == 1
    assert context["messaging_product"] == "whatsapp"
    assert context["change_fields"] == ["messages"]
    assert context["message_ids"] == ["wamid.abc123"]
    assert "instagram_inbound" not in context


def test_extract_instagram_real_dm_change_value_message() -> None:
    body = {
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

    messages = extract_instagram_inbound_messages(body)

    assert len(messages) == 1
    assert messages[0].sender_id == "SENDER_ID"
    assert messages[0].message_id == "MID_REAL_001"
    assert messages[0].message_text == "hello real dm"


def test_extract_instagram_real_dm_sender_as_string_and_message_id() -> None:
    body = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "sender": "STRING_SENDER",
                            "message": {
                                "id": "MID_REAL_002",
                                "text": {"body": "nested text body"},
                            },
                        },
                    }
                ],
            }
        ],
    }

    messages = extract_instagram_inbound_messages(body)

    assert len(messages) == 1
    assert messages[0].sender_id == "STRING_SENDER"
    assert messages[0].message_id == "MID_REAL_002"
    assert messages[0].message_text == "nested text body"


def test_extract_instagram_ignores_non_message_change_fields() -> None:
    body = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {"field": "messaging_seen", "value": {"sender": {"id": "1"}}},
                    {"field": "read", "value": {"sender": {"id": "1"}}},
                    {"field": "delivery", "value": {"sender": {"id": "1"}}},
                ],
            }
        ],
    }

    assert extract_instagram_inbound_messages(body) == []


def test_extract_instagram_ignores_echo_in_change_value_message() -> None:
    body = {
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

    assert extract_instagram_inbound_messages(body) == []


def test_extract_instagram_cloud_api_messages() -> None:
    body = {
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

    messages = extract_instagram_inbound_messages(body)

    assert len(messages) == 1
    assert messages[0].sender_id == "1234567890"
    assert messages[0].message_id == "mid.instagram.inbound.001"
    assert messages[0].message_text == "Hello from Instagram"
    assert messages[0].message_type == "text"


def test_meta_webhook_log_context_includes_instagram_inbound() -> None:
    body = {
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
                                    "from": "9876543210",
                                    "id": "mid.instagram.inbound.002",
                                    "type": "text",
                                    "text": {"body": "Need a quote"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }

    context = meta_webhook_log_context(body)

    assert context["object"] == "instagram"
    assert context["messaging_product"] == "instagram"
    assert context["instagram_inbound"] == [
        {
            "sender_id": "9876543210",
            "message_id": "mid.instagram.inbound.002",
            "message_text": "Need a quote",
            "message_type": "text",
        }
    ]


def test_extract_instagram_messaging_array_format() -> None:
    body = {
        "object": "instagram",
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "111"},
                        "recipient": {"id": "222"},
                        "timestamp": 1520383572,
                        "message": {
                            "mid": "mid.legacy.001",
                            "text": "Hi there",
                        },
                    },
                    {
                        "sender": {"id": "111"},
                        "message": {
                            "mid": "mid.echo",
                            "text": "echo",
                            "is_echo": True,
                        },
                    },
                ],
            }
        ],
    }

    messages = extract_instagram_inbound_messages(body)

    assert len(messages) == 1
    assert messages[0].sender_id == "111"
    assert messages[0].message_id == "mid.legacy.001"
    assert messages[0].message_text == "Hi there"


def test_instagram_payload_shape_diagnostic_cloud_api_structure() -> None:
    body = {
        "object": "instagram",
        "entry": [
            {
                "id": "IG_ACCOUNT",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "instagram",
                            "metadata": {"display_phone_number": "hidden"},
                            "messages": [
                                {
                                    "from": "sender",
                                    "id": "mid.1",
                                    "text": {"body": "secret text must not appear"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
        "access_token": "must-not-log",
    }

    shape = instagram_payload_shape_diagnostic(body)

    assert shape["top_level_keys"] == ["entry", "object"]
    assert shape["entry_count"] == 1
    entry = shape["entries"][0]
    assert entry["entry_id"] == "IG_ACCOUNT"
    assert entry["has_messaging"] is False
    change = entry["changes"][0]
    assert change["field"] == "messages"
    assert "messages" in change["value_keys"]
    assert "secret text must not appear" not in str(shape)


def test_instagram_payload_shape_diagnostic_messaging_structure() -> None:
    body = {
        "object": "instagram",
        "entry": [
            {
                "id": "IG_ACCOUNT",
                "messaging": [
                    {
                        "sender": {"id": "111"},
                        "recipient": {"id": "222"},
                        "message": {
                            "mid": "mid.messaging.1",
                            "text": "hello must not appear",
                        },
                    }
                ],
            }
        ],
    }

    shape = instagram_payload_shape_diagnostic(body)
    item = shape["entries"][0]["messaging_items"][0]

    assert item["sender_id"] == "111"
    assert item["recipient_id"] == "222"
    assert item["message_mid"] == "mid.messaging.1"
    assert item["has_message_text"] is True
    assert "hello must not appear" not in str(shape)


def test_safe_message_text_for_log_truncates_long_text() -> None:
    long_text = "x" * 250
    logged = safe_message_text_for_log(long_text)
    assert len(logged) == 201
    assert logged.endswith("…")

    context = meta_webhook_log_context(
        {
            "object": "instagram",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "instagram",
                                "messages": [
                                    {
                                        "from": "1",
                                        "id": "mid.long",
                                        "type": "text",
                                        "text": {"body": long_text},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
    )

    entry = context["instagram_inbound"][0]
    assert entry["message_text_length"] == 250
    assert len(entry["message_text"]) == 201


def test_instagram_ingress_ignored_log_extra_messaging_seen() -> None:
    body = {
        "object": "instagram",
        "entry": [
            {
                "id": "IG_ACCOUNT",
                "changes": [
                    {
                        "field": "messaging_seen",
                        "value": {"sender": {"id": "111"}, "timestamp": 123},
                    }
                ],
            }
        ],
    }

    extra = instagram_ingress_ignored_log_extra(body, source_account_id="27717448494529916")

    assert extra["object"] == "instagram"
    assert extra["entry_count"] == 1
    assert "changes" in extra["entry_keys"]
    assert extra["change_fields"] == ["messaging_seen"]
    assert extra["has_messaging"] is False
    assert extra["raw_event_types"] == ["changes.messaging_seen"]
    assert extra["ignored_reason"] == "non_message_change_field"
    assert extra["source_account_id"] == "27717448494529916"
    assert "access_token" not in str(extra)


def test_instagram_ingress_ignored_log_extra_echo_message() -> None:
    body = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "sender": {"id": "SENDER"},
                            "message": {
                                "mid": "MID_ECHO",
                                "text": "secret outbound text must not appear in ignored log",
                                "is_echo": True,
                            },
                        },
                    }
                ],
            }
        ],
    }

    extra = instagram_ingress_ignored_log_extra(body, source_account_id="IG_ACCOUNT")

    assert extra["ignored_reason"] == "echo_message"
    assert extra["change_fields"] == ["messages"]
    assert "changes.value.message.echo" in extra["raw_event_types"]
    assert "secret outbound text" not in str(extra)


def test_instagram_ingress_ignored_log_extra_read_delivery() -> None:
    body = {
        "object": "instagram",
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "111"},
                        "recipient": {"id": "222"},
                        "read": {"watermark": 123},
                    },
                    {
                        "sender": {"id": "111"},
                        "recipient": {"id": "222"},
                        "delivery": {"mids": ["mid.1"], "watermark": 123},
                    },
                ],
            }
        ],
    }

    extra = instagram_ingress_ignored_log_extra(body, source_account_id="IG_ACCOUNT")

    assert extra["has_messaging"] is True
    assert extra["ignored_reason"] == "read_or_delivery"
    assert "entry.messaging.read" in extra["raw_event_types"]
    assert "entry.messaging.delivery" in extra["raw_event_types"]


def test_instagram_ingress_ignored_log_extra_no_text_attachment() -> None:
    body = {
        "object": "instagram",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "sender": {"id": "SENDER"},
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

    extra = instagram_ingress_ignored_log_extra(body, source_account_id="IG_ACCOUNT")

    assert extra["ignored_reason"] == "no_text_content"
    assert "changes.value.message.no_text" in extra["raw_event_types"]
