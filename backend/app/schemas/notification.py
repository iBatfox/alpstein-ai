"""Owner notification policy DTOs (T12.3)."""

from __future__ import annotations

from dataclasses import dataclass

NOTIFICATION_TYPE_URGENT_LEAD = "urgent_lead"
NOTIFICATION_TYPE_HUMAN_HANDOFF = "human_handoff"
NOTIFICATION_TYPE_AI_FAILURE = "ai_failure"
NOTIFICATION_TYPE_NEW_LEAD = "new_lead"

NOTIFICATION_PRIORITY_URGENT = "urgent"
NOTIFICATION_PRIORITY_HIGH = "high"
NOTIFICATION_PRIORITY_NORMAL = "normal"


@dataclass(frozen=True)
class NotificationDecision:
    """Whether and how to notify the business owner for a webhook event."""

    should_notify_owner: bool
    notification_type: str | None
    reason: str
    priority: str
