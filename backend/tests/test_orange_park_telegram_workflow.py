import json
from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2]
    / "n8n"
    / "workflows"
    / "orange-park-telegram-mvp.json"
)


def _workflow() -> dict:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _node(workflow: dict, name: str) -> dict:
    return next(node for node in workflow["nodes"] if node["name"] == name)


def test_orange_park_workflow_requests_contact_when_backend_metadata_requires_it():
    workflow = _workflow()
    shape_code = _node(workflow, "Shape Telegram Reply")["parameters"]["jsCode"]
    send_parameters = _node(workflow, "Telegram Send Message")["parameters"]

    assert "metadata?.telegram_contact_request?.needed === true" in shape_code
    assert send_parameters["replyMarkup"] == (
        '={{ $json.reply_markup ? "replyKeyboard" : "none" }}'
    )
    assert send_parameters["replyKeyboard"] == {
        "rows": [
            {
                "row": {
                    "buttons": [
                        {
                            "text": "📱 Поділитися номером",
                            "additionalFields": {"request_contact": True},
                        }
                    ]
                }
            }
        ]
    }
    assert send_parameters["replyKeyboardOptions"] == {
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def test_orange_park_workflow_normalizes_telegram_contact_payload_without_token():
    workflow = _workflow()
    normalize_code = _node(workflow, "Normalize Telegram Message")["parameters"][
        "jsCode"
    ]

    assert "message.contact" in normalize_code
    assert "phone_number" in normalize_code
    assert "first_name" in normalize_code
    assert "last_name" in normalize_code
    assert "telegram_id: telegramUserId" in normalize_code
    assert "contact_shared: isContactShared" in normalize_code
    serialized = json.dumps(workflow).casefold()
    assert "api.telegram.org/bot" not in serialized
    assert "telegram_bot_token" not in serialized
