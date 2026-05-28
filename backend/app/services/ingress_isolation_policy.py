"""Ingress failure isolation and containment rules (E3.4a/c)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, settings
from app.services.adapter_health_policy import (
    ADAPTER_STATUS_DEGRADED,
    ADAPTER_STATUS_HEALTHY,
    ADAPTER_STATUS_INACTIVE,
    ADAPTER_STATUS_WARNING,
    AdapterStatus,
    AdapterHealthMetrics,
    AdapterHealthThresholds,
    adapter_health_thresholds,
    compute_delivery_failure_rate,
    evaluate_adapter_status,
)

CONTAINMENT_NORMAL = "normal"
CONTAINMENT_CONTAINED = "contained"
CONTAINMENT_PEER_AT_RISK = "peer_at_risk"
CONTAINMENT_SHARED_AT_RISK = "shared_at_risk"

ISOLATION_INTACT = "intact"
ISOLATION_AT_RISK = "at_risk"
ISOLATION_UNKNOWN = "unknown"

REASON_INGRESS_NO_ACTIVITY = "ingress_no_recent_activity"
REASON_INGRESS_FAILED_ELEVATED = "ingress_failed_elevated"
REASON_INGRESS_FAILED_HIGH = "ingress_failed_high"
REASON_INGRESS_INBOUND_DEAD_LETTER = "ingress_inbound_dead_letter"
REASON_INGRESS_INBOUND_RETRIES = "ingress_inbound_retries_elevated"

NOTE_CONTAINED_ADAPTER = "failure_contained_to_adapter"
NOTE_PEER_HEALTHY = "peer_adapter_unaffected"
NOTE_SPREAD_RISK = "multiple_adapters_show_ingress_failures"
NOTE_BOTH_INACTIVE = "all_adapters_inactive_in_window"


@dataclass(frozen=True)
class IngressHealthThresholds:
    failed_warning: int
    failed_degraded: int
    inbound_dl_degraded: int
    inbound_retry_warning: int


@dataclass(frozen=True)
class IngressHealthMetrics:
    adapter: str
    ingress_recent_messages: int
    ingress_failed_count: int
    ingress_retry_count: int
    ingress_dead_letter_count: int


@dataclass(frozen=True)
class AdapterIsolationView:
    adapter: str
    ingress_status: AdapterStatus
    delivery_status: AdapterStatus
    status: AdapterStatus
    ingress_status_reasons: list[str]
    delivery_status_reasons: list[str]
    containment_status: str
    ingress_failed_count: int
    ingress_dead_letter_count: int


@dataclass(frozen=True)
class IsolationSummary:
    isolation_status: str
    spread_risk: bool
    affected_adapters: list[str]
    healthy_adapters: list[str]
    inactive_adapters: list[str]
    containment_notes: list[str]


STATUS_SEVERITY: dict[str, int] = {
    ADAPTER_STATUS_INACTIVE: 0,
    ADAPTER_STATUS_HEALTHY: 1,
    ADAPTER_STATUS_WARNING: 2,
    ADAPTER_STATUS_DEGRADED: 3,
}


def ingress_health_thresholds(app_settings: Settings | None = None) -> IngressHealthThresholds:
    cfg = app_settings or settings
    return IngressHealthThresholds(
        failed_warning=cfg.ingress_monitor_failed_warning,
        failed_degraded=cfg.ingress_monitor_failed_degraded,
        inbound_dl_degraded=cfg.ingress_monitor_inbound_dl_degraded,
        inbound_retry_warning=cfg.adapter_monitor_retry_warning,
    )


def combine_adapter_status(
    ingress_status: AdapterStatus,
    delivery_status: AdapterStatus,
) -> AdapterStatus:
    if STATUS_SEVERITY[ingress_status] >= STATUS_SEVERITY[delivery_status]:
        return ingress_status
    return delivery_status


def evaluate_ingress_status(
    metrics: IngressHealthMetrics,
    thresholds: IngressHealthThresholds | None = None,
) -> tuple[AdapterStatus, list[str]]:
    cfg = thresholds or ingress_health_thresholds()
    if metrics.ingress_recent_messages == 0:
        return ADAPTER_STATUS_INACTIVE, [REASON_INGRESS_NO_ACTIVITY]

    reasons: list[str] = []
    if metrics.ingress_dead_letter_count >= cfg.inbound_dl_degraded:
        reasons.append(REASON_INGRESS_INBOUND_DEAD_LETTER)
    if metrics.ingress_failed_count >= cfg.failed_degraded:
        reasons.append(REASON_INGRESS_FAILED_HIGH)
    if reasons:
        return ADAPTER_STATUS_DEGRADED, reasons

    warning_reasons: list[str] = []
    if metrics.ingress_failed_count >= cfg.failed_warning:
        warning_reasons.append(REASON_INGRESS_FAILED_ELEVATED)
    if metrics.ingress_retry_count >= cfg.inbound_retry_warning:
        warning_reasons.append(REASON_INGRESS_INBOUND_RETRIES)
    if warning_reasons:
        return ADAPTER_STATUS_WARNING, warning_reasons

    return ADAPTER_STATUS_HEALTHY, []


def evaluate_delivery_status(
    *,
    recent_messages: int,
    delivery_success_count: int,
    delivery_failure_count: int,
    delivery_pending_count: int,
    delivery_retry_count: int,
    delivery_dead_letter_count: int,
    thresholds: AdapterHealthThresholds | None = None,
) -> tuple[AdapterStatus, list[str], float | None]:
    delivery_activity = (
        delivery_success_count
        + delivery_failure_count
        + delivery_pending_count
    )
    if delivery_activity == 0:
        return ADAPTER_STATUS_HEALTHY, [], None

    metrics = AdapterHealthMetrics(
        adapter="",
        recent_messages=max(recent_messages, 1),
        delivery_success_count=delivery_success_count,
        delivery_failure_count=delivery_failure_count,
        delivery_pending_count=delivery_pending_count,
        retry_count=delivery_retry_count,
        dead_letter_count=delivery_dead_letter_count,
    )
    status, reasons, rate = evaluate_adapter_status(metrics, thresholds)
    if status == ADAPTER_STATUS_INACTIVE:
        return ADAPTER_STATUS_HEALTHY, [], rate
    return status, reasons, rate


def evaluate_containment_status(
    *,
    adapter: str,
    adapter_status: AdapterStatus,
    peer_status: AdapterStatus | None,
    spread_risk: bool,
) -> str:
    if spread_risk:
        return CONTAINMENT_SHARED_AT_RISK
    if peer_status is None:
        return CONTAINMENT_NORMAL
    adapter_stressed = adapter_status in (ADAPTER_STATUS_WARNING, ADAPTER_STATUS_DEGRADED)
    peer_stressed = peer_status in (ADAPTER_STATUS_WARNING, ADAPTER_STATUS_DEGRADED)
    peer_ok = peer_status in (ADAPTER_STATUS_HEALTHY, ADAPTER_STATUS_INACTIVE)
    if adapter_stressed and peer_ok:
        return CONTAINMENT_CONTAINED
    if adapter_status in (ADAPTER_STATUS_HEALTHY, ADAPTER_STATUS_INACTIVE) and peer_stressed:
        return CONTAINMENT_PEER_AT_RISK
    return CONTAINMENT_NORMAL


def build_isolation_summary(
    views: list[AdapterIsolationView],
) -> IsolationSummary:
    if not views:
        return IsolationSummary(
            isolation_status=ISOLATION_UNKNOWN,
            spread_risk=False,
            affected_adapters=[],
            healthy_adapters=[],
            inactive_adapters=[],
            containment_notes=[NOTE_BOTH_INACTIVE],
        )

    spread_risk = compute_spread_risk(views)
    affected = [
        v.adapter
        for v in views
        if v.status in (ADAPTER_STATUS_WARNING, ADAPTER_STATUS_DEGRADED)
    ]
    healthy = [v.adapter for v in views if v.status == ADAPTER_STATUS_HEALTHY]
    inactive = [v.adapter for v in views if v.status == ADAPTER_STATUS_INACTIVE]

    notes: list[str] = []
    if spread_risk:
        notes.append(NOTE_SPREAD_RISK)
    if any(v.containment_status == CONTAINMENT_CONTAINED for v in views):
        notes.append(NOTE_CONTAINED_ADAPTER)
        notes.append(NOTE_PEER_HEALTHY)
    if len(inactive) == len(views) or all(
        view.ingress_status == ADAPTER_STATUS_INACTIVE for view in views
    ):
        isolation_status = ISOLATION_UNKNOWN
        if NOTE_BOTH_INACTIVE not in notes:
            notes.append(NOTE_BOTH_INACTIVE)
    elif spread_risk or len(affected) >= 2:
        isolation_status = ISOLATION_AT_RISK
    else:
        isolation_status = ISOLATION_INTACT

    return IsolationSummary(
        isolation_status=isolation_status,
        spread_risk=spread_risk,
        affected_adapters=sorted(affected),
        healthy_adapters=sorted(healthy),
        inactive_adapters=sorted(inactive),
        containment_notes=sorted(set(notes)),
    )


def compute_spread_risk(views: list[AdapterIsolationView]) -> bool:
    ingress_failures = [
        view
        for view in views
        if view.ingress_status in (ADAPTER_STATUS_WARNING, ADAPTER_STATUS_DEGRADED)
        and view.ingress_failed_count > 0
    ]
    return len(ingress_failures) >= 2


def should_reject_ingress(
    *,
    channel: str,
    ingress_containment_enabled: bool,
    ingress_dead_letter_count: int,
    containment_status: str,
) -> bool:
    if not ingress_containment_enabled:
        return False
    if ingress_dead_letter_count <= 0:
        return False
    if containment_status != CONTAINMENT_CONTAINED:
        return False
    return True
