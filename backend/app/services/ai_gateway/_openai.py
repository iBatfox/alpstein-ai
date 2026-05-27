"""OpenAI provider types and HTTP client (Gateway-internal only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.schemas.assembled_prompt import AssembledPrompt

OPENAI_PROVIDER_NAME = "openai"
OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


@dataclass(frozen=True)
class OpenAIChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class OpenAIChatCompletionRequest:
    model: str
    messages: tuple[OpenAIChatMessage, ...]


@dataclass(frozen=True)
class OpenAIChatCompletionResponse:
    content: str
    model: str
    input_tokens: int | None
    output_tokens: int | None


class OpenAIChatClient(Protocol):
    async def create_chat_completion(
        self,
        request: OpenAIChatCompletionRequest,
    ) -> OpenAIChatCompletionResponse:
        ...


def map_assembled_prompt_to_openai_request(
    prompt: AssembledPrompt,
    *,
    model: str,
) -> OpenAIChatCompletionRequest:
    system_parts: list[str] = []
    user_parts: list[str] = []

    for section in prompt.sections:
        if section.kind == "system":
            system_parts.append(section.content)
        else:
            user_parts.append(section.content)

    messages: list[OpenAIChatMessage] = []
    if system_parts:
        messages.append(
            OpenAIChatMessage(
                role="system",
                content="\n\n".join(system_parts),
            )
        )
    if user_parts:
        messages.append(
            OpenAIChatMessage(
                role="user",
                content="\n\n".join(user_parts),
            )
        )

    if not messages:
        messages.append(OpenAIChatMessage(role="user", content=""))

    return OpenAIChatCompletionRequest(model=model, messages=tuple(messages))


class HttpxOpenAIChatClient:
    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float,
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def create_chat_completion(
        self,
        request: OpenAIChatCompletionRequest,
    ) -> OpenAIChatCompletionResponse:
        payload = {
            "model": request.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(self._timeout_seconds)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENAI_CHAT_COMPLETIONS_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return _parse_chat_completion_response(response.json())


def _parse_chat_completion_response(data: dict[str, Any]) -> OpenAIChatCompletionResponse:
    choices = data.get("choices") or []
    if not choices:
        return OpenAIChatCompletionResponse(
            content="",
            model=data.get("model", ""),
            input_tokens=_usage_tokens(data, "prompt_tokens"),
            output_tokens=_usage_tokens(data, "completion_tokens"),
        )

    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if not isinstance(content, str):
        content = str(content)

    return OpenAIChatCompletionResponse(
        content=content,
        model=data.get("model") or "",
        input_tokens=_usage_tokens(data, "prompt_tokens"),
        output_tokens=_usage_tokens(data, "completion_tokens"),
    )


def _usage_tokens(data: dict[str, Any], field: str) -> int | None:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None
    value = usage.get(field)
    return int(value) if isinstance(value, int) else None
