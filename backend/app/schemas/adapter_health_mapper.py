"""Map adapter health snapshots to API responses."""

from __future__ import annotations

from app.schemas.adapter_health import (
    AdapterDeliveryBreakdown,
    AdapterHealthResponse,
    IsolationSummaryResponse,
    PeerAdapterSummary,
)
from app.services.adapter_monitoring_service import AdapterHealthSnapshot
from app.services.ingress_isolation_policy import IsolationSummary


def isolation_summary_to_response(summary: IsolationSummary) -> IsolationSummaryResponse:
    return IsolationSummaryResponse(
        isolation_status=summary.isolation_status,  # type: ignore[arg-type]
        spread_risk=summary.spread_risk,
        affected_adapters=list(summary.affected_adapters),
        healthy_adapters=list(summary.healthy_adapters),
        inactive_adapters=list(summary.inactive_adapters),
        containment_notes=list(summary.containment_notes),
    )


def adapter_health_to_response(snapshot: AdapterHealthSnapshot) -> AdapterHealthResponse:
    breakdown = None
    if snapshot.breakdown is not None:
        breakdown = AdapterDeliveryBreakdown(
            delivery_by_status=snapshot.breakdown.get("delivery_by_status", {}),
        )
    peer = None
    if snapshot.peer_adapter is not None:
        peer = PeerAdapterSummary(
            adapter=snapshot.peer_adapter.adapter,
            status=snapshot.peer_adapter.status,  # type: ignore[arg-type]
            ingress_status=snapshot.peer_adapter.ingress_status,  # type: ignore[arg-type]
            delivery_status=snapshot.peer_adapter.delivery_status,  # type: ignore[arg-type]
            containment_status=snapshot.peer_adapter.containment_status,  # type: ignore[arg-type]
        )
    return AdapterHealthResponse(
        adapter=snapshot.adapter,
        status=snapshot.status,  # type: ignore[arg-type]
        status_reasons=list(snapshot.status_reasons),
        ingress_status=snapshot.ingress_status,  # type: ignore[arg-type]
        delivery_status=snapshot.delivery_status,  # type: ignore[arg-type]
        ingress_status_reasons=list(snapshot.ingress_status_reasons),
        delivery_status_reasons=list(snapshot.delivery_status_reasons),
        containment_status=snapshot.containment_status,  # type: ignore[arg-type]
        recent_messages=snapshot.recent_messages,
        ingress_failed_count=snapshot.ingress_failed_count,
        ingress_retry_count=snapshot.ingress_retry_count,
        ingress_dead_letter_count=snapshot.ingress_dead_letter_count,
        delivery_success_count=snapshot.delivery_success_count,
        delivery_failure_count=snapshot.delivery_failure_count,
        delivery_pending_count=snapshot.delivery_pending_count,
        retry_count=snapshot.retry_count,
        dead_letter_count=snapshot.dead_letter_count,
        rate_limit_violation_count=snapshot.rate_limit_violation_count,
        spam_decision_count=snapshot.spam_decision_count,
        spam_containment_count=snapshot.spam_containment_count,
        delivery_failure_rate=snapshot.delivery_failure_rate,
        last_activity_at=snapshot.last_activity_at,
        evaluated_at=snapshot.evaluated_at,
        breakdown=breakdown,
        peer_adapter=peer,
    )
