"""Langfuse tracing service tests (no live Langfuse calls)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.schemas.ai_gateway import AiGatewayResult
from app.schemas.assembled_prompt import AssembledPrompt, AssembledPromptSection
from app.schemas.greeting import GreetingMode, GreetingPolicy
from app.services.langfuse_tracing_service import (
    DEMO_BUSINESS_EXTERNAL_ID,
    LangfuseTracingService,
    TRACE_TAG_DEMO_BUSINESS,
    TRACE_TAG_GREETING,
)


def _settings(**overrides) -> Settings:
    return Settings(
        environment=overrides.get("environment", "development"),
        LANGFUSE_PUBLIC_KEY=overrides.get("langfuse_public_key", "pk-test"),
        LANGFUSE_SECRET_KEY=overrides.get("langfuse_secret_key", "sk-test"),
        LANGFUSE_TRACING_ENABLED=overrides.get("langfuse_tracing_enabled", False),
    )


def _assembled_prompt() -> AssembledPrompt:
    return AssembledPrompt(
        task="reply_to_customer",
        sections=(
            AssembledPromptSection(
                section_id="platform_system",
                label="PLATFORM SYSTEM",
                content="[PLATFORM SYSTEM]\nSafety.",
                kind="system",
            ),
            AssembledPromptSection(
                section_id="current_customer_message",
                label="CURRENT CUSTOMER MESSAGE (reference data)",
                content="[CURRENT CUSTOMER MESSAGE (reference data)]\nHello",
                kind="data",
            ),
        ),
    )


def _greeting_policy() -> GreetingPolicy:
    return GreetingPolicy(
        mode=GreetingMode.FIRST_CONTACT,
        reply_language_code="ru",
        reply_language_name="Russian",
    )


def test_tracing_disabled_without_keys():
    service = LangfuseTracingService(
        app_settings=_settings(
            langfuse_public_key="",
            langfuse_secret_key="",
        )
    )
    assert service.is_enabled() is False


def test_tracing_enabled_in_development_with_keys():
    service = LangfuseTracingService(app_settings=_settings())
    assert service.is_enabled() is True


def test_tracing_disabled_in_production_without_explicit_flag():
    service = LangfuseTracingService(
        app_settings=_settings(environment="production")
    )
    assert service.is_enabled() is False


def test_tracing_enabled_in_production_when_explicit():
    service = LangfuseTracingService(
        app_settings=_settings(
            environment="production",
            langfuse_tracing_enabled=True,
        )
    )
    assert service.is_enabled() is True


def test_build_tags_for_telegram_demo():
    from app.services import langfuse_tracing_service as module

    context = module._AiReplyTraceContext(
        business_external_id=DEMO_BUSINESS_EXTERNAL_ID,
        business_id=str(uuid.uuid4()),
        conversation_id=str(uuid.uuid4()),
        channel="telegram",
        customer_language_code="ru",
        greeting_mode="first_contact",
        operator_business_context="Russian supported",
        customer_message_preview="Привет",
    )
    tags = module._build_tags(context)

    assert TRACE_TAG_GREETING in tags
    assert "telegram" in tags
    assert TRACE_TAG_DEMO_BUSINESS in tags


@pytest.mark.anyio
async def test_trace_ai_reply_noop_when_disabled():
    service = LangfuseTracingService(
        app_settings=_settings(langfuse_public_key=""),
    )
    recorded = False

    async with service.trace_ai_reply(
        business_external_id=DEMO_BUSINESS_EXTERNAL_ID,
        business_id=str(uuid.uuid4()),
        conversation_id=str(uuid.uuid4()),
        channel="telegram",
        greeting_policy=_greeting_policy(),
        operator_business_context="notes",
        customer_message_text="Hi",
        assembled_prompt=_assembled_prompt(),
    ) as recorder:
        recorder.record_gateway_result(
            assembled_prompt=_assembled_prompt(),
            gateway_result=AiGatewayResult(
                text="Hello",
                model="gpt-4o-mini",
                provider="openai",
                input_tokens=1,
                output_tokens=2,
                latency_ms=10,
                error=None,
            ),
            model="gpt-4o-mini",
        )
        recorded = True

    assert recorded is True


@pytest.mark.anyio
async def test_trace_ai_reply_records_openai_generation_when_enabled():
    mock_client = MagicMock()
    mock_span = MagicMock()
    mock_client.start_as_current_observation.return_value.__enter__ = MagicMock(
        return_value=mock_span
    )
    mock_client.start_as_current_observation.return_value.__exit__ = MagicMock(
        return_value=False
    )

    service = LangfuseTracingService(
        app_settings=_settings(),
        client=mock_client,
    )

    with patch(
        "app.services.langfuse_tracing_service.propagate_attributes"
    ) as mock_propagate:
        mock_propagate.return_value.__enter__ = MagicMock(return_value=None)
        mock_propagate.return_value.__exit__ = MagicMock(return_value=False)

        async with service.trace_ai_reply(
            business_external_id=DEMO_BUSINESS_EXTERNAL_ID,
            business_id=str(uuid.uuid4()),
            conversation_id=str(uuid.uuid4()),
            channel="telegram",
            greeting_policy=_greeting_policy(),
            operator_business_context="If Russian, reply in Russian",
            customer_message_text="Привет",
            assembled_prompt=_assembled_prompt(),
        ) as recorder:
            recorder.record_gateway_result(
                assembled_prompt=_assembled_prompt(),
                gateway_result=AiGatewayResult(
                    text="Здравствуйте",
                    model="gpt-4o-mini",
                    provider="openai",
                    input_tokens=100,
                    output_tokens=20,
                    latency_ms=250,
                    error=None,
                ),
                model="gpt-4o-mini",
            )

    mock_client.flush.assert_called_once()
    generation_calls = [
        call
        for call in mock_client.start_as_current_observation.call_args_list
        if call.kwargs.get("as_type") == "generation"
    ]
    assert len(generation_calls) == 1
    gen_kwargs = generation_calls[0].kwargs
    assert gen_kwargs["name"] == "openai_chat_completion"
    assert gen_kwargs["output"] == "Здравствуйте"
    assert gen_kwargs["usage_details"] == {"input": 100, "output": 20}
    assert "messages" in gen_kwargs["input"]

    metadata = None
    for call in mock_client.start_as_current_observation.call_args_list:
        if call.kwargs.get("as_type") == "span":
            metadata = call.kwargs.get("metadata")
            break
    assert metadata is not None
    assert metadata["business_id"] == DEMO_BUSINESS_EXTERNAL_ID
    assert metadata["greeting_mode"] == "first_contact"
    assert metadata["customer_language"] == "ru"
    assert "operator_business_context" in metadata
    assert "assembled_prompt" in metadata
    assert "sk-test" not in str(metadata)
    assert "pk-test" not in str(metadata)
