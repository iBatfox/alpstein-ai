import ast
from pathlib import Path

import pytest

from app.services.lead_signal_detection_service import LeadSignalDetectionService
from app.services.notification_policy_service import NotificationPolicyService


@pytest.fixture
def detection_service() -> LeadSignalDetectionService:
    return LeadSignalDetectionService()


def test_handoff_phrase_detected(detection_service: LeadSignalDetectionService):
    result = detection_service.detect(
        customer_message_text="Please let me speak to someone about my booking.",
    )

    assert result.handoff_requested is True
    assert "speak to someone" in result.matched_keywords
    assert "handoff_keyword:speak to someone" in result.reasons
    assert result.urgent_detected is False


def test_urgent_phrase_detected(detection_service: LeadSignalDetectionService):
    result = detection_service.detect(
        customer_message_text="This is urgent — I need help ASAP.",
    )

    assert result.urgent_detected is True
    assert result.matched_keywords == ["asap", "urgent"]
    assert result.reasons == ["urgent_keyword:asap", "urgent_keyword:urgent"]
    assert result.handoff_requested is False


def test_case_insensitive_matching(detection_service: LeadSignalDetectionService):
    result = detection_service.detect(
        customer_message_text="EMERGENCY: Call Me NOW!",
    )

    assert result.urgent_detected is True
    assert result.handoff_requested is True
    assert "emergency" in result.matched_keywords
    assert "call me" in result.matched_keywords
    assert "now" in result.matched_keywords


def test_no_false_positive_on_unrelated_text(
    detection_service: LeadSignalDetectionService,
):
    result = detection_service.detect(
        customer_message_text="I'd like a haircut next Tuesday at 2pm, thanks.",
    )

    assert result.urgent_detected is False
    assert result.handoff_requested is False
    assert result.matched_keywords == []
    assert result.reasons == []


def test_person_word_boundary_avoids_personal_substring(
    detection_service: LeadSignalDetectionService,
):
    result = detection_service.detect(
        customer_message_text="Looking for a personalized haircut package.",
    )

    assert result.handoff_requested is False
    assert "person" not in result.matched_keywords


def test_both_urgent_and_handoff_can_be_true(
    detection_service: LeadSignalDetectionService,
):
    result = detection_service.detect(
        customer_message_text="Urgent: I need a manager to call me immediately.",
    )

    assert result.urgent_detected is True
    assert result.handoff_requested is True
    assert result.matched_keywords == [
        "call me",
        "manager",
        "immediately",
        "urgent",
    ]
    assert result.reasons == [
        "handoff_keyword:call me",
        "handoff_keyword:manager",
        "urgent_keyword:immediately",
        "urgent_keyword:urgent",
    ]


def test_deterministic_output_feeds_notification_policy(
    detection_service: LeadSignalDetectionService,
):
    message = "Emergency — talk to someone now."
    first = detection_service.detect(customer_message_text=message)
    second = detection_service.detect(customer_message_text=message)

    assert first == second

    policy = NotificationPolicyService()
    decision = policy.decide(
        urgent_detected=first.urgent_detected,
        handoff_requested=first.handoff_requested,
        lead_created=True,
    )
    assert decision.notification_type == "urgent_lead"


def test_empty_message_returns_no_signals(
    detection_service: LeadSignalDetectionService,
):
    result = detection_service.detect(customer_message_text="   ")

    assert result.urgent_detected is False
    assert result.handoff_requested is False
    assert result.matched_keywords == []
    assert result.reasons == []


def test_module_has_no_db_or_provider_imports():
    service_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "lead_signal_detection_service.py"
    )
    source = service_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    forbidden = {"sqlalchemy", "openai", "httpx"}
    assert not imported.intersection(forbidden)
    assert "sqlalchemy" not in source
