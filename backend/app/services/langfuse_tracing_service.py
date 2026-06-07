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
from app.schemas.observability import (
    ALPSTEIN_DEMO_BUSINESS_EXTERNAL_ID,
    ObservabilityContext,
)
from app.services.ai_gateway import _openai

logger = logging.getLogger(__name__)

TRACE_TAG_GREETING = "greeting_orchestration"


class AiReplyTraceRecorder(Protocol):
    def record_gateway_result(
        self,
        *,
        assembled_prompt: AssembledPrompt,
        gateway_result: AiGatewayResult,
        model: str,
    ) -> None: ...

    def update_trace_metadata(self, metadata: dict[str, str]) -> None: ...


@dataclass
class _SpanHandle:
    span: Any | None = None

    @property
    def langfuse_trace_id(self) -> str | None:
        return _try_extract_langfuse_trace_id(self.span)

    def update_trace_metadata(self, metadata: dict[str, str]) -> None:
        if self.span is not None:
            self.span.update(metadata=metadata)


class _NoOpTraceRecorder:
    @property
    def langfuse_trace_id(self) -> str | None:
        return None

    def record_gateway_result(
        self,
        *,
        assembled_prompt: AssembledPrompt,
        gateway_result: AiGatewayResult,
        model: str,
    ) -> None:
        del assembled_prompt, gateway_result, model

    def update_trace_metadata(self, metadata: dict[str, str]) -> None:
        del metadata


class _LangfuseTraceRecorder:
    def __init__(self, client: Langfuse, observability: ObservabilityContext) -> None:
        self._client = client
        self._observability = observability

    @property
    def langfuse_trace_id(self) -> str | None:
        return None

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

        generation_metadata = _build_generation_metadata(
            observability=self._observability,
            gateway_result=gateway_result,
        )
        if gateway_result.model:
            generation_metadata["gateway_model"] = gateway_result.model
        if gateway_result.provider:
            generation_metadata["gateway_provider"] = gateway_result.provider
        generation_metadata["ai_success"] = "true" if gateway_result.succeeded else "false"

        with self._client.start_as_current_observation(
            name="openai_chat_completion",
            as_type="generation",
            model=gateway_result.model or model,
            input={"messages": input_messages},
            output=output,
            usage_details=usage_details or None,
            level=level,
            metadata=generation_metadata,
        ):
            pass

    def update_trace_metadata(self, metadata: dict[str, str]) -> None:
        del metadata


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
        observability: ObservabilityContext,
        customer_message_preview: str,
        assembled_prompt: AssembledPrompt,
    ) -> AsyncIterator[AiReplyTraceRecorder]:
        if not self.is_enabled():
            yield _NoOpTraceRecorder()
            return

        if observability.conversation_id is None:
            raise ValueError("observability.conversation_id is required for tracing")

        client = self._client or self._build_client()
        tags = _build_tags(observability)
        metadata = observability.to_langfuse_metadata(
            settings=self._settings,
        )
        span_input = {
            "business_id": observability.business_external_id,
            "conversation_id": str(observability.conversation_id),
            "channel": observability.channel,
            "customer_language": observability.customer_language_code,
            "greeting_mode": observability.greeting_mode,
            "customer_message": _truncate(customer_message_preview, 500),
            "correlation_id": str(observability.correlation_id),
        }

        span_handle = _SpanHandle()

        try:
            with propagate_attributes(
                tags=tags,
                session_id=str(observability.conversation_id),
                metadata=metadata,
            ):
                with client.start_as_current_observation(
                    name="ai_reply_orchestration",
                    as_type="span",
                    input=span_input,
                    metadata=metadata,
                ) as span:
                    span_handle.span = span
                    recorder = _LangfuseTraceRecorder(client, observability)
                    try:
                        yield _CompositeTraceRecorder(recorder, span_handle)
                    finally:
                        span.update(
                            output={
                                "traced": True,
                                "greeting_mode": observability.greeting_mode,
                                "customer_language": observability.customer_language_code,
                                "correlation_id": str(observability.correlation_id),
                            }
                        )
        except Exception:
            logger.exception(
                "Langfuse trace failed; continuing without tracing",
                extra={"correlation_id": str(observability.correlation_id)},
            )
            yield _NoOpTraceRecorder()
            return
        finally:
            try:
                client.flush()
            except Exception:
                logger.exception(
                    "Langfuse flush failed",
                    extra={"correlation_id": str(observability.correlation_id)},
                )

    def _build_client(self) -> Langfuse:
        host = self._settings.langfuse_host.strip()
        return Langfuse(
            public_key=self._settings.langfuse_public_key.strip(),
            secret_key=self._settings.langfuse_secret_key.strip(),
            base_url=host if host else None,
        )


class _CompositeTraceRecorder:
    def __init__(
        self,
        generation_recorder: _LangfuseTraceRecorder,
        span_handle: _SpanHandle,
    ) -> None:
        self._generation_recorder = generation_recorder
        self._span_handle = span_handle

    @property
    def langfuse_trace_id(self) -> str | None:
        return self._span_handle.langfuse_trace_id

    def record_gateway_result(
        self,
        *,
        assembled_prompt: AssembledPrompt,
        gateway_result: AiGatewayResult,
        model: str,
    ) -> None:
        self._generation_recorder.record_gateway_result(
            assembled_prompt=assembled_prompt,
            gateway_result=gateway_result,
            model=model,
        )

    def update_trace_metadata(self, metadata: dict[str, str]) -> None:
        self._span_handle.update_trace_metadata(metadata)


def _build_tags(observability: ObservabilityContext) -> list[str]:
    tags = [TRACE_TAG_GREETING]
    if observability.channel == "telegram":
        tags.append("telegram")
    if observability.business_external_id == ALPSTEIN_DEMO_BUSINESS_EXTERNAL_ID:
        tags.append(ALPSTEIN_DEMO_BUSINESS_EXTERNAL_ID)
    return tags


def _build_generation_metadata(
    *,
    observability: ObservabilityContext,
    gateway_result: AiGatewayResult,
) -> dict[str, str]:
    metadata = {
        "business_id": observability.business_external_id or "",
        "channel": observability.channel or "",
        "conversation_id": str(observability.conversation_id)
        if observability.conversation_id
        else "",
        "prompt_version": observability.prompt_version or "",
        "latency_ms": str(gateway_result.latency_ms),
    }
    if observability.user_external_id:
        metadata["user_external_id"] = observability.user_external_id
    return {key: value for key, value in metadata.items() if value}


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _try_extract_langfuse_trace_id(span: Any | None) -> str | None:
    if span is None:
        return None
    for attr in ("trace_id", "traceId"):
        value = getattr(span, attr, None)
        if value:
            return str(value)
    trace_context = getattr(span, "trace_context", None)
    if trace_context is not None:
        for attr in ("trace_id", "traceId"):
            value = getattr(trace_context, attr, None)
            if value:
                return str(value)
    return None
