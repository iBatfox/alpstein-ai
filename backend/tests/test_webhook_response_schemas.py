"""T12.5 webhook response schema serialization and safety."""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.webhook_response import (
    FORBIDDEN_WEBHOOK_RESPONSE_FIELDS,
    WebhookLeadSummary,
    WebhookMessageResponseData,
    WebhookMessageSuccessEnvelope,
    WebhookNotificationPayload,
    build_webhook_message_success_envelope,
    serialize_webhook_message_success,
)

SCHEMA_MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "schemas" / "webhook_response.py"


def test_backward_compatible_minimal_serialization():
    """Existing clients: core flags + conversation/message; no lead/notification keys."""
    conversation_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    payload = serialize_webhook_message_success(
        reply_to_customer="Hello from AI",
        lead_created=False,
        notify_owner=False,
        conversation_id=conversation_id,
        conversation_status="open",
        message_id=message_id,
        is_duplicate=False,
    )

    assert payload["success"] is True
    data = payload["data"]
    assert data["reply_to_customer"] == "Hello from AI"
    assert data["lead_created"] is False
    assert data["lead_updated"] is False
    assert data["notify_owner"] is False
    assert data["conversation"] == {"id": conversation_id, "status": "open"}
    assert data["message"] == {"id": message_id, "is_duplicate": False}
    assert "lead" not in data
    assert "notification" not in data


def test_lead_updated_defaults_false():
    data = WebhookMessageResponseData(
        reply_to_customer="Hi",
        lead_created=False,
        notify_owner=False,
        conversation={"id": str(uuid.uuid4()), "status": "open"},
        message={"id": str(uuid.uuid4()), "is_duplicate": False},
    )
    assert data.lead_updated is False


def test_optional_lead_and_notification_included_when_set():
    lead_id = str(uuid.uuid4())
    payload = serialize_webhook_message_success(
        reply_to_customer="Hi",
        lead_created=True,
        lead_updated=False,
        notify_owner=True,
        conversation_id=str(uuid.uuid4()),
        conversation_status="open",
        message_id=str(uuid.uuid4()),
        is_duplicate=False,
        lead=WebhookLeadSummary(id=lead_id, status="new", priority="normal"),
        notification=WebhookNotificationPayload(
            should_notify_owner=True,
            notification_type="new_lead",
            reason="lead_created",
            priority="normal",
        ),
    )
    data = payload["data"]
    assert data["lead_created"] is True
    assert data["lead_updated"] is False
    assert data["lead"] == {
        "id": lead_id,
        "status": "new",
        "priority": "normal",
    }
    assert data["notification"] == {
        "should_notify_owner": True,
        "notification_type": "new_lead",
        "reason": "lead_created",
        "priority": "normal",
    }


def test_lead_updated_without_lead_object():
    payload = serialize_webhook_message_success(
        reply_to_customer="Hi",
        lead_created=False,
        lead_updated=True,
        notify_owner=False,
        conversation_id=str(uuid.uuid4()),
        conversation_status="open",
        message_id=str(uuid.uuid4()),
        is_duplicate=False,
    )
    assert payload["data"]["lead_updated"] is True
    assert "lead" not in payload["data"]


def test_notification_omitted_when_none():
    payload = serialize_webhook_message_success(
        reply_to_customer="Hi",
        lead_created=False,
        notify_owner=False,
        conversation_id=str(uuid.uuid4()),
        conversation_status="open",
        message_id=str(uuid.uuid4()),
        is_duplicate=False,
        notification=None,
    )
    assert "notification" not in payload["data"]


def test_notification_type_none_omitted_from_json():
    """Null optional fields are omitted from serialized webhook JSON."""
    payload = serialize_webhook_message_success(
        reply_to_customer="Hi",
        lead_created=False,
        notify_owner=False,
        conversation_id=str(uuid.uuid4()),
        conversation_status="open",
        message_id=str(uuid.uuid4()),
        is_duplicate=False,
        notification=WebhookNotificationPayload(
            should_notify_owner=False,
            notification_type=None,
            reason="duplicate_webhook",
            priority="normal",
        ),
    )
    notification = payload["data"]["notification"]
    assert "notification_type" not in notification
    assert notification["should_notify_owner"] is False
    assert notification["reason"] == "duplicate_webhook"


def test_envelope_rejects_extra_fields():
    with pytest.raises(ValidationError):
        WebhookMessageSuccessEnvelope.model_validate(
            {
                "success": True,
                "data": {
                    "reply_to_customer": "Hi",
                    "lead_created": False,
                    "lead_updated": False,
                    "notify_owner": False,
                    "conversation": {"id": "c", "status": "open"},
                    "message": {"id": "m", "is_duplicate": False},
                    "final_prompt": "secret",
                },
            }
        )


def test_lead_summary_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        WebhookLeadSummary.model_validate(
            {
                "id": str(uuid.uuid4()),
                "status": "new",
                "priority": "normal",
                "raw_payload": {},
            }
        )


def test_forbidden_fields_not_in_response_model_fields():
    response_fields = set(WebhookMessageResponseData.model_fields)
    assert FORBIDDEN_WEBHOOK_RESPONSE_FIELDS.isdisjoint(response_fields)
    nested = (
        set(WebhookLeadSummary.model_fields)
        | set(WebhookNotificationPayload.model_fields)
        | set(WebhookMessageResponseData.model_fields)
    )
    assert FORBIDDEN_WEBHOOK_RESPONSE_FIELDS.isdisjoint(nested)


def test_schema_module_has_no_db_or_provider_imports():
    tree = ast.parse(SCHEMA_MODULE_PATH.read_text(encoding="utf-8"))
    import_from_modules = [
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    ]
    assert not any(
        mod.startswith(("app.models", "app.db", "sqlalchemy", "httpx", "openai"))
        for mod in import_from_modules
    )


def test_build_envelope_matches_serialize_helper():
    kwargs = {
        "reply_to_customer": "Hi",
        "lead_created": True,
        "lead_updated": False,
        "notify_owner": True,
        "conversation_id": str(uuid.uuid4()),
        "conversation_status": "waiting_for_customer",
        "message_id": str(uuid.uuid4()),
        "is_duplicate": False,
        "lead": WebhookLeadSummary(
            id=str(uuid.uuid4()),
            status="in_progress",
            priority="high",
        ),
    }
    envelope = build_webhook_message_success_envelope(**kwargs)
    assert envelope.model_dump(mode="json", exclude_none=True) == serialize_webhook_message_success(
        **kwargs
    )
