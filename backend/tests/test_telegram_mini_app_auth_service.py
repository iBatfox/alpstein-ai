import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.services.telegram_mini_app_auth_service import (
    TelegramMiniAppAuthError,
    TelegramMiniAppAuthService,
)

BOT_TOKEN = "123456:test-token"
NOW = 1_782_000_000


def signed_init_data(*, auth_date: int = NOW, bot_token: str = BOT_TOKEN) -> str:
    pairs = {
        "auth_date": str(auth_date),
        "query_id": "query-1",
        "user": json.dumps(
            {
                "id": 424242,
                "first_name": "Ada",
                "last_name": "Lovelace",
                "username": "ada",
                "language_code": "en",
            },
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    pairs["hash"] = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(pairs)


def test_valid_init_data_is_accepted():
    context = TelegramMiniAppAuthService().validate_init_data(
        signed_init_data(),
        bot_token=BOT_TOKEN,
        max_age_seconds=60,
        now_seconds=NOW,
    )

    assert context.telegram_user.id == 424242
    assert context.telegram_user.username == "ada"
    assert context.auth_date == NOW
    assert context.query_id == "query-1"


def test_invalid_signature_is_rejected():
    with pytest.raises(TelegramMiniAppAuthError) as exc_info:
        TelegramMiniAppAuthService().validate_init_data(
            signed_init_data(bot_token="wrong-token"),
            bot_token=BOT_TOKEN,
            max_age_seconds=60,
            now_seconds=NOW,
        )

    assert exc_info.value.code == "TELEGRAM_INIT_DATA_INVALID_SIGNATURE"


def test_expired_init_data_is_rejected():
    with pytest.raises(TelegramMiniAppAuthError) as exc_info:
        TelegramMiniAppAuthService().validate_init_data(
            signed_init_data(auth_date=NOW - 61),
            bot_token=BOT_TOKEN,
            max_age_seconds=60,
            now_seconds=NOW,
        )

    assert exc_info.value.code == "TELEGRAM_INIT_DATA_EXPIRED"


def test_missing_init_data_is_rejected():
    with pytest.raises(TelegramMiniAppAuthError) as exc_info:
        TelegramMiniAppAuthService().validate_init_data(
            "",
            bot_token=BOT_TOKEN,
            max_age_seconds=60,
            now_seconds=NOW,
        )

    assert exc_info.value.code == "TELEGRAM_INIT_DATA_REQUIRED"
