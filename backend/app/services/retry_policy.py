"""Platform retry limits and terminal error classification (E3.2)."""

from __future__ import annotations

from app.core.config import Settings, settings

DEFAULT_DELIVERY_MAX_RETRIES = 3
DEFAULT_INBOUND_PROVIDER_RETRY_MAX = 5
DEFAULT_TERMINAL_DELIVERY_ERROR_TYPES = frozenset(
    {
        "chat_not_found",
        "invalid_chat_id",
    }
)


def delivery_max_retries(app_settings: Settings | None = None) -> int:
    cfg = app_settings or settings
    raw = getattr(cfg, "delivery_max_retries", DEFAULT_DELIVERY_MAX_RETRIES)
    return max(1, int(raw))


def inbound_provider_retry_max(app_settings: Settings | None = None) -> int:
    cfg = app_settings or settings
    raw = getattr(cfg, "inbound_provider_retry_max", DEFAULT_INBOUND_PROVIDER_RETRY_MAX)
    return max(1, int(raw))


def terminal_delivery_error_types(app_settings: Settings | None = None) -> frozenset[str]:
    cfg = app_settings or settings
    raw = getattr(cfg, "delivery_terminal_error_types", None)
    if raw is None:
        return DEFAULT_TERMINAL_DELIVERY_ERROR_TYPES
    if isinstance(raw, frozenset):
        return raw
    if isinstance(raw, (list, tuple)):
        return frozenset(str(item).strip().lower() for item in raw if str(item).strip())
    text = str(raw).strip()
    if not text:
        return DEFAULT_TERMINAL_DELIVERY_ERROR_TYPES
    return frozenset(part.strip().lower() for part in text.split(",") if part.strip())


def is_terminal_delivery_error(error_type: str | None, app_settings: Settings | None = None) -> bool:
    if not error_type:
        return False
    return error_type.strip().lower() in terminal_delivery_error_types(app_settings)


def delivery_retries_exhausted(retry_count: int, app_settings: Settings | None = None) -> bool:
    return retry_count >= delivery_max_retries(app_settings)


def inbound_replays_exhausted(replay_count: int, app_settings: Settings | None = None) -> bool:
    return replay_count >= inbound_provider_retry_max(app_settings)
