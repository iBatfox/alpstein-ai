"""Map adapter health snapshots to API responses."""

from __future__ import annotations

from app.schemas.adapter_health import (
    AdapterDeliveryBreakdown,
    AdapterHealthResponse,
)
from app.services.adapter_monitoring_service import AdapterHealthSnapshot


def adapter_health_to_response(snapshot: AdapterHealthSnapshot) -> AdapterHealthResponse:
    breakdown = None
    if snapshot.breakdown is not None:
        breakdown = AdapterDeliveryBreakdown(
            delivery_by_status=snapshot.breakdown.get("delivery_by_status", {}),
        )
    return AdapterHealthResponse(
        adapter=snapshot.adapter,
        status=snapshot.status,  # type: ignore[arg-type]
        status_reasons=list(snapshot.status_reasons),
        recent_messages=snapshot.recent_messages,
        delivery_success_count=snapshot.delivery_success_count,
        delivery_failure_count=snapshot.delivery_failure_count,
        delivery_pending_count=snapshot.delivery_pending_count,
        retry_count=snapshot.retry_count,
        dead_letter_count=snapshot.dead_letter_count,
        delivery_failure_rate=snapshot.delivery_failure_rate,
        last_activity_at=snapshot.last_activity_at,
        evaluated_at=snapshot.evaluated_at,
        breakdown=breakdown,
    )
