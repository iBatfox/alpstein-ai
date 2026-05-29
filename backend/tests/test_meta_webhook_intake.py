"""Unit tests for Meta webhook safe log extraction."""

from app.services.meta_webhook_intake import meta_webhook_log_context


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
                ]
            }
        ],
    }

    context = meta_webhook_log_context(body)

    assert context["object"] == "whatsapp_business_account"
    assert context["entry_count"] == 1
    assert context["messaging_product"] == "whatsapp"
    assert context["change_fields"] == ["messages"]
    assert context["message_ids"] == ["wamid.abc123"]
