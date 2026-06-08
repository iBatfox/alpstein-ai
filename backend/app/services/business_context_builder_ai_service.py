"""AI next-question generation for Business Context Builder (Phase 3.1)."""

from __future__ import annotations

import logging
import json
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, settings
from app.models.business_context_builder import BusinessContextBuilderMessage
from app.services.ai_gateway_service import AiGatewayService
from app.services.business_context_builder_prompt_service import (
    BusinessContextBuilderConversationTurn,
    BusinessContextBuilderPromptInput,
    BusinessContextBuilderPromptService,
)

logger = logging.getLogger(__name__)

BCB_AI_FEATURE = "business_context_builder"
BCB_AI_NEXT_QUESTION_OPERATION = "next_question"
BCB_AI_DRAFT_RESULT_OPERATION = "draft_result"


@dataclass(frozen=True)
class BusinessContextBuilderDraftResult:
    structured_context: dict[str, Any]
    generated_prompt: str
    fallback_used: bool


class BusinessContextBuilderAiService:
    def __init__(
        self,
        *,
        app_settings: Settings | None = None,
        prompt_service: BusinessContextBuilderPromptService | None = None,
        ai_gateway_service: AiGatewayService | None = None,
    ) -> None:
        self._settings = app_settings or settings
        self._prompt_service = prompt_service or BusinessContextBuilderPromptService()
        self._ai_gateway_service = ai_gateway_service or AiGatewayService(
            app_settings=self._settings
        )

    async def generate_next_question(
        self,
        *,
        session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        next_step: str,
        messages: list[BusinessContextBuilderMessage],
        fallback_question: str,
    ) -> str:
        if not self._bcb_ai_enabled():
            logger.info(
                "bcb_ai_next_question_skipped",
                extra=_observability_metadata(
                    operation=BCB_AI_NEXT_QUESTION_OPERATION,
                    session_id=session_id,
                    tenant_id=tenant_id,
                    business_id=business_id,
                    next_step=next_step,
                    ai_enabled=False,
                    used_fallback=True,
                ),
            )
            return fallback_question

        prompt_input = BusinessContextBuilderPromptInput(
            session_id=session_id,
            tenant_id=tenant_id,
            business_id=business_id,
            next_step=next_step,
            messages=tuple(
                BusinessContextBuilderConversationTurn(
                    role=message.role,
                    content=message.content,
                )
                for message in messages
            ),
        )
        assembled_prompt = self._prompt_service.build_next_question_prompt(prompt_input)
        gateway_result = await self._ai_gateway_service.complete(assembled_prompt)

        logger.info(
            "bcb_ai_next_question_completed",
            extra=_observability_metadata(
                operation=BCB_AI_NEXT_QUESTION_OPERATION,
                session_id=session_id,
                tenant_id=tenant_id,
                business_id=business_id,
                next_step=next_step,
                ai_enabled=True,
                used_fallback=not gateway_result.succeeded,
                provider=gateway_result.provider,
                model=gateway_result.model,
                latency_ms=gateway_result.latency_ms,
                input_tokens=gateway_result.input_tokens,
                output_tokens=gateway_result.output_tokens,
                error=gateway_result.error,
            ),
        )

        if gateway_result.succeeded and gateway_result.text:
            normalized = _normalize_question_text(gateway_result.text)
            if normalized:
                return normalized

        return fallback_question

    async def generate_draft_result(
        self,
        *,
        session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        current_step: str | None,
        messages: list[BusinessContextBuilderMessage],
        fallback_result: BusinessContextBuilderDraftResult,
    ) -> BusinessContextBuilderDraftResult:
        if not self._bcb_ai_draft_enabled():
            logger.info(
                "bcb_ai_draft_result_skipped",
                extra=_observability_metadata(
                    operation=BCB_AI_DRAFT_RESULT_OPERATION,
                    session_id=session_id,
                    tenant_id=tenant_id,
                    business_id=business_id,
                    next_step=current_step,
                    ai_enabled=False,
                    used_fallback=True,
                ),
            )
            return fallback_result

        prompt_input = BusinessContextBuilderPromptInput(
            session_id=session_id,
            tenant_id=tenant_id,
            business_id=business_id,
            next_step=current_step or "",
            messages=tuple(
                BusinessContextBuilderConversationTurn(
                    role=message.role,
                    content=message.content,
                )
                for message in messages
            ),
        )
        assembled_prompt = self._prompt_service.build_draft_result_prompt(prompt_input)
        gateway_result = await self._ai_gateway_service.complete(assembled_prompt)

        logger.info(
            "bcb_ai_draft_result_completed",
            extra=_observability_metadata(
                operation=BCB_AI_DRAFT_RESULT_OPERATION,
                session_id=session_id,
                tenant_id=tenant_id,
                business_id=business_id,
                next_step=current_step,
                ai_enabled=True,
                used_fallback=not gateway_result.succeeded,
                provider=gateway_result.provider,
                model=gateway_result.model,
                latency_ms=gateway_result.latency_ms,
                input_tokens=gateway_result.input_tokens,
                output_tokens=gateway_result.output_tokens,
                error=gateway_result.error,
            ),
        )

        if gateway_result.succeeded and gateway_result.text:
            parsed = _parse_draft_result(gateway_result.text)
            if parsed is not None:
                return parsed

        return fallback_result

    def _bcb_ai_enabled(self) -> bool:
        if not self._settings.bcb_ai_enabled:
            return False
        return bool(self._settings.openai_api_key.strip())

    def _bcb_ai_draft_enabled(self) -> bool:
        if not self._settings.bcb_ai_draft_enabled:
            return False
        return bool(self._settings.openai_api_key.strip())


def _normalize_question_text(text: str) -> str:
    cleaned = text.strip().strip('"').strip("'")
    if not cleaned:
        return ""
    if "\n" in cleaned:
        cleaned = cleaned.splitlines()[0].strip()
    return cleaned


def _parse_draft_result(text: str) -> BusinessContextBuilderDraftResult | None:
    try:
        payload = json.loads(text.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None

    structured_context = payload.get("structured_context")
    generated_prompt = payload.get("generated_prompt")
    if not isinstance(structured_context, dict):
        return None
    if not isinstance(generated_prompt, str) or not generated_prompt.strip():
        return None

    return BusinessContextBuilderDraftResult(
        structured_context=structured_context,
        generated_prompt=generated_prompt.strip(),
        fallback_used=False,
    )


def _observability_metadata(
    *,
    operation: str,
    session_id: uuid.UUID,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    next_step: str | None,
    ai_enabled: bool,
    used_fallback: bool,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    error: str | None = None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "feature": BCB_AI_FEATURE,
        "operation": operation,
        "session_id": str(session_id),
        "tenant_id": str(tenant_id),
        "business_id": str(business_id),
        "ai_enabled": ai_enabled,
        "fallback_used": used_fallback,
    }
    if next_step is not None:
        metadata["next_step"] = next_step
    if provider is not None:
        metadata["provider"] = provider
    if model is not None:
        metadata["model"] = model
    if latency_ms is not None:
        metadata["latency_ms"] = latency_ms
    if input_tokens is not None:
        metadata["input_tokens"] = input_tokens
    if output_tokens is not None:
        metadata["output_tokens"] = output_tokens
    if error is not None:
        metadata["error"] = error
    return metadata
