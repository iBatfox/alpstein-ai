"""Spam protection policy and rule definitions (E3.6a)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, settings
from app.models.spam_containment import ACTION_TEMPORARY_BLOCK, ACTION_THROTTLE
from app.models.spam_decision import (
    DECISION_IGNORE,
    DECISION_MARK_SUSPICIOUS,
    DECISION_TEMPORARY_BLOCK,
    DECISION_THROTTLE,
)
from app.models.spam_indicator_bucket import SCOPE_ADAPTER, SCOPE_CONVERSATION

RULE_PAYLOAD_REPEAT = "payload_repeat"
RULE_CONVERSATION_BURST = "conversation_burst"
RULE_ADAPTER_FANOUT = "adapter_fanout"
RULE_RETRY_ABUSE = "retry_abuse"
RULE_REPLAY_STORM = "replay_storm"

SPAM_RULE_IDS = frozenset(
    {
        RULE_PAYLOAD_REPEAT,
        RULE_CONVERSATION_BURST,
        RULE_ADAPTER_FANOUT,
        RULE_RETRY_ABUSE,
        RULE_REPLAY_STORM,
    }
)

MONITORED_SPAM_CHANNELS = frozenset({"telegram", "website_chat"})

SCOPE_SPECIFICITY_ORDER: tuple[str, ...] = (
    SCOPE_CONVERSATION,
    SCOPE_ADAPTER,
    "business",
)

BLOCKING_DECISIONS = frozenset({DECISION_THROTTLE, DECISION_TEMPORARY_BLOCK})


@dataclass(frozen=True)
class SpamRuleDefinition:
    rule_id: str
    scope_type: str
    window_seconds: int
    threshold: int
    configured_action: str
    enabled: bool = True


@dataclass(frozen=True)
class SpamPolicyConfig:
    production_safe_mode: bool
    throttle_ttl_seconds: int
    block_ttl_seconds: int
    rules: tuple[SpamRuleDefinition, ...]


def _rule_enabled(settings_obj: Settings, rule_id: str, default: bool = True) -> bool:
    field = f"spam_rule_{rule_id}_enabled"
    return bool(getattr(settings_obj, field, default))


def _rule_threshold(settings_obj: Settings, rule_id: str, default: int) -> int:
    field = f"spam_rule_{rule_id}_threshold"
    return int(getattr(settings_obj, field, default))


def _rule_window(settings_obj: Settings, rule_id: str, default: int) -> int:
    field = f"spam_rule_{rule_id}_window_seconds"
    return int(getattr(settings_obj, field, default))


def _rule_action(settings_obj: Settings, rule_id: str, default: str) -> str:
    field = f"spam_rule_{rule_id}_action"
    return str(getattr(settings_obj, field, default))


def spam_policy_config(app_settings: Settings | None = None) -> SpamPolicyConfig:
    cfg = app_settings or settings
    rules = (
        SpamRuleDefinition(
            rule_id=RULE_PAYLOAD_REPEAT,
            scope_type=SCOPE_CONVERSATION,
            window_seconds=_rule_window(cfg, RULE_PAYLOAD_REPEAT, 300),
            threshold=_rule_threshold(cfg, RULE_PAYLOAD_REPEAT, 5),
            configured_action=_rule_action(cfg, RULE_PAYLOAD_REPEAT, DECISION_THROTTLE),
            enabled=_rule_enabled(cfg, RULE_PAYLOAD_REPEAT),
        ),
        SpamRuleDefinition(
            rule_id=RULE_CONVERSATION_BURST,
            scope_type=SCOPE_CONVERSATION,
            window_seconds=_rule_window(cfg, RULE_CONVERSATION_BURST, 60),
            threshold=_rule_threshold(cfg, RULE_CONVERSATION_BURST, 15),
            configured_action=_rule_action(
                cfg, RULE_CONVERSATION_BURST, DECISION_MARK_SUSPICIOUS
            ),
            enabled=_rule_enabled(cfg, RULE_CONVERSATION_BURST),
        ),
        SpamRuleDefinition(
            rule_id=RULE_ADAPTER_FANOUT,
            scope_type=SCOPE_ADAPTER,
            window_seconds=_rule_window(cfg, RULE_ADAPTER_FANOUT, 300),
            threshold=_rule_threshold(cfg, RULE_ADAPTER_FANOUT, 50),
            configured_action=_rule_action(
                cfg, RULE_ADAPTER_FANOUT, DECISION_MARK_SUSPICIOUS
            ),
            enabled=_rule_enabled(cfg, RULE_ADAPTER_FANOUT),
        ),
        SpamRuleDefinition(
            rule_id=RULE_RETRY_ABUSE,
            scope_type=SCOPE_CONVERSATION,
            window_seconds=_rule_window(cfg, RULE_RETRY_ABUSE, 600),
            threshold=_rule_threshold(cfg, RULE_RETRY_ABUSE, 10),
            configured_action=_rule_action(cfg, RULE_RETRY_ABUSE, DECISION_THROTTLE),
            enabled=_rule_enabled(cfg, RULE_RETRY_ABUSE),
        ),
        SpamRuleDefinition(
            rule_id=RULE_REPLAY_STORM,
            scope_type=SCOPE_ADAPTER,
            window_seconds=_rule_window(cfg, RULE_REPLAY_STORM, 300),
            threshold=_rule_threshold(cfg, RULE_REPLAY_STORM, 20),
            configured_action=_rule_action(
                cfg, RULE_REPLAY_STORM, DECISION_TEMPORARY_BLOCK
            ),
            enabled=_rule_enabled(cfg, RULE_REPLAY_STORM),
        ),
    )
    return SpamPolicyConfig(
        production_safe_mode=cfg.spam_production_safe_mode,
        throttle_ttl_seconds=cfg.spam_containment_throttle_ttl_seconds,
        block_ttl_seconds=cfg.spam_containment_block_ttl_seconds,
        rules=rules,
    )


def effective_decision(
    configured_action: str,
    *,
    production_safe_mode: bool,
) -> str:
    if configured_action == DECISION_IGNORE:
        return DECISION_IGNORE
    if production_safe_mode and configured_action in BLOCKING_DECISIONS:
        return DECISION_MARK_SUSPICIOUS
    return configured_action


def containment_action_for_decision(decision: str) -> str | None:
    if decision == DECISION_THROTTLE:
        return ACTION_THROTTLE
    if decision == DECISION_TEMPORARY_BLOCK:
        return ACTION_TEMPORARY_BLOCK
    return None
