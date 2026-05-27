import pytest

from app.schemas.notification import (
    NOTIFICATION_PRIORITY_HIGH,
    NOTIFICATION_PRIORITY_NORMAL,
    NOTIFICATION_PRIORITY_URGENT,
    NOTIFICATION_TYPE_AI_FAILURE,
    NOTIFICATION_TYPE_HUMAN_HANDOFF,
    NOTIFICATION_TYPE_NEW_LEAD,
    NOTIFICATION_TYPE_URGENT_LEAD,
)
from app.services.notification_policy_service import (
    REASON_AI_FAILED,
    REASON_DUPLICATE_WEBHOOK,
    REASON_HANDOFF_REQUESTED,
    REASON_LEAD_CREATED,
    REASON_LEAD_UPDATED_ONLY,
    REASON_URGENT_DETECTED,
    NotificationPolicyService,
)


@pytest.fixture
def policy_service() -> NotificationPolicyService:
    return NotificationPolicyService()


def test_duplicate_webhook_suppresses_notification(
    policy_service: NotificationPolicyService,
):
    decision = policy_service.decide(
        is_duplicate=True,
        lead_created=True,
        urgent_detected=True,
        ai_failed=True,
    )

    assert decision.should_notify_owner is False
    assert decision.notification_type is None
    assert decision.reason == REASON_DUPLICATE_WEBHOOK


def test_urgent_detected_overrides_other_notification_types(
    policy_service: NotificationPolicyService,
):
    decision = policy_service.decide(
        urgent_detected=True,
        handoff_requested=True,
        ai_failed=True,
        lead_created=True,
        lead_updated=True,
    )

    assert decision.should_notify_owner is True
    assert decision.notification_type == NOTIFICATION_TYPE_URGENT_LEAD
    assert decision.reason == REASON_URGENT_DETECTED
    assert decision.priority == NOTIFICATION_PRIORITY_URGENT


def test_handoff_beats_ai_failure_and_new_lead(
    policy_service: NotificationPolicyService,
):
    decision = policy_service.decide(
        handoff_requested=True,
        ai_failed=True,
        lead_created=True,
    )

    assert decision.should_notify_owner is True
    assert decision.notification_type == NOTIFICATION_TYPE_HUMAN_HANDOFF
    assert decision.reason == REASON_HANDOFF_REQUESTED
    assert decision.priority == NOTIFICATION_PRIORITY_HIGH


def test_ai_failure_notification(
    policy_service: NotificationPolicyService,
):
    decision = policy_service.decide(ai_failed=True, lead_created=True)

    assert decision.should_notify_owner is True
    assert decision.notification_type == NOTIFICATION_TYPE_AI_FAILURE
    assert decision.reason == REASON_AI_FAILED
    assert decision.priority == NOTIFICATION_PRIORITY_HIGH


def test_new_lead_notification(
    policy_service: NotificationPolicyService,
):
    decision = policy_service.decide(lead_created=True)

    assert decision.should_notify_owner is True
    assert decision.notification_type == NOTIFICATION_TYPE_NEW_LEAD
    assert decision.reason == REASON_LEAD_CREATED
    assert decision.priority == NOTIFICATION_PRIORITY_NORMAL


def test_lead_updated_only_does_not_notify(
    policy_service: NotificationPolicyService,
):
    decision = policy_service.decide(lead_updated=True)

    assert decision.should_notify_owner is False
    assert decision.notification_type is None
    assert decision.reason == REASON_LEAD_UPDATED_ONLY


@pytest.mark.parametrize(
    (
        "urgent_detected",
        "handoff_requested",
        "ai_failed",
        "lead_created",
        "expected_type",
        "expected_reason",
        "expected_priority",
    ),
    [
        (
            True,
            True,
            True,
            True,
            NOTIFICATION_TYPE_URGENT_LEAD,
            REASON_URGENT_DETECTED,
            NOTIFICATION_PRIORITY_URGENT,
        ),
        (
            False,
            True,
            True,
            True,
            NOTIFICATION_TYPE_HUMAN_HANDOFF,
            REASON_HANDOFF_REQUESTED,
            NOTIFICATION_PRIORITY_HIGH,
        ),
        (
            False,
            False,
            True,
            True,
            NOTIFICATION_TYPE_AI_FAILURE,
            REASON_AI_FAILED,
            NOTIFICATION_PRIORITY_HIGH,
        ),
        (
            False,
            False,
            False,
            True,
            NOTIFICATION_TYPE_NEW_LEAD,
            REASON_LEAD_CREATED,
            NOTIFICATION_PRIORITY_NORMAL,
        ),
    ],
)
def test_deterministic_priority_resolution(
    policy_service: NotificationPolicyService,
    urgent_detected: bool,
    handoff_requested: bool,
    ai_failed: bool,
    lead_created: bool,
    expected_type: str,
    expected_reason: str,
    expected_priority: str,
):
    decision = policy_service.decide(
        urgent_detected=urgent_detected,
        handoff_requested=handoff_requested,
        ai_failed=ai_failed,
        lead_created=lead_created,
    )

    assert decision.should_notify_owner is True
    assert decision.notification_type == expected_type
    assert decision.reason == expected_reason
    assert decision.priority == expected_priority
