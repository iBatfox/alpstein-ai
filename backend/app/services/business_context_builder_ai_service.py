"""AI next-question generation for Business Context Builder (Phase 3.1)."""

from __future__ import annotations

import logging
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, settings
from app.models.business_context_builder import BusinessContextBuilderMessage
from app.services.ai_gateway_service import AiGatewayService
from app.services.business_context_builder_prompt_service import (
    BCB_DRAFT_RESULT_PROMPT_VERSION,
    BCB_NEXT_QUESTION_PROMPT_VERSION,
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
    trace: "BusinessContextBuilderAiTrace"

    def with_trace(
        self,
        trace: "BusinessContextBuilderAiTrace",
    ) -> "BusinessContextBuilderDraftResult":
        return BusinessContextBuilderDraftResult(
            structured_context=self.structured_context,
            generated_prompt=self.generated_prompt,
            fallback_used=trace.fallback_used,
            trace=trace,
        )


@dataclass(frozen=True)
class BusinessContextBuilderAiTrace:
    provider: str | None
    model: str | None
    prompt_version: str
    generation_timestamp: str
    fallback_used: bool
    ai_enabled: bool
    generation_mode: str
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    def to_metadata(self) -> dict[str, object]:
        metadata: dict[str, object] = {
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "generation_timestamp": self.generation_timestamp,
            "fallback_used": self.fallback_used,
            "ai_enabled": self.ai_enabled,
            "generation_mode": self.generation_mode,
        }
        if self.latency_ms is not None:
            metadata["latency_ms"] = self.latency_ms
        if self.input_tokens is not None:
            metadata["input_tokens"] = self.input_tokens
        if self.output_tokens is not None:
            metadata["output_tokens"] = self.output_tokens
        return metadata


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
                    prompt_version=BCB_NEXT_QUESTION_PROMPT_VERSION,
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
                prompt_version=BCB_NEXT_QUESTION_PROMPT_VERSION,
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
                    prompt_version=BCB_DRAFT_RESULT_PROMPT_VERSION,
                ),
            )
            return fallback_result.with_trace(
                _build_trace(
                    provider=None,
                    model=None,
                    prompt_version=BCB_DRAFT_RESULT_PROMPT_VERSION,
                    fallback_used=True,
                    ai_enabled=False,
                    generation_mode="fallback",
                )
            )

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
        parsed_result = (
            _parse_draft_result(
                gateway_result.text,
                trace=_build_trace(
                    provider=gateway_result.provider,
                    model=gateway_result.model,
                    prompt_version=BCB_DRAFT_RESULT_PROMPT_VERSION,
                    fallback_used=False,
                    ai_enabled=True,
                    generation_mode="ai",
                    latency_ms=gateway_result.latency_ms,
                    input_tokens=gateway_result.input_tokens,
                    output_tokens=gateway_result.output_tokens,
                ),
            )
            if gateway_result.succeeded and gateway_result.text
            else None
        )

        logger.info(
            "bcb_ai_draft_result_completed",
            extra=_observability_metadata(
                operation=BCB_AI_DRAFT_RESULT_OPERATION,
                session_id=session_id,
                tenant_id=tenant_id,
                business_id=business_id,
                next_step=current_step,
                ai_enabled=True,
                used_fallback=parsed_result is None,
                provider=gateway_result.provider,
                model=gateway_result.model,
                prompt_version=BCB_DRAFT_RESULT_PROMPT_VERSION,
                latency_ms=gateway_result.latency_ms,
                input_tokens=gateway_result.input_tokens,
                output_tokens=gateway_result.output_tokens,
                error=gateway_result.error,
            ),
        )

        if parsed_result is not None:
            return parsed_result

        return fallback_result.with_trace(
            _build_trace(
                provider=gateway_result.provider,
                model=gateway_result.model,
                prompt_version=BCB_DRAFT_RESULT_PROMPT_VERSION,
                fallback_used=True,
                ai_enabled=True,
                generation_mode="fallback",
                latency_ms=gateway_result.latency_ms,
                input_tokens=gateway_result.input_tokens,
                output_tokens=gateway_result.output_tokens,
            )
        )

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


def _parse_draft_result(
    text: str,
    *,
    trace: BusinessContextBuilderAiTrace,
) -> BusinessContextBuilderDraftResult | None:
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
        trace=trace,
    )


def _build_trace(
    *,
    provider: str | None,
    model: str | None,
    prompt_version: str,
    fallback_used: bool,
    ai_enabled: bool,
    generation_mode: str,
    latency_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> BusinessContextBuilderAiTrace:
    return BusinessContextBuilderAiTrace(
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        generation_timestamp=datetime.now(UTC).isoformat(),
        fallback_used=fallback_used,
        ai_enabled=ai_enabled,
        generation_mode=generation_mode,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
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
    prompt_version: str,
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
        "prompt_version": prompt_version,
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
