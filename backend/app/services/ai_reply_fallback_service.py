"""Resolve customer-facing fallback text when AI replies fail (T11.12)."""

from __future__ import annotations

from app.schemas.ai_configuration import TenantBehaviorConfig
from app.schemas.ai_fallback import FallbackDecision
from app.schemas.ai_reply import AiReplyResult

PLATFORM_DEFAULT_FALLBACK = (
    "Sorry, something went wrong. A team member will contact you soon."
)

REASON_AI_SUCCESS = "ai_success"
REASON_AI_FAILURE = "ai_failure"
REASON_AI_EMPTY_TEXT = "ai_empty_text"


class AiReplyFallbackService:
    def decide(
        self,
        *,
        ai_reply: AiReplyResult,
        behavior: TenantBehaviorConfig,
        channel: str | None = None,
    ) -> FallbackDecision:
        del channel  # reserved for future channel-specific policy

        if _ai_reply_is_usable(ai_reply):
            return FallbackDecision(
                should_reply=False,
                fallback_text=None,
                should_handoff=False,
                reason=REASON_AI_SUCCESS,
            )

        return FallbackDecision(
            should_reply=True,
            fallback_text=_resolve_fallback_text(behavior),
            should_handoff=_should_handoff(behavior),
            reason=_failure_reason(ai_reply),
        )


def _ai_reply_is_usable(ai_reply: AiReplyResult) -> bool:
    return (
        ai_reply.is_success
        and ai_reply.text is not None
        and ai_reply.text.strip() != ""
    )


def _failure_reason(ai_reply: AiReplyResult) -> str:
    if ai_reply.text is not None and ai_reply.text.strip() == "":
        return REASON_AI_EMPTY_TEXT
    return REASON_AI_FAILURE


def _resolve_fallback_text(behavior: TenantBehaviorConfig) -> str:
    tenant_fallback = behavior.fallback_response
    if tenant_fallback is not None and tenant_fallback.strip():
        return tenant_fallback.strip()
    return PLATFORM_DEFAULT_FALLBACK


def _should_handoff(behavior: TenantBehaviorConfig) -> bool:
    if behavior.handoff_enabled is None:
        return True
    return behavior.handoff_enabled
