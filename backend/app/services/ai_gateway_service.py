"""AI Gateway Service — sole OpenAI HTTP integration (T11.8)."""

from __future__ import annotations

import time

import httpx

from app.core.config import Settings, settings
from app.schemas.ai_gateway import AiGatewayResult
from app.schemas.assembled_prompt import AssembledPrompt
from app.services.ai_gateway import _openai

ERROR_MISSING_API_KEY = "OpenAI API key is not configured"
ERROR_TIMEOUT = "AI provider request timed out"
ERROR_EMPTY_RESPONSE = "AI provider returned empty response"
ERROR_PROVIDER_PREFIX = "AI provider error"


class AiGatewayService:
    def __init__(
        self,
        *,
        app_settings: Settings | None = None,
        client: _openai.OpenAIChatClient | None = None,
    ) -> None:
        self._settings = app_settings or settings
        self._client = client

    async def complete(self, prompt: AssembledPrompt) -> AiGatewayResult:
        model = self._settings.openai_model
        started = time.perf_counter()

        if not self._settings.openai_api_key.strip():
            return _error_result(
                model=model,
                latency_ms=_elapsed_ms(started),
                error=ERROR_MISSING_API_KEY,
            )

        request = _openai.map_assembled_prompt_to_openai_request(
            prompt,
            model=model,
        )
        client = self._client or _openai.HttpxOpenAIChatClient(
            api_key=self._settings.openai_api_key,
            timeout_seconds=self._settings.ai_request_timeout_seconds,
        )

        try:
            response = await client.create_chat_completion(request)
        except httpx.TimeoutException:
            return _error_result(
                model=model,
                latency_ms=_elapsed_ms(started),
                error=ERROR_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            return _error_result(
                model=model,
                latency_ms=_elapsed_ms(started),
                error=f"{ERROR_PROVIDER_PREFIX}: {exc}",
            )
        except Exception as exc:
            return _error_result(
                model=model,
                latency_ms=_elapsed_ms(started),
                error=f"{ERROR_PROVIDER_PREFIX}: {exc}",
            )

        return _map_success_or_empty(response, latency_ms=_elapsed_ms(started))


def _map_success_or_empty(
    response: _openai.OpenAIChatCompletionResponse,
    *,
    latency_ms: int,
) -> AiGatewayResult:
    text = response.content.strip()
    if not text:
        return _error_result(
            model=response.model or settings.openai_model,
            latency_ms=latency_ms,
            error=ERROR_EMPTY_RESPONSE,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

    return AiGatewayResult(
        text=text,
        model=response.model or settings.openai_model,
        provider=_openai.OPENAI_PROVIDER_NAME,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        latency_ms=latency_ms,
        error=None,
    )


def _error_result(
    *,
    model: str,
    latency_ms: int,
    error: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> AiGatewayResult:
    return AiGatewayResult(
        text=None,
        model=model,
        provider=_openai.OPENAI_PROVIDER_NAME,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        error=error,
    )


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
