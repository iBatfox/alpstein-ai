from __future__ import annotations

import json
from datetime import datetime

import httpx
import pytest

from app.core.config import Settings
from app.schemas.conversation_context import (
    ConversationHistory,
    ConversationHistoryMessage,
)
from app.services.orange_park_bitrix_service import (
    BITRIX_LEAD_TITLE,
    BITRIX_SOURCE_DESCRIPTION,
    BITRIX_SOURCE_ID,
    OrangeParkBitrixContact,
    OrangeParkBitrixService,
    normalize_bitrix_phone,
)


def _settings(*, configured: bool = True) -> Settings:
    return Settings(
        ORANGE_PARK_BITRIX_WEBHOOK_URL=(
            "https://bitrix.invalid/rest/test/" if configured else ""
        ),
    )


def _contact() -> OrangeParkBitrixContact:
    return OrangeParkBitrixContact(
        first_name="Olena",
        last_name="Shevchenko",
        phone="00 380 67 111 22 33",
        telegram_id="111",
        telegram_username="olena",
    )


def _history() -> ConversationHistory:
    timestamp = datetime(2026, 6, 13, 10, 0, 0)
    return ConversationHistory(
        messages=(
            ConversationHistoryMessage(
                sender_type="customer",
                message_text="Interested in a one-room apartment.",
                created_at=timestamp,
            ),
            ConversationHistoryMessage(
                sender_type="ai",
                message_text="What area do you prefer?",
                created_at=timestamp,
            ),
            ConversationHistoryMessage(
                sender_type="customer",
                message_text="About 40 square meters.",
                created_at=timestamp,
            ),
        )
    )


@pytest.mark.anyio
async def test_creates_new_bitrix_lead_when_phone_is_not_found():
    requests: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append((request.url.path, payload))
        if request.url.path.endswith("/crm.duplicate.findbycomm.json"):
            return httpx.Response(200, json={"result": []})
        if request.url.path.endswith("/crm.lead.add.json"):
            return httpx.Response(200, json={"result": 501})
        raise AssertionError(f"Unexpected method path: {request.url.path}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OrangeParkBitrixService(
            app_settings=_settings(),
            http_client=client,
        ).create_or_update_lead(contact=_contact(), history=_history())

    assert result is not None
    assert result.lead_id == "501"
    assert result.action == "create"
    assert [path.rsplit("/", 1)[-1] for path, _ in requests] == [
        "crm.duplicate.findbycomm.json",
        "crm.lead.add.json",
    ]
    fields = requests[1][1]["fields"]
    assert fields["TITLE"] == BITRIX_LEAD_TITLE
    assert fields["NAME"] == "Olena"
    assert fields["LAST_NAME"] == "Shevchenko"
    assert fields["PHONE"][0]["VALUE"] == "+380671112233"
    assert fields["SOURCE_ID"] == BITRIX_SOURCE_ID
    assert fields["SOURCE_DESCRIPTION"] == BITRIX_SOURCE_DESCRIPTION
    assert "Source: Telegram" in fields["COMMENTS"]
    assert "Telegram ID: 111" in fields["COMMENTS"]
    assert "Latest customer messages:" in fields["COMMENTS"]


@pytest.mark.anyio
async def test_updates_existing_bitrix_lead_found_by_phone_without_create():
    method_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        method_paths.append(request.url.path)
        if request.url.path.endswith("/crm.duplicate.findbycomm.json"):
            return httpx.Response(200, json={"result": {"LEAD": [701]}})
        if request.url.path.endswith("/crm.lead.update.json"):
            return httpx.Response(200, json={"result": True})
        raise AssertionError(f"Unexpected method path: {request.url.path}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = OrangeParkBitrixService(
            app_settings=_settings(),
            http_client=client,
        )
        first = await service.create_or_update_lead(
            contact=_contact(),
            history=_history(),
        )
        second = await service.create_or_update_lead(
            contact=_contact(),
            history=_history(),
        )

    assert first is not None and first.action == "update"
    assert second is not None and second.action == "update"
    assert first.lead_id == second.lead_id == "701"
    assert not any(path.endswith("/crm.lead.add.json") for path in method_paths)


@pytest.mark.anyio
async def test_phone_only_contact_creates_lead_with_safe_fallback_name():
    captured_fields: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if request.url.path.endswith("/crm.duplicate.findbycomm.json"):
            return httpx.Response(200, json={"result": []})
        if request.url.path.endswith("/crm.lead.add.json"):
            captured_fields.update(payload["fields"])
            return httpx.Response(200, json={"result": 801})
        raise AssertionError(f"Unexpected method path: {request.url.path}")

    contact = OrangeParkBitrixContact(
        first_name="Telegram contact",
        last_name=None,
        phone="+380671112233",
        telegram_id="111",
        telegram_username=None,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OrangeParkBitrixService(
            app_settings=_settings(),
            http_client=client,
        ).create_or_update_lead(contact=contact, history=_history())

    assert result is not None
    assert result.action == "create"
    assert captured_fields["NAME"] == "Telegram contact"
    assert captured_fields["LAST_NAME"] == ""


@pytest.mark.anyio
async def test_missing_webhook_configuration_disables_bitrix_safely():
    result = await OrangeParkBitrixService(
        app_settings=_settings(configured=False),
    ).create_or_update_lead(contact=_contact(), history=_history())

    assert result is None


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("+380 (67) 111-22-33", "+380671112233"),
        ("00380 67 111 22 33", "+380671112233"),
        ("380671112233", "+380671112233"),
    ],
)
def test_normalize_bitrix_phone(raw: str, normalized: str):
    assert normalize_bitrix_phone(raw) == normalized
