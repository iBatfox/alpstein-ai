"""Ingress rate limit policy and scope definitions (E3.5a)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.config import Settings, settings
from app.models.rate_limit_bucket import (
    SCOPE_ADAPTER,
    SCOPE_BUSINESS,
    SCOPE_CONVERSATION,
    SCOPE_TENANT,
)

SCOPE_SPECIFICITY_ORDER: tuple[str, ...] = (
    SCOPE_CONVERSATION,
    SCOPE_ADAPTER,
    SCOPE_BUSINESS,
    SCOPE_TENANT,
)


@dataclass(frozen=True)
class RateLimitScopeDefinition:
    scope_type: str
    scope_key: str
    channel: str | None
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitPolicyConfig:
    window_seconds: int
    tenant_limit: int
    business_limit: int
    adapter_telegram_limit: int
    adapter_website_chat_limit: int
    conversation_limit: int


def rate_limit_policy_config(app_settings: Settings | None = None) -> RateLimitPolicyConfig:
    cfg = app_settings or settings
    return RateLimitPolicyConfig(
        window_seconds=cfg.rate_limit_window_seconds,
        tenant_limit=cfg.rate_limit_tenant_limit,
        business_limit=cfg.rate_limit_business_limit,
        adapter_telegram_limit=cfg.rate_limit_adapter_telegram_limit,
        adapter_website_chat_limit=cfg.rate_limit_adapter_website_chat_limit,
        conversation_limit=cfg.rate_limit_conversation_limit,
    )


def compute_window_start(*, now: datetime, window_seconds: int) -> datetime:
    if now.tzinfo is None:
        epoch = int(now.replace(tzinfo=timezone.utc).timestamp())
    else:
        epoch = int(now.timestamp())
    bucket_epoch = epoch - (epoch % window_seconds)
    return datetime.fromtimestamp(bucket_epoch, tz=timezone.utc).replace(tzinfo=None)


def retry_after_seconds(*, now: datetime, window_start: datetime, window_seconds: int) -> int:
    window_end = window_start + timedelta(seconds=window_seconds)
    remaining = int((window_end - now).total_seconds())
    return max(1, remaining)


def build_rate_limit_scopes(
    *,
    tenant_id: str,
    business_id: str,
    channel: str,
    conversation_id: str,
    policy: RateLimitPolicyConfig | None = None,
) -> list[RateLimitScopeDefinition]:
    cfg = policy or rate_limit_policy_config()
    adapter_limit = (
        cfg.adapter_telegram_limit
        if channel == "telegram"
        else cfg.adapter_website_chat_limit
    )
    return [
        RateLimitScopeDefinition(
            scope_type=SCOPE_TENANT,
            scope_key=tenant_id,
            channel=None,
            limit=cfg.tenant_limit,
            window_seconds=cfg.window_seconds,
        ),
        RateLimitScopeDefinition(
            scope_type=SCOPE_BUSINESS,
            scope_key=business_id,
            channel=None,
            limit=cfg.business_limit,
            window_seconds=cfg.window_seconds,
        ),
        RateLimitScopeDefinition(
            scope_type=SCOPE_ADAPTER,
            scope_key=f"{business_id}:{channel}",
            channel=channel,
            limit=adapter_limit,
            window_seconds=cfg.window_seconds,
        ),
        RateLimitScopeDefinition(
            scope_type=SCOPE_CONVERSATION,
            scope_key=conversation_id,
            channel=channel,
            limit=cfg.conversation_limit,
            window_seconds=cfg.window_seconds,
        ),
    ]


def pick_violation_scope(
    exceeded: list[tuple[RateLimitScopeDefinition, int]],
) -> tuple[RateLimitScopeDefinition, int]:
    by_type = {scope.scope_type: (scope, count) for scope, count in exceeded}
    for scope_type in SCOPE_SPECIFICITY_ORDER:
        if scope_type in by_type:
            return by_type[scope_type]
    return exceeded[0]
