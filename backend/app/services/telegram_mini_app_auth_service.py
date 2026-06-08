from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl


class TelegramMiniAppAuthError(Exception):
    """Raised when Telegram Mini App initData cannot be trusted."""

    def __init__(self, code: str, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class TelegramMiniAppUser:
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None


@dataclass(frozen=True)
class TelegramMiniAppAuthContext:
    telegram_user: TelegramMiniAppUser
    auth_date: int
    query_id: str | None = None


class TelegramMiniAppAuthService:
    def validate_init_data(
        self,
        init_data: str | None,
        *,
        bot_token: str,
        max_age_seconds: int,
        now_seconds: int | None = None,
    ) -> TelegramMiniAppAuthContext:
        if not init_data or not init_data.strip():
            raise TelegramMiniAppAuthError(
                "TELEGRAM_INIT_DATA_REQUIRED",
                "Telegram initData is required",
            )
        clean_bot_token = bot_token.strip()
        if not clean_bot_token:
            raise TelegramMiniAppAuthError(
                "TELEGRAM_BOT_TOKEN_NOT_CONFIGURED",
                "Telegram bot token is not configured",
                status_code=503,
            )
        if max_age_seconds < 1:
            raise TelegramMiniAppAuthError(
                "TELEGRAM_INIT_DATA_MAX_AGE_INVALID",
                "Telegram initData max age must be positive",
                status_code=503,
            )

        try:
            pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
        except ValueError as exc:
            raise TelegramMiniAppAuthError(
                "TELEGRAM_INIT_DATA_MALFORMED",
                "Telegram initData is malformed",
            ) from exc
        values = dict(pairs)
        received_hash = values.get("hash", "")
        if not received_hash:
            raise TelegramMiniAppAuthError(
                "TELEGRAM_INIT_DATA_MALFORMED",
                "Telegram initData hash is missing",
            )

        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(pairs) if key != "hash"
        )
        if not data_check_string:
            raise TelegramMiniAppAuthError(
                "TELEGRAM_INIT_DATA_MALFORMED",
                "Telegram initData payload is empty",
            )

        secret_key = hmac.new(
            b"WebAppData",
            clean_bot_token.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            raise TelegramMiniAppAuthError(
                "TELEGRAM_INIT_DATA_INVALID_SIGNATURE",
                "Telegram initData signature is invalid",
            )

        auth_date = _parse_auth_date(values.get("auth_date"))
        current = int(time.time()) if now_seconds is None else now_seconds
        if auth_date > current:
            raise TelegramMiniAppAuthError(
                "TELEGRAM_INIT_DATA_INVALID_AUTH_DATE",
                "Telegram initData auth_date is in the future",
            )
        if current - auth_date > max_age_seconds:
            raise TelegramMiniAppAuthError(
                "TELEGRAM_INIT_DATA_EXPIRED",
                "Telegram initData is expired",
            )

        return TelegramMiniAppAuthContext(
            telegram_user=_parse_user(values.get("user")),
            auth_date=auth_date,
            query_id=values.get("query_id") or None,
        )


def _parse_auth_date(value: str | None) -> int:
    if value is None:
        raise TelegramMiniAppAuthError(
            "TELEGRAM_INIT_DATA_MALFORMED",
            "Telegram initData auth_date is missing",
        )
    try:
        return int(value)
    except ValueError as exc:
        raise TelegramMiniAppAuthError(
            "TELEGRAM_INIT_DATA_MALFORMED",
            "Telegram initData auth_date is invalid",
        ) from exc


def _parse_user(value: str | None) -> TelegramMiniAppUser:
    if not value:
        raise TelegramMiniAppAuthError(
            "TELEGRAM_INIT_DATA_MALFORMED",
            "Telegram initData user is missing",
        )
    try:
        raw_user: Any = json.loads(value)
    except json.JSONDecodeError as exc:
        raise TelegramMiniAppAuthError(
            "TELEGRAM_INIT_DATA_MALFORMED",
            "Telegram initData user is invalid JSON",
        ) from exc
    if not isinstance(raw_user, dict):
        raise TelegramMiniAppAuthError(
            "TELEGRAM_INIT_DATA_MALFORMED",
            "Telegram initData user must be an object",
        )
    user_id = raw_user.get("id")
    if not isinstance(user_id, int):
        raise TelegramMiniAppAuthError(
            "TELEGRAM_INIT_DATA_MALFORMED",
            "Telegram initData user id is missing",
        )
    return TelegramMiniAppUser(
        id=user_id,
        first_name=_optional_str(raw_user.get("first_name")),
        last_name=_optional_str(raw_user.get("last_name")),
        username=_optional_str(raw_user.get("username")),
        language_code=_optional_str(raw_user.get("language_code")),
        is_premium=(
            raw_user.get("is_premium")
            if isinstance(raw_user.get("is_premium"), bool)
            else None
        ),
    )


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
