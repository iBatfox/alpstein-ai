"""ATTR-2 — channel source attribution webhook schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.webhook import NormalizedWebhookMessageRequest
from app.schemas.webhook_attribution import EXTERNAL_CONVERSATION_ID_PREFIXES


def _minimal_telegram_payload(**overrides) -> dict:
    payload = {
        "business_id": "demo_barbershop_001",
        "channel": "telegram",
        "customer": {
            "external_customer_id": "123456789",
            "name": "John",
        },
        "message": {
            "text": "Hello",
            "external_message_id": "tg:987654321:42",
        },
    }
    if "message" in overrides and isinstance(overrides["message"], dict):
        payload["message"] = {**payload["message"], **overrides.pop("message")}
    payload.update(overrides)
    return payload


def _full_attribution_payload() -> dict:
    return {
        "business_id": "demo_barbershop_001",
        "channel": "telegram",
        "source": {
            "platform": "telegram_bot_api",
            "account_id": "8123456789",
            "account_name": "@DemoBarbershopBot",
            "locale": "de-CH",
            "country": "CH",
            "region": "ZH",
            "timezone": "Europe/Zurich",
        },
        "attribution": {
            "marketing_source": "organic",
            "campaign_id": "spring-2026",
            "landing_page_url": "https://example.com/booking",
            "referrer_url": "https://google.com/search",
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "barbershop",
            "utm_content": "ad1",
            "utm_term": "haircut zurich",
        },
        "customer": {
            "external_customer_id": "123456789",
            "name": "John",
        },
        "message": {
            "text": "Hello, can I book tomorrow?",
            "external_message_id": "tg:987654321:42",
            "external_conversation_id": "tg:987654321",
            "timestamp": "2026-05-21T10:00:00Z",
            "client": {
                "user_agent": "Mozilla/5.0 (compatible; Demo/1.0)",
                "ip_address_hash": "sha256:abc123",
            },
            "raw_payload": {"update_id": 1},
        },
    }


def test_minimal_telegram_payload_still_passes():
    request = NormalizedWebhookMessageRequest.model_validate(_minimal_telegram_payload())

    assert request.channel.value == "telegram"
    assert request.source is None
    assert request.attribution is None
    assert request.message.external_conversation_id is None
    assert request.message.client is None
    assert request.message.external_message_id == "tg:987654321:42"


def test_full_source_attribution_client_payload_passes():
    request = NormalizedWebhookMessageRequest.model_validate(
        _full_attribution_payload()
    )

    assert request.source is not None
    assert request.source.platform == "telegram_bot_api"
    assert request.source.country == "CH"
    assert request.attribution is not None
    assert request.attribution.utm_source == "google"
    assert request.message.external_conversation_id == "tg:987654321"
    assert request.message.client is not None
    assert request.message.client.user_agent is not None
    assert request.message.raw_payload == {"update_id": 1}


@pytest.mark.parametrize("prefix", ["tg:", "wa:", "web:", "ig:", "fb:", "email:", "sms:", "voice:", "api:"])
def test_external_conversation_id_valid_prefixes_pass(prefix: str):
    request = NormalizedWebhookMessageRequest.model_validate(
        _minimal_telegram_payload(
            message={
                "text": "Hi",
                "external_message_id": "tg:1:1",
                "external_conversation_id": f"{prefix}thread-001",
            }
        )
    )
    assert request.message.external_conversation_id == f"{prefix}thread-001"


def test_external_conversation_id_without_prefix_fails():
    with pytest.raises(ValidationError) as exc_info:
        NormalizedWebhookMessageRequest.model_validate(
            _minimal_telegram_payload(
                message={
                    "text": "Hi",
                    "external_message_id": "tg:1:1",
                    "external_conversation_id": "987654321",
                }
            )
        )

    assert "external_conversation_id" in str(exc_info.value)


def test_external_message_id_without_prefix_still_allowed():
    """Adapters should prefix message ids; ATTR-2 does not break legacy shapes."""
    request = NormalizedWebhookMessageRequest.model_validate(
        _minimal_telegram_payload(
            message={
                "text": "Hi",
                "external_message_id": "wamid.example",
            }
        )
    )
    assert request.message.external_message_id == "wamid.example"


def test_over_length_source_platform_fails():
    with pytest.raises(ValidationError):
        NormalizedWebhookMessageRequest.model_validate(
            _minimal_telegram_payload(
                source={"platform": "x" * 129},
            )
        )


def test_over_length_utm_field_fails():
    with pytest.raises(ValidationError):
        NormalizedWebhookMessageRequest.model_validate(
            _minimal_telegram_payload(
                attribution={"utm_source": "a" * 257},
            )
        )


def test_secret_like_value_in_source_rejected():
    with pytest.raises(ValidationError) as exc_info:
        NormalizedWebhookMessageRequest.model_validate(
            _minimal_telegram_payload(
                source={"account_name": "Bearer sk-test-secret-token"},
            )
        )

    assert "secrets" in str(exc_info.value).lower()


def test_unknown_top_level_extra_field_ignored():
    request = NormalizedWebhookMessageRequest.model_validate(
        {
            **_minimal_telegram_payload(),
            "unknown_future_field": "ignored",
        }
    )
    assert request.business_id == "demo_barbershop_001"


def test_unknown_nested_extra_field_ignored():
    request = NormalizedWebhookMessageRequest.model_validate(
        _minimal_telegram_payload(
            source={
                "platform": "telegram_bot_api",
                "future_source_field": "ignored",
            }
        )
    )
    assert request.source is not None
    assert request.source.platform == "telegram_bot_api"


def test_whitespace_only_attribution_fields_normalize_to_none():
    request = NormalizedWebhookMessageRequest.model_validate(
        _minimal_telegram_payload(
            attribution={"utm_source": "   "},
        )
    )
    assert request.attribution is not None
    assert request.attribution.utm_source is None


def test_all_documented_conversation_prefixes_listed():
    assert "tg:" in EXTERNAL_CONVERSATION_ID_PREFIXES
    assert "wa:" in EXTERNAL_CONVERSATION_ID_PREFIXES
