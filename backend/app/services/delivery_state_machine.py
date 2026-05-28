"""Terminal-safe delivery status transitions (E3.1b)."""

from __future__ import annotations

from app.models.delivery_event import (
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_FAILED,
    DELIVERY_STATUS_PENDING,
    DELIVERY_STATUS_RETRYING,
    DELIVERY_STATUS_SKIPPED,
)

ALLOWED_DELIVERY_TRANSITIONS: dict[str, frozenset[str]] = {
    DELIVERY_STATUS_PENDING: frozenset(
        {
            DELIVERY_STATUS_DELIVERED,
            DELIVERY_STATUS_FAILED,
            DELIVERY_STATUS_SKIPPED,
            DELIVERY_STATUS_RETRYING,
        }
    ),
    DELIVERY_STATUS_RETRYING: frozenset(
        {
            DELIVERY_STATUS_DELIVERED,
            DELIVERY_STATUS_FAILED,
            DELIVERY_STATUS_RETRYING,
        }
    ),
    DELIVERY_STATUS_FAILED: frozenset({DELIVERY_STATUS_RETRYING}),
    DELIVERY_STATUS_DELIVERED: frozenset({DELIVERY_STATUS_DELIVERED}),
    DELIVERY_STATUS_SKIPPED: frozenset({DELIVERY_STATUS_SKIPPED}),
}


def is_delivery_transition_allowed(current_status: str, target_status: str) -> bool:
    if current_status == target_status:
        return True
    allowed = ALLOWED_DELIVERY_TRANSITIONS.get(current_status, frozenset())
    return target_status in allowed
