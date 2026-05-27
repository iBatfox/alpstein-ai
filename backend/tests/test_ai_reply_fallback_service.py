import uuid
from dataclasses import fields

import pytest

from app.schemas.ai_configuration import TenantBehaviorConfig
from app.schemas.ai_fallback import FallbackDecision
from app.schemas.ai_reply import AiReplyResult
from app.services.ai_reply_fallback_service import (
    PLATFORM_DEFAULT_FALLBACK,
    REASON_AI_EMPTY_TEXT,
    REASON_AI_FAILURE,
    REASON_AI_SUCCESS,
    AiReplyFallbackService,
)


@pytest.fixture
def fallback_service() -> AiReplyFallbackService:
    return AiReplyFallbackService()


def _ai_reply(
    *,
    text: str | None,
    is_success: bool,
    error: str | None = None,
) -> AiReplyResult:
    return AiReplyResult(
        text=text,
        is_success=is_success,
        prompt_run_id=uuid.uuid4(),
        model="gpt-4o-mini",
        provider="openai",
        error=error,
    )


def test_success_reply_bypasses_fallback(fallback_service: AiReplyFallbackService):
    decision = fallback_service.decide(
        ai_reply=_ai_reply(text="Hello from AI", is_success=True),
        behavior=TenantBehaviorConfig(
            present=True,
            fallback_response="Tenant fallback",
            handoff_enabled=True,
        ),
    )

    assert decision.should_reply is False
    assert decision.fallback_text is None
    assert decision.should_handoff is False
    assert decision.reason == REASON_AI_SUCCESS


def test_ai_failure_uses_tenant_fallback_response(
    fallback_service: AiReplyFallbackService,
):
    decision = fallback_service.decide(
        ai_reply=_ai_reply(
            text=None,
            is_success=False,
            error="AI provider request timed out",
        ),
        behavior=TenantBehaviorConfig(
            present=True,
            fallback_response="Please call us at 044 000 00 00.",
            handoff_enabled=False,
        ),
    )

    assert decision.should_reply is True
    assert decision.fallback_text == "Please call us at 044 000 00 00."
    assert decision.should_handoff is False
    assert decision.reason == REASON_AI_FAILURE


def test_missing_tenant_fallback_uses_platform_default(
    fallback_service: AiReplyFallbackService,
):
    decision = fallback_service.decide(
        ai_reply=_ai_reply(text=None, is_success=False, error="provider error"),
        behavior=TenantBehaviorConfig.missing(),
    )

    assert decision.should_reply is True
    assert decision.fallback_text == PLATFORM_DEFAULT_FALLBACK
    assert decision.reason == REASON_AI_FAILURE


def test_handoff_enabled_produces_handoff_decision(
    fallback_service: AiReplyFallbackService,
):
    decision = fallback_service.decide(
        ai_reply=_ai_reply(text=None, is_success=False, error="timeout"),
        behavior=TenantBehaviorConfig(
            present=True,
            handoff_enabled=True,
        ),
    )

    assert decision.should_handoff is True


def test_handoff_disabled_suppresses_handoff_flag(
    fallback_service: AiReplyFallbackService,
):
    decision = fallback_service.decide(
        ai_reply=_ai_reply(text=None, is_success=False, error="timeout"),
        behavior=TenantBehaviorConfig(
            present=True,
            handoff_enabled=False,
        ),
    )

    assert decision.should_handoff is False


def test_empty_ai_text_treated_as_failure(fallback_service: AiReplyFallbackService):
    decision = fallback_service.decide(
        ai_reply=_ai_reply(text="   ", is_success=True),
        behavior=TenantBehaviorConfig(
            present=True,
            fallback_response="We will get back to you shortly.",
        ),
    )

    assert decision.should_reply is True
    assert decision.fallback_text == "We will get back to you shortly."
    assert decision.reason == REASON_AI_EMPTY_TEXT


def test_fallback_decision_dto_has_no_provider_or_prompt_fields():
    field_names = {field.name for field in fields(FallbackDecision)}
    forbidden = {
        "final_prompt",
        "provider",
        "model",
        "prompt_run_id",
        "system_prompt",
        "assembled_prompt",
    }
    assert field_names.isdisjoint(forbidden)
