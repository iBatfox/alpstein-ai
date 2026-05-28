"""E3.3c — deterministic adapter health status rules."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.adapter_health_policy import (
    ADAPTER_STATUS_DEGRADED,
    ADAPTER_STATUS_HEALTHY,
    ADAPTER_STATUS_INACTIVE,
    ADAPTER_STATUS_WARNING,
    REASON_DEAD_LETTER_PRESENT,
    REASON_ELEVATED_PENDING_DELIVERIES,
    REASON_ELEVATED_RETRIES,
    REASON_HIGH_FAILURE_RATE,
    REASON_MODERATE_FAILURE_RATE,
    REASON_NO_RECENT_ACTIVITY,
    REASON_STALE_PENDING_DELIVERIES,
    AdapterHealthMetrics,
    AdapterHealthThresholds,
    compute_delivery_failure_rate,
    evaluate_adapter_status,
    is_monitored_adapter,
)

DEFAULT_THRESHOLDS = AdapterHealthThresholds(
    min_sample=5,
    degraded_failure_rate=0.50,
    warning_failure_rate=0.25,
    retry_warning=10,
    pending_warning=5,
    pending_stale_min=3,
)


def _metrics(**overrides: int) -> AdapterHealthMetrics:
    base = {
        "adapter": "telegram",
        "recent_messages": 10,
        "delivery_success_count": 8,
        "delivery_failure_count": 2,
        "delivery_pending_count": 0,
        "retry_count": 0,
        "dead_letter_count": 0,
    }
    base.update(overrides)
    return AdapterHealthMetrics(**base)


def test_compute_delivery_failure_rate():
    assert compute_delivery_failure_rate(delivery_success_count=0, delivery_failure_count=0) is None
    assert compute_delivery_failure_rate(delivery_success_count=8, delivery_failure_count=2) == 0.2


def test_inactive_when_no_recent_messages():
    status, reasons, rate = evaluate_adapter_status(
        _metrics(recent_messages=0),
        DEFAULT_THRESHOLDS,
    )
    assert status == ADAPTER_STATUS_INACTIVE
    assert reasons == [REASON_NO_RECENT_ACTIVITY]
    assert rate == 0.2


def test_degraded_on_dead_letter():
    status, reasons, _ = evaluate_adapter_status(
        _metrics(dead_letter_count=1),
        DEFAULT_THRESHOLDS,
    )
    assert status == ADAPTER_STATUS_DEGRADED
    assert REASON_DEAD_LETTER_PRESENT in reasons


def test_degraded_on_high_failure_rate_with_min_sample():
    status, reasons, rate = evaluate_adapter_status(
        _metrics(
            recent_messages=10,
            delivery_success_count=4,
            delivery_failure_count=6,
        ),
        DEFAULT_THRESHOLDS,
    )
    assert status == ADAPTER_STATUS_DEGRADED
    assert REASON_HIGH_FAILURE_RATE in reasons
    assert rate == 0.6


def test_failure_rate_rules_do_not_apply_below_min_sample():
    status, reasons, _ = evaluate_adapter_status(
        _metrics(
            recent_messages=4,
            delivery_success_count=0,
            delivery_failure_count=4,
        ),
        DEFAULT_THRESHOLDS,
    )
    assert status == ADAPTER_STATUS_HEALTHY
    assert reasons == []


def test_degraded_on_stale_pending_without_success():
    status, reasons, _ = evaluate_adapter_status(
        _metrics(
            delivery_success_count=0,
            delivery_pending_count=3,
        ),
        DEFAULT_THRESHOLDS,
    )
    assert status == ADAPTER_STATUS_DEGRADED
    assert REASON_STALE_PENDING_DELIVERIES in reasons


def test_warning_on_elevated_retries():
    status, reasons, _ = evaluate_adapter_status(
        _metrics(retry_count=10),
        DEFAULT_THRESHOLDS,
    )
    assert status == ADAPTER_STATUS_WARNING
    assert REASON_ELEVATED_RETRIES in reasons


def test_warning_on_moderate_failure_rate():
    status, reasons, rate = evaluate_adapter_status(
        _metrics(
            recent_messages=10,
            delivery_success_count=6,
            delivery_failure_count=4,
        ),
        DEFAULT_THRESHOLDS,
    )
    assert status == ADAPTER_STATUS_WARNING
    assert REASON_MODERATE_FAILURE_RATE in reasons
    assert rate == 0.4


def test_warning_on_elevated_pending():
    status, reasons, _ = evaluate_adapter_status(
        _metrics(delivery_pending_count=5),
        DEFAULT_THRESHOLDS,
    )
    assert status == ADAPTER_STATUS_WARNING
    assert REASON_ELEVATED_PENDING_DELIVERIES in reasons


def test_healthy_baseline():
    status, reasons, rate = evaluate_adapter_status(_metrics(), DEFAULT_THRESHOLDS)
    assert status == ADAPTER_STATUS_HEALTHY
    assert reasons == []
    assert rate == 0.2


def test_degraded_precedence_over_warning():
    status, reasons, _ = evaluate_adapter_status(
        _metrics(
            dead_letter_count=1,
            retry_count=20,
            delivery_pending_count=6,
        ),
        DEFAULT_THRESHOLDS,
    )
    assert status == ADAPTER_STATUS_DEGRADED
    assert REASON_DEAD_LETTER_PRESENT in reasons
    assert REASON_ELEVATED_RETRIES not in reasons


@pytest.mark.parametrize(
    ("adapter", "expected"),
    [
        ("telegram", True),
        ("website_chat", True),
        ("whatsapp", False),
        ("test", False),
    ],
)
def test_is_monitored_adapter(adapter: str, expected: bool):
    assert is_monitored_adapter(adapter) is expected


def test_thresholds_from_settings():
    cfg = Settings(
        adapter_monitor_min_sample=7,
        adapter_monitor_degraded_failure_rate=0.40,
        adapter_monitor_warning_failure_rate=0.20,
        adapter_monitor_retry_warning=15,
        adapter_monitor_pending_warning=6,
        adapter_monitor_pending_stale_min=4,
    )
    status, reasons, _ = evaluate_adapter_status(
        _metrics(
            retry_count=12,
            delivery_success_count=10,
            delivery_failure_count=0,
        ),
        AdapterHealthThresholds(
            min_sample=cfg.adapter_monitor_min_sample,
            degraded_failure_rate=cfg.adapter_monitor_degraded_failure_rate,
            warning_failure_rate=cfg.adapter_monitor_warning_failure_rate,
            retry_warning=cfg.adapter_monitor_retry_warning,
            pending_warning=cfg.adapter_monitor_pending_warning,
            pending_stale_min=cfg.adapter_monitor_pending_stale_min,
        ),
    )
    assert status == ADAPTER_STATUS_HEALTHY
    assert reasons == []
