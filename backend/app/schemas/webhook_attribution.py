"""Optional channel source / attribution fields on normalized webhook requests (ATTR-2)."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

STRING_FIELD_MAX_LENGTH = 128
LOCALE_FIELD_MAX_LENGTH = 64
URL_FIELD_MAX_LENGTH = 2048
UTM_FIELD_MAX_LENGTH = 256
USER_AGENT_MAX_LENGTH = 512
IP_ADDRESS_HASH_MAX_LENGTH = 128
EXTERNAL_CONVERSATION_ID_MAX_LENGTH = 512

EXTERNAL_CONVERSATION_ID_PREFIXES: tuple[str, ...] = (
    "tg:",
    "wa:",
    "web:",
    "ig:",
    "fb:",
    "email:",
    "sms:",
    "voice:",
    "api:",
)

_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"^sk-[a-zA-Z0-9]{8,}", re.IGNORECASE),
    re.compile(r"^pk-[a-zA-Z0-9]{8,}", re.IGNORECASE),
    re.compile(r"^xox[baprs]-", re.IGNORECASE),
)

_SECRET_SUBSTRING_MARKERS: tuple[str, ...] = (
    "api_key=",
    "apikey=",
    "secret=",
    "password=",
    "bot_token=",
    "access_token=",
    "refresh_token=",
    "webhook_secret=",
)


class WebhookAttributionModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


def _normalize_optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return value  # type: ignore[return-value]
    stripped = value.strip()
    return stripped if stripped else None


def _reject_secret_like_string(value: str, *, field_name: str) -> str:
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(value):
            raise ValueError(
                f"{field_name} must not contain API tokens or secrets"
            )
    lowered = value.lower()
    for marker in _SECRET_SUBSTRING_MARKERS:
        if marker in lowered:
            raise ValueError(
                f"{field_name} must not contain API tokens or secrets"
            )
    return value


def _optional_attribution_string(
    value: object,
    *,
    field_name: str,
) -> str | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    return _reject_secret_like_string(normalized, field_name=field_name)


class WebhookSource(WebhookAttributionModel):
    platform: str | None = Field(default=None, max_length=STRING_FIELD_MAX_LENGTH)
    account_id: str | None = Field(default=None, max_length=STRING_FIELD_MAX_LENGTH)
    account_name: str | None = Field(default=None, max_length=STRING_FIELD_MAX_LENGTH)
    locale: str | None = Field(default=None, max_length=LOCALE_FIELD_MAX_LENGTH)
    country: str | None = Field(default=None, max_length=LOCALE_FIELD_MAX_LENGTH)
    region: str | None = Field(default=None, max_length=STRING_FIELD_MAX_LENGTH)
    timezone: str | None = Field(default=None, max_length=LOCALE_FIELD_MAX_LENGTH)

    @field_validator(
        "platform",
        "account_id",
        "account_name",
        "locale",
        "country",
        "region",
        "timezone",
        mode="before",
    )
    @classmethod
    def normalize_and_scrub_strings(cls, value: object, info) -> str | None:
        return _optional_attribution_string(value, field_name=f"source.{info.field_name}")


class WebhookAttribution(WebhookAttributionModel):
    marketing_source: str | None = Field(
        default=None,
        max_length=STRING_FIELD_MAX_LENGTH,
    )
    campaign_id: str | None = Field(default=None, max_length=STRING_FIELD_MAX_LENGTH)
    landing_page_url: str | None = Field(default=None, max_length=URL_FIELD_MAX_LENGTH)
    referrer_url: str | None = Field(default=None, max_length=URL_FIELD_MAX_LENGTH)
    utm_source: str | None = Field(default=None, max_length=UTM_FIELD_MAX_LENGTH)
    utm_medium: str | None = Field(default=None, max_length=UTM_FIELD_MAX_LENGTH)
    utm_campaign: str | None = Field(default=None, max_length=UTM_FIELD_MAX_LENGTH)
    utm_content: str | None = Field(default=None, max_length=UTM_FIELD_MAX_LENGTH)
    utm_term: str | None = Field(default=None, max_length=UTM_FIELD_MAX_LENGTH)

    @field_validator(
        "marketing_source",
        "campaign_id",
        "landing_page_url",
        "referrer_url",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        mode="before",
    )
    @classmethod
    def normalize_and_scrub_strings(cls, value: object, info) -> str | None:
        return _optional_attribution_string(
            value,
            field_name=f"attribution.{info.field_name}",
        )


class WebhookMessageClient(WebhookAttributionModel):
    user_agent: str | None = Field(default=None, max_length=USER_AGENT_MAX_LENGTH)
    ip_address_hash: str | None = Field(
        default=None,
        max_length=IP_ADDRESS_HASH_MAX_LENGTH,
    )

    @field_validator("user_agent", "ip_address_hash", mode="before")
    @classmethod
    def normalize_and_scrub_strings(cls, value: object, info) -> str | None:
        return _optional_attribution_string(
            value,
            field_name=f"message.client.{info.field_name}",
        )


def validate_external_conversation_id(value: object) -> str | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    if not any(
        normalized.startswith(prefix) for prefix in EXTERNAL_CONVERSATION_ID_PREFIXES
    ):
        prefixes = ", ".join(EXTERNAL_CONVERSATION_ID_PREFIXES)
        raise ValueError(
            "external_conversation_id must start with a known channel prefix "
            f"({prefixes})"
        )
    return _reject_secret_like_string(
        normalized,
        field_name="message.external_conversation_id",
    )
