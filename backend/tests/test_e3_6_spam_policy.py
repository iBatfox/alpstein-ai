"""E3.6a — spam policy and fingerprint unit tests."""

from __future__ import annotations

from app.core.config import Settings
from app.models.spam_decision import DECISION_MARK_SUSPICIOUS, DECISION_THROTTLE
from app.services.spam_payload_fingerprint import compute_payload_hash, normalize_message_text
from app.services.spam_policy import (
    RULE_ADAPTER_FANOUT,
    RULE_CONVERSATION_BURST,
    RULE_PAYLOAD_REPEAT,
    RULE_REPLAY_STORM,
    RULE_RETRY_ABUSE,
    effective_decision,
    spam_policy_config,
)
from app.services.spam_protection_service import sanitize_spam_metadata


def test_feature_flags_default_off_and_production_safe():
    cfg = Settings()
    assert cfg.spam_protection_enabled is False
    assert cfg.spam_production_safe_mode is True


def test_payload_hash_is_stable_and_not_raw_text():
    text = "  hello   world  "
    assert normalize_message_text(text) == "hello world"
    digest = compute_payload_hash(text)
    assert digest == compute_payload_hash("hello world")
    assert "hello world" not in digest


def test_spam_policy_includes_approved_rules():
    policy = spam_policy_config(Settings())
    rule_ids = {rule.rule_id for rule in policy.rules}
    assert rule_ids == {
        RULE_PAYLOAD_REPEAT,
        RULE_CONVERSATION_BURST,
        RULE_ADAPTER_FANOUT,
        RULE_RETRY_ABUSE,
        RULE_REPLAY_STORM,
    }


def test_production_safe_mode_downgrades_blocking_actions():
    assert effective_decision(DECISION_THROTTLE, production_safe_mode=True) == DECISION_MARK_SUSPICIOUS
    assert effective_decision(DECISION_THROTTLE, production_safe_mode=False) == DECISION_THROTTLE


def test_sanitize_spam_metadata_strips_secrets_and_message_text():
    cleaned = sanitize_spam_metadata(
        {
            "rule_id": RULE_PAYLOAD_REPEAT,
            "message_text": "secret",
            "prompt": "hidden",
            "payload_hash_prefix": "abc123",
        }
    )
    assert cleaned == {"rule_id": RULE_PAYLOAD_REPEAT, "payload_hash_prefix": "abc123"}
