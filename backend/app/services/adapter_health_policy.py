"""Deterministic adapter health status rules (E3.3c)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.config import Settings, settings

AdapterStatus = Literal["healthy", "warning", "degraded", "inactive"]

ADAPTER_TELEGRAM = "telegram"
ADAPTER_WEBSITE_CHAT = "website_chat"

MONITORED_ADAPTERS: tuple[str, ...] = (ADAPTER_TELEGRAM, ADAPTER_WEBSITE_CHAT)

ADAPTER_STATUS_HEALTHY: AdapterStatus = "healthy"
ADAPTER_STATUS_WARNING: AdapterStatus = "warning"
ADAPTER_STATUS_DEGRADED: AdapterStatus = "degraded"
ADAPTER_STATUS_INACTIVE: AdapterStatus = "inactive"

REASON_NO_RECENT_ACTIVITY = "no_recent_activity"
REASON_DEAD_LETTER_PRESENT = "dead_letter_present"
REASON_HIGH_FAILURE_RATE = "high_failure_rate"
REASON_MODERATE_FAILURE_RATE = "moderate_failure_rate"
REASON_STALE_PENDING_DELIVERIES = "stale_pending_deliveries"
REASON_ELEVATED_RETRIES = "elevated_retries"
REASON_ELEVATED_PENDING_DELIVERIES = "elevated_pending_deliveries"


@dataclass(frozen=True)
class AdapterHealthThresholds:
    min_sample: int
    degraded_failure_rate: float
    warning_failure_rate: float
    retry_warning: int
    pending_warning: int
    pending_stale_min: int


@dataclass(frozen=True)
class AdapterHealthMetrics:
    adapter: str
    recent_messages: int
    delivery_success_count: int
    delivery_failure_count: int
    delivery_pending_count: int
    retry_count: int
    dead_letter_count: int


def adapter_health_thresholds(app_settings: Settings | None = None) -> AdapterHealthThresholds:
    cfg = app_settings or settings
    return AdapterHealthThresholds(
        min_sample=cfg.adapter_monitor_min_sample,
        degraded_failure_rate=cfg.adapter_monitor_degraded_failure_rate,
        warning_failure_rate=cfg.adapter_monitor_warning_failure_rate,
        retry_warning=cfg.adapter_monitor_retry_warning,
        pending_warning=cfg.adapter_monitor_pending_warning,
        pending_stale_min=cfg.adapter_monitor_pending_stale_min,
    )


def compute_delivery_failure_rate(
    *,
    delivery_success_count: int,
    delivery_failure_count: int,
) -> float | None:
    attempted = delivery_success_count + delivery_failure_count
    if attempted <= 0:
        return None
    return delivery_failure_count / attempted


def evaluate_adapter_status(
    metrics: AdapterHealthMetrics,
    thresholds: AdapterHealthThresholds | None = None,
) -> tuple[AdapterStatus, list[str], float | None]:
    """Return status, machine-readable reasons, and optional failure rate."""
    cfg = thresholds or adapter_health_thresholds()
    failure_rate = compute_delivery_failure_rate(
        delivery_success_count=metrics.delivery_success_count,
        delivery_failure_count=metrics.delivery_failure_count,
    )

    if metrics.recent_messages == 0:
        return ADAPTER_STATUS_INACTIVE, [REASON_NO_RECENT_ACTIVITY], failure_rate

    reasons: list[str] = []

    rate_rules_apply = metrics.recent_messages >= cfg.min_sample
    if metrics.dead_letter_count > 0:
        reasons.append(REASON_DEAD_LETTER_PRESENT)
    if (
        rate_rules_apply
        and failure_rate is not None
        and failure_rate >= cfg.degraded_failure_rate
    ):
        reasons.append(REASON_HIGH_FAILURE_RATE)
    if (
        metrics.delivery_pending_count >= cfg.pending_stale_min
        and metrics.delivery_success_count == 0
    ):
        reasons.append(REASON_STALE_PENDING_DELIVERIES)

    if reasons:
        return ADAPTER_STATUS_DEGRADED, reasons, failure_rate

    warning_reasons: list[str] = []
    if metrics.retry_count >= cfg.retry_warning:
        warning_reasons.append(REASON_ELEVATED_RETRIES)
    if (
        rate_rules_apply
        and failure_rate is not None
        and failure_rate >= cfg.warning_failure_rate
    ):
        warning_reasons.append(REASON_MODERATE_FAILURE_RATE)
    if metrics.delivery_pending_count >= cfg.pending_warning:
        warning_reasons.append(REASON_ELEVATED_PENDING_DELIVERIES)

    if warning_reasons:
        return ADAPTER_STATUS_WARNING, warning_reasons, failure_rate

    return ADAPTER_STATUS_HEALTHY, [], failure_rate


def is_monitored_adapter(adapter: str) -> bool:
    return adapter in MONITORED_ADAPTERS
