"""Orange Park Bitrix24 lead synchronization for captured Telegram contacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings, settings
from app.schemas.conversation_context import ConversationHistory

BITRIX_SOURCE_ID = "OTHER"
BITRIX_SOURCE_DESCRIPTION = "Telegram / Orange Park Telegram Bot"
BITRIX_LEAD_TITLE = "Telegram Lead — Orange Park"
BITRIX_COMMENTS_MAX_LENGTH = 4000
BITRIX_LATEST_CUSTOMER_MESSAGES_LIMIT = 5


class OrangeParkBitrixError(Exception):
    """Bitrix24 request failed without exposing the secret webhook URL."""


@dataclass(frozen=True)
class OrangeParkBitrixContact:
    first_name: str
    last_name: str | None
    phone: str
    telegram_id: str | None
    telegram_username: str | None


@dataclass(frozen=True)
class OrangeParkBitrixLeadResult:
    lead_id: str
    action: str
    timestamp: datetime


class OrangeParkBitrixService:
    def __init__(
        self,
        *,
        app_settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = app_settings or settings
        self._http_client = http_client

    def is_configured(self) -> bool:
        return bool(self._settings.orange_park_bitrix_webhook_url.strip())

    async def create_or_update_lead(
        self,
        *,
        contact: OrangeParkBitrixContact,
        history: ConversationHistory,
    ) -> OrangeParkBitrixLeadResult | None:
        if not self.is_configured():
            return None

        normalized_phone = normalize_bitrix_phone(contact.phone)
        fields = build_orange_park_bitrix_lead_fields(
            contact=OrangeParkBitrixContact(
                first_name=contact.first_name,
                last_name=contact.last_name,
                phone=normalized_phone,
                telegram_id=contact.telegram_id,
                telegram_username=contact.telegram_username,
            ),
            history=history,
        )
        lead_id = await self._find_lead_id_by_phone(normalized_phone)
        timestamp = datetime.now(UTC)

        if lead_id is not None:
            await self._call(
                "crm.lead.update",
                {"id": lead_id, "fields": fields},
            )
            return OrangeParkBitrixLeadResult(
                lead_id=lead_id,
                action="update",
                timestamp=timestamp,
            )

        result = await self._call("crm.lead.add", {"fields": fields})
        created_lead_id = _required_lead_id(result)
        return OrangeParkBitrixLeadResult(
            lead_id=created_lead_id,
            action="create",
            timestamp=timestamp,
        )

    async def get_profile(self) -> dict[str, Any]:
        result = await self._call("profile", {})
        if not isinstance(result, dict):
            raise OrangeParkBitrixError("Bitrix24 profile response is invalid")
        return result

    async def _find_lead_id_by_phone(self, phone: str) -> str | None:
        result = await self._call(
            "crm.duplicate.findbycomm",
            {
                "entity_type": "LEAD",
                "type": "PHONE",
                "values": [phone],
            },
        )
        if result == []:
            return None
        if not isinstance(result, dict):
            raise OrangeParkBitrixError("Bitrix24 duplicate search response is invalid")
        raw_ids = result.get("LEAD")
        if not isinstance(raw_ids, list) or not raw_ids:
            return None
        lead_id = str(raw_ids[0]).strip()
        return lead_id or None

    async def _call(self, method: str, payload: dict[str, Any]) -> Any:
        base_url = self._settings.orange_park_bitrix_webhook_url.strip()
        if not base_url:
            raise OrangeParkBitrixError("Bitrix24 is not configured")
        url = f"{base_url.rstrip('/')}/{method}.json"

        try:
            if self._http_client is not None:
                response = await self._http_client.post(url, json=payload)
            else:
                timeout = httpx.Timeout(
                    self._settings.orange_park_bitrix_timeout_seconds
                )
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise OrangeParkBitrixError("Bitrix24 request timed out") from exc
        except httpx.RequestError as exc:
            raise OrangeParkBitrixError("Bitrix24 network request failed") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise OrangeParkBitrixError("Bitrix24 returned invalid JSON") from exc

        if response.is_error:
            raise OrangeParkBitrixError(
                f"Bitrix24 request failed with HTTP {response.status_code}"
            )
        if not isinstance(body, dict):
            raise OrangeParkBitrixError("Bitrix24 response is invalid")
        if body.get("error"):
            error_code = str(body.get("error")).strip() or "UNKNOWN"
            raise OrangeParkBitrixError(f"Bitrix24 API error: {error_code}")
        if "result" not in body:
            raise OrangeParkBitrixError("Bitrix24 response is missing result")
        return body["result"]


def normalize_bitrix_phone(value: str) -> str:
    stripped = value.strip()
    digits = "".join(char for char in stripped if char.isdigit())
    if stripped.startswith("00"):
        digits = digits[2:]
    if len(digits) < 8 or len(digits) > 15:
        raise ValueError("phone must contain 8 to 15 digits")
    return f"+{digits}"


def build_orange_park_bitrix_lead_fields(
    *,
    contact: OrangeParkBitrixContact,
    history: ConversationHistory,
) -> dict[str, Any]:
    return {
        "TITLE": BITRIX_LEAD_TITLE,
        "NAME": contact.first_name,
        "LAST_NAME": contact.last_name or "",
        "PHONE": [
            {
                "VALUE": contact.phone,
                "VALUE_TYPE": "MOBILE",
            }
        ],
        "SOURCE_ID": BITRIX_SOURCE_ID,
        "SOURCE_DESCRIPTION": BITRIX_SOURCE_DESCRIPTION,
        "COMMENTS": build_orange_park_bitrix_comments(
            contact=contact,
            history=history,
        ),
    }


def build_orange_park_bitrix_comments(
    *,
    contact: OrangeParkBitrixContact,
    history: ConversationHistory,
) -> str:
    latest_customer_messages = [
        message.message_text.strip()
        for message in history.messages
        if message.sender_type == "customer"
        and message.message_text.strip()
        and message.message_text.strip() != "[telegram_contact_shared]"
    ][-BITRIX_LATEST_CUSTOMER_MESSAGES_LIMIT:]
    conversation_lines = [
        f"{message.sender_type}: {message.message_text.strip()}"
        for message in history.messages
        if message.message_text.strip()
        and message.message_text.strip() != "[telegram_contact_shared]"
    ]

    sections = [
        "Business: Orange Park",
        "Source: Telegram",
        "Handoff reason: shared Telegram contact",
        f"Telegram ID: {contact.telegram_id or 'not available'}",
        f"Telegram username: {contact.telegram_username or 'not available'}",
        "",
        "Conversation context:",
        "\n".join(conversation_lines) or "No prior conversation messages.",
        "",
        "Latest customer messages:",
        "\n".join(f"- {text}" for text in latest_customer_messages)
        or "No prior customer messages.",
    ]
    comments = "\n".join(sections)
    if len(comments) <= BITRIX_COMMENTS_MAX_LENGTH:
        return comments
    return comments[: BITRIX_COMMENTS_MAX_LENGTH - 3].rstrip() + "..."


def _required_lead_id(value: Any) -> str:
    lead_id = str(value).strip() if value is not None else ""
    if not lead_id:
        raise OrangeParkBitrixError("Bitrix24 create response is missing lead id")
    return lead_id
