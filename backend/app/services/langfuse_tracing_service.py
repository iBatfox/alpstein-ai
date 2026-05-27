"""Langfuse tracing for AI reply orchestration (dev/internal only)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol

from langfuse import Langfuse, propagate_attributes

from app.core.config import Settings, langfuse_tracing_active, settings
from app.schemas.ai_gateway import AiGatewayResult
from app.schemas.assembled_prompt import AssembledPrompt
from app.schemas.greeting import GreetingPolicy
from app.services.ai_gateway import _openai

logger = logging.getLogger(__name__)

TRACE_TAG_GREETING = "greeting_orchestration"
TRACE_TAG_DEMO_BUSINESS = "alpstein_ai_demo_001"
DEMO_BUSINESS_EXTERNAL_ID = "demo_barbershop_001"
OPERATOR_CONTEXT_TRACE_MAX_CHARS = 4000
ASSEMBLED_PROMPT_TRACE_MAX_CHARS = 24_000


class AiReplyTraceRecorder(Protocol):
    def record_gateway_result(
        self,
        *,
        assembled_prompt: AssembledPrompt,
        gateway_result: AiGatewayResult,
        model: str,
    ) -> None: ...


@dataclass(frozen=True)
class _AiReplyTraceContext:
    business_external_id: str
    business_id: str
    conversation_id: str
    channel: str
    customer_language_code: str
    greeting_mode: str
    operator_business_context: str | None
    customer_message_preview: str


class _NoOpTraceRecorder:
    def record_gateway_result(
        self,
        *,
        assembled_prompt: AssembledPrompt,
        gateway_result: AiGatewayResult,
        model: str,
    ) -> None:
        del assembled_prompt, gateway_result, model


class _LangfuseTraceRecorder:
    def __init__(self, client: Langfuse) -> None:
        self._client = client

    def record_gateway_result(
        self,
        *,
        assembled_prompt: AssembledPrompt,
        gateway_result: AiGatewayResult,
        model: str,
    ) -> None:
        request = _openai.map_assembled_prompt_to_openai_request(
            assembled_prompt,
            model=model,
        )
        input_messages = [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ]
        usage_details: dict[str, int] = {}
        if gateway_result.input_tokens is not None:
            usage_details["input"] = gateway_result.input_tokens
        if gateway_result.output_tokens is not None:
            usage_details["output"] = gateway_result.output_tokens

        level = "DEFAULT" if gateway_result.succeeded else "ERROR"
        output: str | dict[str, Any]
        if gateway_result.text:
            output = gateway_result.text
        elif gateway_result.error:
            output = {"error": gateway_result.error}
        else:
            output = {"error": "unknown_failure"}

        with self._client.start_as_current_observation(
            name="openai_chat_completion",
            as_type="generation",
            model=gateway_result.model or model,
            input={"messages": input_messages},
            output=output,
            usage_details=usage_details or None,
            level=level,
            metadata={"latency_ms": gateway_result.latency_ms},
        ):
            pass


class LangfuseTracingService:
    def __init__(
        self,
        *,
        app_settings: Settings | None = None,
        client: Langfuse | None = None,
    ) -> None:
        self._settings = app_settings or settings
        self._client = client

    def is_enabled(self) -> bool:
        return langfuse_tracing_active(self._settings)

    @asynccontextmanager
    async def trace_ai_reply(
        self,
        *,
        business_external_id: str,
        business_id: str,
        conversation_id: str,
        channel: str,
        greeting_policy: GreetingPolicy,
        operator_business_context: str | None,
        customer_message_text: str,
        assembled_prompt: AssembledPrompt,
    ) -> AsyncIterator[AiReplyTraceRecorder]:
        if not self.is_enabled():
            yield _NoOpTraceRecorder()
            return

        context = _AiReplyTraceContext(
            business_external_id=business_external_id,
            business_id=business_id,
            conversation_id=conversation_id,
            channel=channel,
            customer_language_code=greeting_policy.reply_language_code,
            greeting_mode=greeting_policy.mode.value,
            operator_business_context=operator_business_context,
            customer_message_preview=_truncate(customer_message_text, 500),
        )

        client = self._client or self._build_client()
        tags = _build_tags(context)
        metadata = _build_metadata(context, assembled_prompt)
        span_input = {
            "business_id": context.business_external_id,
            "conversation_id": context.conversation_id,
            "channel": context.channel,
            "customer_language": context.customer_language_code,
            "greeting_mode": context.greeting_mode,
            "customer_message": context.customer_message_preview,
        }

        try:
            with propagate_attributes(
                tags=tags,
                session_id=context.conversation_id,
                metadata=metadata,
            ):
                with client.start_as_current_observation(
                    name="ai_reply_orchestration",
                    as_type="span",
                    input=span_input,
                    metadata=metadata,
                ) as span:
                    recorder = _LangfuseTraceRecorder(client)
                    try:
                        yield recorder
                    finally:
                        span.update(
                            output={
                                "traced": True,
                                "greeting_mode": context.greeting_mode,
                                "customer_language": context.customer_language_code,
                            }
                        )
        except Exception:
            logger.exception("Langfuse trace failed; continuing without tracing")
            yield _NoOpTraceRecorder()
            return
        finally:
            try:
                client.flush()
            except Exception:
                logger.exception("Langfuse flush failed")

    def _build_client(self) -> Langfuse:
        host = self._settings.langfuse_host.strip()
        return Langfuse(
            public_key=self._settings.langfuse_public_key.strip(),
            secret_key=self._settings.langfuse_secret_key.strip(),
            base_url=host if host else None,
        )


def _build_tags(context: _AiReplyTraceContext) -> list[str]:
    tags = [TRACE_TAG_GREETING]
    if context.channel == "telegram":
        tags.append("telegram")
    if context.business_external_id == DEMO_BUSINESS_EXTERNAL_ID:
        tags.append(TRACE_TAG_DEMO_BUSINESS)
    return tags


def _build_metadata(
    context: _AiReplyTraceContext,
    assembled_prompt: AssembledPrompt,
) -> dict[str, str]:
    metadata: dict[str, str] = {
        "business_id": context.business_external_id,
        "business_uuid": context.business_id,
        "conversation_id": context.conversation_id,
        "channel": context.channel,
        "customer_language": context.customer_language_code,
        "greeting_mode": context.greeting_mode,
    }
    if context.operator_business_context:
        metadata["operator_business_context"] = _truncate(
            context.operator_business_context,
            OPERATOR_CONTEXT_TRACE_MAX_CHARS,
        )
    metadata["assembled_prompt"] = _truncate(
        _serialize_prompt_for_trace(assembled_prompt),
        ASSEMBLED_PROMPT_TRACE_MAX_CHARS,
    )
    return metadata


def _serialize_prompt_for_trace(prompt: AssembledPrompt) -> str:
    return "\n\n".join(
        f"=== {section.section_id} ({section.kind}) ===\n{section.content}"
        for section in prompt.sections
    )


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."
