"""E3.4 — ingress failure isolation policy and containment."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.adapter_health_policy import (
    ADAPTER_STATUS_DEGRADED,
    ADAPTER_STATUS_HEALTHY,
    ADAPTER_STATUS_INACTIVE,
    ADAPTER_STATUS_WARNING,
)
from app.services.ingress_isolation_policy import (
    CONTAINMENT_CONTAINED,
    CONTAINMENT_NORMAL,
    CONTAINMENT_PEER_AT_RISK,
    CONTAINMENT_SHARED_AT_RISK,
    ISOLATION_AT_RISK,
    ISOLATION_INTACT,
    ISOLATION_UNKNOWN,
    REASON_INGRESS_FAILED_ELEVATED,
    REASON_INGRESS_INBOUND_DEAD_LETTER,
    AdapterIsolationView,
    IngressHealthMetrics,
    IngressHealthThresholds,
    build_isolation_summary,
    combine_adapter_status,
    compute_spread_risk,
    evaluate_containment_status,
    evaluate_delivery_status,
    evaluate_ingress_status,
    should_reject_ingress,
)

DEFAULT_INGRESS_THRESHOLDS = IngressHealthThresholds(
    failed_warning=3,
    failed_degraded=10,
    inbound_dl_degraded=1,
    inbound_retry_warning=10,
)


def _ingress_metrics(**overrides: int) -> IngressHealthMetrics:
    base = {
        "adapter": "telegram",
        "ingress_recent_messages": 10,
        "ingress_failed_count": 0,
        "ingress_retry_count": 0,
        "ingress_dead_letter_count": 0,
    }
    base.update(overrides)
    return IngressHealthMetrics(**base)


def _view(
    adapter: str,
    *,
    ingress_status: str = ADAPTER_STATUS_HEALTHY,
    delivery_status: str = ADAPTER_STATUS_HEALTHY,
    ingress_failed_count: int = 0,
    ingress_dead_letter_count: int = 0,
    ingress_reasons: list[str] | None = None,
    delivery_reasons: list[str] | None = None,
    containment_status: str = CONTAINMENT_NORMAL,
) -> AdapterIsolationView:
    status = combine_adapter_status(ingress_status, delivery_status)  # type: ignore[arg-type]
    return AdapterIsolationView(
        adapter=adapter,
        ingress_status=ingress_status,  # type: ignore[arg-type]
        delivery_status=delivery_status,  # type: ignore[arg-type]
        status=status,
        ingress_status_reasons=ingress_reasons or [],
        delivery_status_reasons=delivery_reasons or [],
        containment_status=containment_status,
        ingress_failed_count=ingress_failed_count,
        ingress_dead_letter_count=ingress_dead_letter_count,
    )


def test_combine_status_uses_worst_severity():
    assert combine_adapter_status(ADAPTER_STATUS_HEALTHY, ADAPTER_STATUS_WARNING) == ADAPTER_STATUS_WARNING
    assert combine_adapter_status(ADAPTER_STATUS_INACTIVE, ADAPTER_STATUS_DEGRADED) == ADAPTER_STATUS_DEGRADED
    assert combine_adapter_status(ADAPTER_STATUS_DEGRADED, ADAPTER_STATUS_HEALTHY) == ADAPTER_STATUS_DEGRADED


def test_ingress_and_delivery_status_independent():
    ingress_status, ingress_reasons = evaluate_ingress_status(
        _ingress_metrics(ingress_failed_count=4),
        DEFAULT_INGRESS_THRESHOLDS,
    )
    delivery_status, delivery_reasons, _ = evaluate_delivery_status(
        recent_messages=10,
        delivery_success_count=10,
        delivery_failure_count=0,
        delivery_pending_count=0,
        delivery_retry_count=0,
        delivery_dead_letter_count=0,
    )
    assert ingress_status == ADAPTER_STATUS_WARNING
    assert REASON_INGRESS_FAILED_ELEVATED in ingress_reasons
    assert delivery_status == ADAPTER_STATUS_HEALTHY
    assert delivery_reasons == []


def test_ingress_degraded_on_inbound_dead_letter():
    status, reasons = evaluate_ingress_status(
        _ingress_metrics(ingress_dead_letter_count=1),
        DEFAULT_INGRESS_THRESHOLDS,
    )
    assert status == ADAPTER_STATUS_DEGRADED
    assert REASON_INGRESS_INBOUND_DEAD_LETTER in reasons


def test_spread_risk_when_both_adapters_have_ingress_failures():
    views = [
        _view(
            "telegram",
            ingress_status=ADAPTER_STATUS_WARNING,
            ingress_failed_count=4,
            ingress_reasons=[REASON_INGRESS_FAILED_ELEVATED],
        ),
        _view(
            "website_chat",
            ingress_status=ADAPTER_STATUS_DEGRADED,
            ingress_failed_count=12,
            ingress_reasons=[REASON_INGRESS_FAILED_ELEVATED],
        ),
    ]
    assert compute_spread_risk(views) is True


def test_spread_risk_false_when_only_one_adapter_fails():
    views = [
        _view(
            "telegram",
            ingress_status=ADAPTER_STATUS_DEGRADED,
            ingress_failed_count=12,
        ),
        _view("website_chat", ingress_status=ADAPTER_STATUS_HEALTHY),
    ]
    assert compute_spread_risk(views) is False


def test_isolation_summary_intact_when_only_telegram_affected():
    telegram = _view(
        "telegram",
        ingress_status=ADAPTER_STATUS_DEGRADED,
        delivery_status=ADAPTER_STATUS_HEALTHY,
        ingress_failed_count=12,
        containment_status=CONTAINMENT_CONTAINED,
    )
    website = _view("website_chat", ingress_status=ADAPTER_STATUS_HEALTHY)
    summary = build_isolation_summary([telegram, website])
    assert summary.isolation_status == ISOLATION_INTACT
    assert summary.spread_risk is False
    assert summary.affected_adapters == ["telegram"]
    assert summary.healthy_adapters == ["website_chat"]


def test_isolation_summary_at_risk_on_spread():
    views = [
        _view(
            "telegram",
            ingress_status=ADAPTER_STATUS_WARNING,
            ingress_failed_count=4,
        ),
        _view(
            "website_chat",
            ingress_status=ADAPTER_STATUS_WARNING,
            ingress_failed_count=5,
        ),
    ]
    summary = build_isolation_summary(views)
    assert summary.spread_risk is True
    assert summary.isolation_status == ISOLATION_AT_RISK


def test_isolation_summary_unknown_when_all_inactive():
    views = [
        _view("telegram", ingress_status=ADAPTER_STATUS_INACTIVE),
        _view("website_chat", ingress_status=ADAPTER_STATUS_INACTIVE),
    ]
    summary = build_isolation_summary(views)
    assert summary.isolation_status == ISOLATION_UNKNOWN


def test_containment_contained_when_peer_healthy():
    status = evaluate_containment_status(
        adapter="telegram",
        adapter_status=ADAPTER_STATUS_DEGRADED,
        peer_status=ADAPTER_STATUS_HEALTHY,
        spread_risk=False,
    )
    assert status == CONTAINMENT_CONTAINED


def test_containment_peer_at_risk():
    status = evaluate_containment_status(
        adapter="website_chat",
        adapter_status=ADAPTER_STATUS_HEALTHY,
        peer_status=ADAPTER_STATUS_DEGRADED,
        spread_risk=False,
    )
    assert status == CONTAINMENT_PEER_AT_RISK


def test_containment_shared_at_risk():
    status = evaluate_containment_status(
        adapter="telegram",
        adapter_status=ADAPTER_STATUS_WARNING,
        peer_status=ADAPTER_STATUS_WARNING,
        spread_risk=True,
    )
    assert status == CONTAINMENT_SHARED_AT_RISK


def test_should_reject_ingress_disabled_by_default():
    assert (
        should_reject_ingress(
            channel="telegram",
            ingress_containment_enabled=False,
            ingress_dead_letter_count=2,
            containment_status=CONTAINMENT_CONTAINED,
        )
        is False
    )


def test_should_reject_ingress_when_enabled_and_contained():
    assert (
        should_reject_ingress(
            channel="telegram",
            ingress_containment_enabled=True,
            ingress_dead_letter_count=1,
            containment_status=CONTAINMENT_CONTAINED,
        )
        is True
    )


def test_should_not_reject_when_peer_containment_only():
    assert (
        should_reject_ingress(
            channel="website_chat",
            ingress_containment_enabled=True,
            ingress_dead_letter_count=0,
            containment_status=CONTAINMENT_PEER_AT_RISK,
        )
        is False
    )


def test_telegram_ingress_failure_does_not_change_website_delivery_evaluation():
    _, telegram_delivery_reasons, _ = evaluate_delivery_status(
        recent_messages=10,
        delivery_success_count=0,
        delivery_failure_count=0,
        delivery_pending_count=0,
        delivery_retry_count=0,
        delivery_dead_letter_count=0,
    )
    ingress_status, _ = evaluate_ingress_status(
        _ingress_metrics(adapter="telegram", ingress_failed_count=12),
        DEFAULT_INGRESS_THRESHOLDS,
    )
    website_delivery_status, website_delivery_reasons, _ = evaluate_delivery_status(
        recent_messages=10,
        delivery_success_count=9,
        delivery_failure_count=0,
        delivery_pending_count=0,
        delivery_retry_count=0,
        delivery_dead_letter_count=0,
    )
    assert ingress_status == ADAPTER_STATUS_DEGRADED
    assert telegram_delivery_reasons == []
    assert website_delivery_status == ADAPTER_STATUS_HEALTHY
    assert website_delivery_reasons == []


@pytest.mark.parametrize(
    "enabled",
    [False, True],
)
def test_ingress_containment_config_default_off(enabled: bool):
    cfg = Settings(ingress_containment_enabled=enabled)
    assert cfg.ingress_containment_enabled is enabled
    assert Settings().ingress_containment_enabled is False
