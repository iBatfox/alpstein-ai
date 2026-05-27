"""Owner notification decision policy for webhook events (T12.3)."""

from __future__ import annotations

from app.schemas.notification import (
    NOTIFICATION_PRIORITY_HIGH,
    NOTIFICATION_PRIORITY_NORMAL,
    NOTIFICATION_PRIORITY_URGENT,
    NOTIFICATION_TYPE_AI_FAILURE,
    NOTIFICATION_TYPE_HUMAN_HANDOFF,
    NOTIFICATION_TYPE_NEW_LEAD,
    NOTIFICATION_TYPE_URGENT_LEAD,
    NotificationDecision,
)

REASON_DUPLICATE_WEBHOOK = "duplicate_webhook"
REASON_URGENT_DETECTED = "urgent_detected"
REASON_HANDOFF_REQUESTED = "handoff_requested"
REASON_AI_FAILED = "ai_failed"
REASON_LEAD_CREATED = "lead_created"
REASON_LEAD_UPDATED_ONLY = "lead_updated_only"
REASON_NO_NOTIFICATION = "no_notification"


class NotificationPolicyService:
    def decide(
        self,
        *,
        lead_created: bool = False,
        lead_updated: bool = False,
        ai_failed: bool = False,
        handoff_requested: bool = False,
        urgent_detected: bool = False,
        is_duplicate: bool = False,
    ) -> NotificationDecision:
        if is_duplicate:
            return NotificationDecision(
                should_notify_owner=False,
                notification_type=None,
                reason=REASON_DUPLICATE_WEBHOOK,
                priority=NOTIFICATION_PRIORITY_NORMAL,
            )

        if urgent_detected:
            return _notify(
                notification_type=NOTIFICATION_TYPE_URGENT_LEAD,
                reason=REASON_URGENT_DETECTED,
                priority=NOTIFICATION_PRIORITY_URGENT,
            )

        if handoff_requested:
            return _notify(
                notification_type=NOTIFICATION_TYPE_HUMAN_HANDOFF,
                reason=REASON_HANDOFF_REQUESTED,
                priority=NOTIFICATION_PRIORITY_HIGH,
            )

        if ai_failed:
            return _notify(
                notification_type=NOTIFICATION_TYPE_AI_FAILURE,
                reason=REASON_AI_FAILED,
                priority=NOTIFICATION_PRIORITY_HIGH,
            )

        if lead_created:
            return _notify(
                notification_type=NOTIFICATION_TYPE_NEW_LEAD,
                reason=REASON_LEAD_CREATED,
                priority=NOTIFICATION_PRIORITY_NORMAL,
            )

        if lead_updated:
            return NotificationDecision(
                should_notify_owner=False,
                notification_type=None,
                reason=REASON_LEAD_UPDATED_ONLY,
                priority=NOTIFICATION_PRIORITY_NORMAL,
            )

        return NotificationDecision(
            should_notify_owner=False,
            notification_type=None,
            reason=REASON_NO_NOTIFICATION,
            priority=NOTIFICATION_PRIORITY_NORMAL,
        )


def _notify(
    *,
    notification_type: str,
    reason: str,
    priority: str,
) -> NotificationDecision:
    return NotificationDecision(
        should_notify_owner=True,
        notification_type=notification_type,
        reason=reason,
        priority=priority,
    )
