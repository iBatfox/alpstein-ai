"""E3.5a — rate limit policy unit tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.config import Settings
from app.models.rate_limit_bucket import (
    SCOPE_ADAPTER,
    SCOPE_BUSINESS,
    SCOPE_CONVERSATION,
    SCOPE_TENANT,
)
from app.services.rate_limit_policy import (
    build_rate_limit_scopes,
    compute_window_start,
    pick_violation_scope,
    rate_limit_policy_config,
    retry_after_seconds,
)
from app.services.rate_limit_service import sanitize_violation_metadata


def test_rate_limit_policy_defaults():
    cfg = rate_limit_policy_config(
        Settings(
            rate_limit_window_seconds=60,
            rate_limit_tenant_limit=1000,
            rate_limit_business_limit=300,
            rate_limit_adapter_telegram_limit=120,
            rate_limit_adapter_website_chat_limit=120,
            rate_limit_conversation_limit=30,
        )
    )
    assert cfg.window_seconds == 60
    assert cfg.tenant_limit == 1000
    assert cfg.business_limit == 300
    assert cfg.conversation_limit == 30


def test_feature_flag_default_off():
    assert Settings().rate_limit_enabled is False


def test_build_scopes_adapter_keys_differ_by_channel():
    tenant_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())

    telegram = build_rate_limit_scopes(
        tenant_id=tenant_id,
        business_id=business_id,
        channel="telegram",
        conversation_id=conversation_id,
    )
    website = build_rate_limit_scopes(
        tenant_id=tenant_id,
        business_id=business_id,
        channel="website_chat",
        conversation_id=conversation_id,
    )

    tg_adapter = next(s for s in telegram if s.scope_type == SCOPE_ADAPTER)
    web_adapter = next(s for s in website if s.scope_type == SCOPE_ADAPTER)
    assert tg_adapter.scope_key != web_adapter.scope_key
    assert tg_adapter.scope_key.endswith(":telegram")
    assert web_adapter.scope_key.endswith(":website_chat")

    tg_business = next(s for s in telegram if s.scope_type == SCOPE_BUSINESS)
    web_business = next(s for s in website if s.scope_type == SCOPE_BUSINESS)
    assert tg_business.scope_key == web_business.scope_key == business_id


def test_fixed_window_bucket_alignment():
    now = datetime(2026, 5, 28, 12, 0, 45, tzinfo=timezone.utc).replace(tzinfo=None)
    start = compute_window_start(now=now, window_seconds=60)
    assert start == datetime(2026, 5, 28, 12, 0, 0)


def test_retry_after_seconds_minimum_one():
    now = datetime(2026, 5, 28, 12, 0, 59)
    start = datetime(2026, 5, 28, 12, 0, 0)
    assert retry_after_seconds(now=now, window_start=start, window_seconds=60) == 1


def test_pick_violation_scope_prefers_conversation():
    tenant_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    scopes = build_rate_limit_scopes(
        tenant_id=tenant_id,
        business_id=business_id,
        channel="telegram",
        conversation_id=conversation_id,
    )
    exceeded = [(scopes[3], 31), (scopes[0], 1001)]
    picked, count = pick_violation_scope(exceeded)
    assert picked.scope_type == SCOPE_CONVERSATION
    assert count == 31


def test_sanitize_violation_metadata_strips_secrets():
    cleaned = sanitize_violation_metadata(
        {
            "scope_type": SCOPE_TENANT,
            "message_text": "secret message",
            "limit": 30,
        }
    )
    assert cleaned == {"scope_type": SCOPE_TENANT, "limit": 30}
