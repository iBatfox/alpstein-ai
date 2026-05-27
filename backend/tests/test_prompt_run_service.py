import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import TenantContextError
from app.services.prompt_run_service import (
    FINAL_PROMPT_MAX_CHARS,
    TRUNCATED_MARKER,
    PromptRunService,
    json_safe_metadata,
)


@pytest.fixture
def prompt_run_service() -> PromptRunService:
    return PromptRunService()


def _scope_entities():
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    message_id = uuid.uuid4()
    template_id = uuid.uuid4()

    business = SimpleNamespace(id=business_id, tenant_id=tenant_id)
    conversation = SimpleNamespace(
        id=conversation_id,
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=uuid.uuid4(),
    )
    message = SimpleNamespace(
        id=message_id,
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
    )
    return tenant_id, business, conversation, message, template_id


def test_json_safe_metadata_serializes_uuid_datetime_and_nested_values():
    correlation_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    observed_at = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)

    payload = json_safe_metadata(
        {
            "correlation_id": correlation_id,
            "tenant_id": tenant_id,
            "assembled_section_ids": ["platform_system", tenant_id],
            "nested": {"business_id": business_id},
            "observed_at": observed_at,
        }
    )

    json.dumps(payload)
    assert payload["correlation_id"] == str(correlation_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["assembled_section_ids"] == ["platform_system", str(tenant_id)]
    assert payload["nested"]["business_id"] == str(business_id)
    assert payload["observed_at"] == observed_at.isoformat()


@pytest.mark.anyio
async def test_create_prompt_run_stores_json_safe_observability_metadata(
    prompt_run_service: PromptRunService,
):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    correlation_id = uuid.uuid4()
    session = MagicMock()
    session.flush = AsyncMock()

    await prompt_run_service.create_prompt_run(
        session,
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        prompt_template_id=template_id,
        prompt_version="1",
        model="gpt-4o-mini",
        provider="openai",
        input_tokens=1,
        output_tokens=1,
        latency_ms=1,
        result="ok",
        error=None,
        metadata={
            "correlation_id": correlation_id,
            "tenant_id": tenant_id,
            "business_id": business.id,
            "conversation_id": conversation.id,
            "assembled_section_ids": ["platform_system"],
        },
    )

    stored = session.add.call_args.args[0]
    assert stored.metadata_ is not None
    json.dumps(stored.metadata_)
    assert stored.metadata_["correlation_id"] == str(correlation_id)
    assert stored.metadata_["tenant_id"] == str(tenant_id)
    assert isinstance(stored.metadata_["business_id"], str)


@pytest.mark.anyio
async def test_create_prompt_run_success(prompt_run_service: PromptRunService):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    session = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    prompt_run = await prompt_run_service.create_prompt_run(
        session,
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        prompt_template_id=template_id,
        prompt_version="1",
        model="gpt-4o-mini",
        provider="openai",
        input_tokens=120,
        output_tokens=45,
        latency_ms=850,
        result="Sure. What time works for you?",
        error=None,
    )

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    session.commit.assert_not_called()

    stored = session.add.call_args.args[0]
    assert prompt_run is stored
    assert stored.tenant_id == tenant_id
    assert stored.business_id == business.id
    assert stored.conversation_id == conversation.id
    assert stored.message_id == message.id
    assert stored.prompt_template_id == template_id
    assert stored.prompt_version == "1"
    assert stored.model == "gpt-4o-mini"
    assert stored.provider == "openai"
    assert stored.input_tokens == 120
    assert stored.output_tokens == 45
    assert stored.latency_ms == 850
    assert stored.result == "Sure. What time works for you?"
    assert stored.error is None


@pytest.mark.anyio
async def test_create_prompt_run_failure(prompt_run_service: PromptRunService):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    session = MagicMock()
    session.flush = AsyncMock()

    prompt_run = await prompt_run_service.create_prompt_run(
        session,
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        prompt_template_id=template_id,
        prompt_version="1",
        model="gpt-4o-mini",
        provider="openai",
        input_tokens=10,
        output_tokens=0,
        latency_ms=30_000,
        result=None,
        error="AI provider timeout",
    )

    stored = session.add.call_args.args[0]
    assert prompt_run is stored
    assert stored.result is None
    assert stored.error == "AI provider timeout"


@pytest.mark.anyio
async def test_create_prompt_run_redacts_and_truncates_final_prompt(
    prompt_run_service: PromptRunService,
):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    session = MagicMock()
    session.flush = AsyncMock()

    secret_body = "x" * (FINAL_PROMPT_MAX_CHARS + 500)
    final_prompt = (
        f"Authorization: Bearer sk-testtoken12345678901234567890\n{secret_body}"
    )

    await prompt_run_service.create_prompt_run(
        session,
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        prompt_template_id=template_id,
        prompt_version="1",
        model="gpt-4o-mini",
        provider="openai",
        input_tokens=None,
        output_tokens=None,
        latency_ms=None,
        result="ok",
        error=None,
        final_prompt=final_prompt,
    )

    stored = session.add.call_args.args[0]
    assert stored.final_prompt is not None
    assert "sk-testtoken" not in stored.final_prompt
    assert "Bearer" not in stored.final_prompt
    assert "[REDACTED]" in stored.final_prompt
    assert TRUNCATED_MARKER in stored.final_prompt
    assert len(stored.final_prompt) <= FINAL_PROMPT_MAX_CHARS + len(TRUNCATED_MARKER)


@pytest.mark.anyio
async def test_create_prompt_run_redacts_secrets_in_result_and_error(
    prompt_run_service: PromptRunService,
):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    session = MagicMock()
    session.flush = AsyncMock()

    await prompt_run_service.create_prompt_run(
        session,
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        prompt_template_id=template_id,
        prompt_version="1",
        model="gpt-4o-mini",
        provider="openai",
        input_tokens=1,
        output_tokens=0,
        latency_ms=1,
        result="failed with api_key=supersecretvalue",
        error="OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz",
    )

    stored = session.add.call_args.args[0]
    assert "supersecretvalue" not in (stored.result or "")
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in (stored.error or "")
    assert "[REDACTED]" in (stored.result or "")
    assert "[REDACTED]" in (stored.error or "")


@pytest.mark.anyio
async def test_create_prompt_run_raises_on_message_scope_mismatch(
    prompt_run_service: PromptRunService,
):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    message.conversation_id = uuid.uuid4()
    session = MagicMock()

    with pytest.raises(
        TenantContextError,
        match="message does not belong to conversation",
    ):
        await prompt_run_service.create_prompt_run(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            message=message,
            prompt_template_id=template_id,
            prompt_version="1",
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=None,
            output_tokens=None,
            latency_ms=None,
            result=None,
            error="scope mismatch",
        )

    session.add.assert_not_called()
