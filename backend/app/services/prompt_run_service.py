"""Persist AI execution audit rows in prompt_runs (T11.10)."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import TenantContextError
from app.models.prompt_run import PromptRun
from app.services.tenant_context_validator import validate_tenant_context

FINAL_PROMPT_MAX_CHARS = 32_000
TRUNCATED_MARKER = " [truncated]"

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(
        r"(api[_-]?key|authorization|x-api-key)\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(r"OPENAI_API_KEY\s*=\s*\S+", re.IGNORECASE),
)


class PromptRunService:
    async def create_prompt_run(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business: object,
        conversation: object,
        message: object,
        prompt_template_id: uuid.UUID | None,
        prompt_version: str | None,
        model: str,
        provider: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        latency_ms: int | None,
        result: str | None,
        error: str | None,
        final_prompt: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PromptRun:
        _validate_prompt_run_scope(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            message=message,
        )

        stored_final_prompt = _prepare_final_prompt(final_prompt)
        stored_result = _redact_secrets(result) if result is not None else None
        stored_error = _redact_secrets(error) if error is not None else None
        stored_metadata = (
            _redact_metadata(json_safe_metadata(metadata))
            if metadata is not None
            else None
        )

        prompt_run = PromptRun(
            tenant_id=tenant_id,
            business_id=business.id,
            conversation_id=conversation.id,
            message_id=message.id,
            prompt_template_id=prompt_template_id,
            prompt_version=prompt_version,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            final_prompt=stored_final_prompt,
            result=stored_result,
            error=stored_error,
            metadata_=stored_metadata,
        )
        session.add(prompt_run)
        await session.flush()
        return prompt_run


def _validate_prompt_run_scope(
    *,
    tenant_id: uuid.UUID,
    business: object,
    conversation: object,
    message: object,
) -> None:
    validate_tenant_context(
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
    )

    if message.tenant_id != tenant_id:
        raise TenantContextError("message does not belong to tenant")

    if message.business_id != business.id:
        raise TenantContextError("message does not belong to business")

    if message.conversation_id != conversation.id:
        raise TenantContextError("message does not belong to conversation")


def _prepare_final_prompt(final_prompt: str | None) -> str | None:
    if final_prompt is None:
        return None

    stripped = final_prompt.strip()
    if not stripped:
        return None

    redacted = _redact_secrets(stripped)
    truncated, _ = _truncate_with_marker(redacted, FINAL_PROMPT_MAX_CHARS)
    return truncated or None


def _redact_secrets(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _truncate_with_marker(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    if max_chars <= len(TRUNCATED_MARKER):
        return text[:max_chars], True
    return text[: max_chars - len(TRUNCATED_MARKER)] + TRUNCATED_MARKER, True


def json_safe_metadata(value: Any) -> Any:
    """Convert metadata values to JSON-serializable forms (UUID → str, etc.)."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return json_safe_metadata(value.value)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): json_safe_metadata(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe_metadata(item) for item in value]
    return str(value)


def _redact_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str):
            redacted[key] = _redact_secrets(value)
        elif isinstance(value, dict):
            redacted[key] = _redact_metadata(value)
        elif isinstance(value, list):
            redacted[key] = [
                _redact_secrets(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            redacted[key] = value
    return redacted
