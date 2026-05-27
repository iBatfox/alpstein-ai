import pytest
from pydantic import ValidationError

from app.schemas.webhook import (
    OPERATOR_BUSINESS_CONTEXT_MAX_LENGTH,
    NormalizedWebhookMessageRequest,
    WebhookChannel,
)


def _valid_payload(**overrides) -> dict:
    payload = {
        "business_id": "demo_barbershop_001",
        "channel": "whatsapp",
        "customer": {
            "phone": "+41790000000",
            "name": "John",
            "email": None,
            "external_customer_id": "wa_001",
        },
        "message": {
            "text": "Hello, can I book an appointment tomorrow?",
            "external_message_id": "wamid.example",
            "timestamp": "2026-05-21T10:00:00Z",
            "raw_payload": {"provider": "whatsapp"},
        },
    }
    payload.update(overrides)
    return payload


def test_valid_normalized_payload_passes():
    request = NormalizedWebhookMessageRequest.model_validate(_valid_payload())

    assert request.business_id == "demo_barbershop_001"
    assert request.channel is WebhookChannel.WHATSAPP
    assert request.customer.phone == "+41790000000"
    assert request.customer.name == "John"
    assert request.customer.email is None
    assert request.customer.external_customer_id == "wa_001"
    assert request.message.text == "Hello, can I book an appointment tomorrow?"
    assert request.message.external_message_id == "wamid.example"
    assert request.message.timestamp is not None
    assert request.message.raw_payload == {"provider": "whatsapp"}


def test_missing_business_id_fails():
    payload = _valid_payload()
    del payload["business_id"]

    with pytest.raises(ValidationError):
        NormalizedWebhookMessageRequest.model_validate(payload)


def test_invalid_channel_fails():
    payload = _valid_payload(channel="sms")

    with pytest.raises(ValidationError):
        NormalizedWebhookMessageRequest.model_validate(payload)


def test_missing_message_text_fails():
    payload = _valid_payload()
    del payload["message"]["text"]

    with pytest.raises(ValidationError):
        NormalizedWebhookMessageRequest.model_validate(payload)


def test_missing_customer_identifiers_fails():
    payload = _valid_payload(
        customer={
            "name": "John",
            "email": "john@example.com",
        }
    )

    with pytest.raises(ValidationError) as exc_info:
        NormalizedWebhookMessageRequest.model_validate(payload)

    assert "phone or external_customer_id is required" in str(exc_info.value)


def test_optional_fields_can_be_missing():
    request = NormalizedWebhookMessageRequest.model_validate(
        {
            "business_id": "demo_barbershop_001",
            "channel": "test",
            "customer": {"phone": "+41790000001"},
            "message": {"text": "Hi"},
        }
    )

    assert request.customer.name is None
    assert request.customer.email is None
    assert request.customer.external_customer_id is None
    assert request.message.external_message_id is None
    assert request.message.timestamp is None
    assert request.message.raw_payload is None


def test_raw_payload_accepts_dict():
    request = NormalizedWebhookMessageRequest.model_validate(
        _valid_payload(message={"text": "Hi", "raw_payload": {"nested": {"id": 1}}})
    )

    assert request.message.raw_payload == {"nested": {"id": 1}}


def test_operator_business_context_optional_and_normalized():
    request = NormalizedWebhookMessageRequest.model_validate(_valid_payload())

    assert request.operator_business_context is None

    with_notes = NormalizedWebhookMessageRequest.model_validate(
        _valid_payload(operator_business_context="  Weekend promo  ")
    )
    assert with_notes.operator_business_context == "Weekend promo"


def test_operator_business_context_max_length_enforced():
    with pytest.raises(ValidationError):
        NormalizedWebhookMessageRequest.model_validate(
            _valid_payload(
                operator_business_context="a" * (OPERATOR_BUSINESS_CONTEXT_MAX_LENGTH + 1)
            )
        )
