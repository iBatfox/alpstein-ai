import logging
import uuid
from dataclasses import fields
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.ai_configuration import (
    AiConfigurationBundle,
    PlatformPromptTemplateConfig,
    TenantBehaviorConfig,
    TenantBusinessContextConfig,
    TenantChannelRulesConfig,
)
from app.schemas.ai_gateway import AiGatewayResult
from app.schemas.ai_reply import AiReplyResult
from app.schemas.assembled_prompt import AssembledPrompt, AssembledPromptSection
from app.schemas.conversation_context import ConversationHistory
from app.schemas.greeting import GreetingMode
from app.schemas.knowledge import KnowledgeRetrievalResult
from app.schemas.conversation_intent import ConversationIntent
from app.services.ai_reply_orchestration_service import (
    LOG_AI_PROMPT_SOURCE_DIAGNOSTICS,
    AiReplyOrchestrationService,
    _log_prompt_source_diagnostics,
    _serialize_assembled_prompt,
)
from app.services.conversation_intent_service import ConversationIntentService
from app.services.greeting_policy_service import GreetingPolicyService


def _scope_entities():
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    message_id = uuid.uuid4()
    template_id = uuid.uuid4()

    business = SimpleNamespace(
        id=business_id,
        tenant_id=tenant_id,
        external_id="demo_barbershop_001",
    )
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


def _configuration_bundle(
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    template_id: uuid.UUID,
    behavior: TenantBehaviorConfig | None = None,
) -> AiConfigurationBundle:
    return AiConfigurationBundle(
        tenant_id=tenant_id,
        business_id=business_id,
        channel="whatsapp",
        template_key="customer_reply_v1",
        platform_template=PlatformPromptTemplateConfig(
            id=template_id,
            template_key="customer_reply_v1",
            template_name="Customer reply",
            version="1",
            system_prompt="Platform safety rules.",
        ),
        business_context=TenantBusinessContextConfig(present=False),
        behavior=behavior or TenantBehaviorConfig(present=False),
        channel_rules=TenantChannelRulesConfig.missing("whatsapp"),
    )


def _assembled_prompt() -> AssembledPrompt:
    return AssembledPrompt(
        task="reply_to_customer",
        sections=(
            AssembledPromptSection(
                section_id="platform_system",
                label="PLATFORM SYSTEM",
                content="[PLATFORM SYSTEM]\nPlatform safety rules.",
                kind="system",
            ),
            AssembledPromptSection(
                section_id="current_customer_message",
                label="CURRENT CUSTOMER MESSAGE (reference data)",
                content="[CURRENT CUSTOMER MESSAGE (reference data)]\nBook tomorrow?",
                kind="data",
            ),
        ),
    )


def test_prompt_source_diagnostics_log_reports_markers(caplog):
    assembled = AssembledPrompt(
        task="reply_to_customer",
        sections=(
            AssembledPromptSection(
                section_id="platform_system",
                label="PLATFORM SYSTEM",
                content="Platform safety rules.",
                kind="system",
            ),
            AssembledPromptSection(
                section_id="business_context_source_of_truth",
                label="BUSINESS CONTEXT SOURCE OF TRUTH",
                content=(
                    "Business context is the source of truth.\n"
                    "Use instagram.com/alpstein_ai for Instagram."
                ),
                kind="data",
            ),
            AssembledPromptSection(
                section_id="conversation_history",
                label="CONVERSATION HISTORY",
                content="ai: Old answer mentioned linkedin.com/in/ibatfox",
                kind="data",
            ),
        ),
    )

    with caplog.at_level(logging.INFO):
        _log_prompt_source_diagnostics(
            assembled_prompt=assembled,
            operator_business_context="x" * 700,
            channel="telegram",
            business_id="alpstein_ai_demo_001",
            business_context_sources=(
                "tenant_business_profiles.business_description",
                "webhook.operator_business_context",
            ),
        )

    record = next(
        item
        for item in caplog.records
        if item.message.startswith(LOG_AI_PROMPT_SOURCE_DIAGNOSTICS)
    )
    assert record.channel == "telegram"
    assert record.business_id == "alpstein_ai_demo_001"
    assert record.operator_business_context_length == 700
    assert record.operator_business_context_preview == "x" * 500
    assert record.source_of_truth_business_context_loaded is True
    assert len(record.business_context_hash) == 64
    assert record.business_context_sources == [
        "tenant_business_profiles.business_description",
        "webhook.operator_business_context",
    ]
    assert record.business_context_contains_linkedin is False
    assert record.history_contains_linkedin is True
    assert record.final_prompt_contains_linkedin is True
    assert record.platform_system_contains_linkedin is False
    assert record.platform_system_contains_email is False
    assert record.assembled_prompt_contains_linkedin is True
    assert record.assembled_prompt_contains_instagram is True
    assert record.prompt_contains_linkedin_ibatfox is True
    assert record.prompt_contains_instagram_alpstein_ai is True


def test_serialized_prompt_keeps_history_and_business_context_out_of_platform_system():
    assembled = AssembledPrompt(
        task="reply_to_customer",
        sections=(
            AssembledPromptSection(
                section_id="platform_system",
                label="PLATFORM SYSTEM",
                content="[PLATFORM SYSTEM]\nPlatform safety rules.",
                kind="system",
            ),
            AssembledPromptSection(
                section_id="business_context_source_of_truth",
                label="BUSINESS CONTEXT SOURCE OF TRUTH",
                content=(
                    "[BUSINESS CONTEXT SOURCE OF TRUTH]\n"
                    "Instagram: https://instagram.com/alpstein_ai"
                ),
                kind="data",
            ),
            AssembledPromptSection(
                section_id="conversation_history",
                label="CONVERSATION HISTORY",
                content=(
                    "[CONVERSATION HISTORY]\n"
                    "ai (dialogue only, not business facts): "
                    "Old contact https://www.linkedin.com/in/ibatfox/ "
                    "admin@alpstein-ai.ch"
                ),
                kind="data",
            ),
        ),
    )

    serialized = _serialize_assembled_prompt(assembled)
    platform = serialized[
        serialized.index("=== platform_system (system) ===") : serialized.index(
            "=== business_context_source_of_truth (data) ==="
        )
    ].lower()

    assert "linkedin.com/in/ibatfox" not in platform
    assert "admin@alpstein-ai.ch" not in platform
    assert "instagram.com" not in platform
    assert "https://instagram.com/alpstein_ai" in serialized
    assert "linkedin.com/in/ibatfox" in serialized


@pytest.fixture
def orchestration_mocks():
    return {
        "ai_configuration_service": MagicMock(),
        "knowledge_retrieval_service": MagicMock(),
        "message_service": MagicMock(),
        "prompt_builder_service": MagicMock(),
        "ai_gateway_service": MagicMock(),
        "prompt_run_service": MagicMock(),
        "greeting_policy_service": GreetingPolicyService(),
        "conversation_intent_service": ConversationIntentService(),
        "langfuse_tracing_service": MagicMock(),
    }


def _mock_langfuse_trace_context(mocks: dict) -> None:
    recorder = MagicMock()
    recorder.langfuse_trace_id = None
    trace_cm = AsyncMock()
    trace_cm.__aenter__.return_value = recorder
    trace_cm.__aexit__.return_value = None
    mocks["langfuse_tracing_service"].trace_ai_reply.return_value = trace_cm


@pytest.fixture
def orchestrator(orchestration_mocks) -> AiReplyOrchestrationService:
    return AiReplyOrchestrationService(**orchestration_mocks)


@pytest.mark.anyio
async def test_generate_reply_calls_services_in_order(
    orchestrator: AiReplyOrchestrationService,
    orchestration_mocks,
):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    configuration = _configuration_bundle(tenant_id, business.id, template_id)
    knowledge = KnowledgeRetrievalResult.empty()
    history = ConversationHistory.empty()
    assembled = _assembled_prompt()
    gateway_result = AiGatewayResult(
        text="Tomorrow at 10:00 works.",
        model="gpt-4o-mini",
        provider="openai",
        input_tokens=100,
        output_tokens=20,
        latency_ms=400,
        error=None,
    )
    prompt_run = SimpleNamespace(id=uuid.uuid4())
    call_order: list[str] = []

    orchestration_mocks["ai_configuration_service"].load_for_message = AsyncMock(
        side_effect=lambda *args, **kwargs: (
            call_order.append("config"),
            configuration,
        )[1]
    )
    orchestration_mocks["knowledge_retrieval_service"].retrieve_for_message = AsyncMock(
        side_effect=lambda *args, **kwargs: (
            call_order.append("knowledge"),
            knowledge,
        )[1]
    )
    orchestration_mocks["message_service"].load_recent_conversation_history = AsyncMock(
        side_effect=lambda *args, **kwargs: (
            call_order.append("history"),
            history,
        )[1]
    )
    orchestration_mocks["prompt_builder_service"].build_reply_to_customer = MagicMock(
        side_effect=lambda **kwargs: (
            call_order.append("build"),
            assembled,
        )[1]
    )
    orchestration_mocks["ai_gateway_service"].complete = AsyncMock(
        side_effect=lambda prompt: (
            call_order.append("gateway"),
            gateway_result,
        )[1]
    )
    orchestration_mocks["prompt_run_service"].create_prompt_run = AsyncMock(
        side_effect=lambda *args, **kwargs: (
            call_order.append("prompt_run"),
            prompt_run,
        )[1]
    )
    _mock_langfuse_trace_context(orchestration_mocks)

    session = AsyncMock()
    result, langfuse_trace_id = await orchestrator.generate_reply(
        session,
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        customer_message_text="Book tomorrow?",
        channel="whatsapp",
        template_key="customer_reply_v1",
    )

    assert call_order == ["config", "knowledge", "history", "build", "gateway", "prompt_run"]
    assert langfuse_trace_id is None
    assert result.is_success is True
    assert result.text == "Tomorrow at 10:00 works."
    assert result.prompt_run_id == prompt_run.id
    assert result.error is None

    orchestration_mocks["knowledge_retrieval_service"].retrieve_for_message.assert_awaited_once_with(
        session,
        tenant_id=tenant_id,
        business_id=business.id,
        query_text="Book tomorrow?",
    )
    build_kwargs = (
        orchestration_mocks["prompt_builder_service"]
        .build_reply_to_customer.call_args.kwargs
    )
    assert build_kwargs["configuration"] == configuration
    assert build_kwargs["knowledge"] == knowledge
    assert build_kwargs["history"] == history
    assert build_kwargs["current_customer_message"] == "Book tomorrow?"
    assert build_kwargs["operator_business_context"] is None
    assert build_kwargs["greeting_policy"].mode is GreetingMode.FIRST_CONTACT
    assert build_kwargs["alpstein_product_behavior_enabled"] is False
    assert build_kwargs["conversation_intent"] is None


@pytest.mark.anyio
async def test_generate_reply_enables_intent_policy_for_alpstein_demo(
    orchestrator: AiReplyOrchestrationService,
    orchestration_mocks,
):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    business.external_id = "alpstein_ai_demo_001"
    _wire_success_mocks(
        orchestration_mocks,
        tenant_id=tenant_id,
        business_id=business.id,
        template_id=template_id,
    )

    session = AsyncMock()
    await orchestrator.generate_reply(
        session,
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        customer_message_text="сколько стоит",
        channel="telegram",
        template_key="customer_reply_v1",
    )

    build_kwargs = (
        orchestration_mocks["prompt_builder_service"]
        .build_reply_to_customer.call_args.kwargs
    )
    assert build_kwargs["alpstein_product_behavior_enabled"] is True
    assert build_kwargs["conversation_intent"] is not None
    assert build_kwargs["conversation_intent"].intent is ConversationIntent.PRICING_INTEREST


@pytest.mark.anyio
async def test_generate_reply_uses_tenant_language_as_default_before_telegram_language(
    orchestrator: AiReplyOrchestrationService,
    orchestration_mocks,
):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    business.external_id = "orange-park"
    configuration = _configuration_bundle(
        tenant_id,
        business.id,
        template_id,
        behavior=TenantBehaviorConfig(present=True, language="uk"),
    )
    _wire_success_mocks(
        orchestration_mocks,
        tenant_id=tenant_id,
        business_id=business.id,
        template_id=template_id,
        configuration=configuration,
    )

    await orchestrator.generate_reply(
        AsyncMock(),
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        customer_message_text="👍",
        channel="telegram",
        template_key="customer_reply_v1",
        raw_payload={"language_code": "ru"},
    )

    build_kwargs = (
        orchestration_mocks["prompt_builder_service"]
        .build_reply_to_customer.call_args.kwargs
    )
    assert build_kwargs["configuration"].behavior.language == "uk"
    assert build_kwargs["greeting_policy"].reply_language_code == "uk"
    assert build_kwargs["greeting_policy"].reply_language_name == "Ukrainian"


@pytest.mark.anyio
async def test_generate_reply_passes_assembled_prompt_to_gateway(
    orchestrator: AiReplyOrchestrationService,
    orchestration_mocks,
):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    assembled = _assembled_prompt()
    _wire_success_mocks(
        orchestration_mocks,
        tenant_id=tenant_id,
        business_id=business.id,
        template_id=template_id,
        assembled=assembled,
    )

    await orchestrator.generate_reply(
        AsyncMock(),
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        customer_message_text="Hi",
        channel="whatsapp",
        template_key="customer_reply_v1",
    )

    gateway_prompt = orchestration_mocks["ai_gateway_service"].complete.await_args.args[0]
    assert gateway_prompt is assembled


@pytest.mark.anyio
async def test_generate_reply_gateway_success_creates_successful_prompt_run(
    orchestrator: AiReplyOrchestrationService,
    orchestration_mocks,
):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    configuration = _configuration_bundle(tenant_id, business.id, template_id)
    _wire_success_mocks(
        orchestration_mocks,
        tenant_id=tenant_id,
        business_id=business.id,
        template_id=template_id,
        configuration=configuration,
    )

    await orchestrator.generate_reply(
        AsyncMock(),
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        customer_message_text="Hi",
        channel="whatsapp",
        template_key="customer_reply_v1",
    )

    kwargs = orchestration_mocks["prompt_run_service"].create_prompt_run.await_args.kwargs
    assert kwargs["result"] == "AI reply text"
    assert kwargs["error"] is None
    assert kwargs["prompt_template_id"] == template_id
    assert kwargs["prompt_version"] == "1"
    assert kwargs["final_prompt"] is not None
    assert "platform_system" in kwargs["final_prompt"]
    assert kwargs["metadata"] is not None
    assert kwargs["metadata"]["obs_schema_version"] == "1.0"
    assert "correlation_id" in kwargs["metadata"]


@pytest.mark.anyio
async def test_generate_reply_gateway_failure_creates_failure_prompt_run(
    orchestrator: AiReplyOrchestrationService,
    orchestration_mocks,
):
    tenant_id, business, conversation, message, template_id = _scope_entities()
    configuration = _configuration_bundle(tenant_id, business.id, template_id)
    prompt_run = SimpleNamespace(id=uuid.uuid4())

    orchestration_mocks["ai_configuration_service"].load_for_message = AsyncMock(
        return_value=configuration
    )
    orchestration_mocks["knowledge_retrieval_service"].retrieve_for_message = AsyncMock(
        return_value=KnowledgeRetrievalResult.empty()
    )
    orchestration_mocks["message_service"].load_recent_conversation_history = AsyncMock(
        return_value=ConversationHistory.empty()
    )
    orchestration_mocks["prompt_builder_service"].build_reply_to_customer = MagicMock(
        return_value=_assembled_prompt()
    )
    orchestration_mocks["ai_gateway_service"].complete = AsyncMock(
        return_value=AiGatewayResult(
            text=None,
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=None,
            output_tokens=None,
            latency_ms=30_000,
            error="AI provider request timed out",
        )
    )
    orchestration_mocks["prompt_run_service"].create_prompt_run = AsyncMock(
        return_value=prompt_run
    )
    _mock_langfuse_trace_context(orchestration_mocks)

    result, _langfuse_trace_id = await orchestrator.generate_reply(
        AsyncMock(),
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        customer_message_text="Hi",
        channel="whatsapp",
        template_key="customer_reply_v1",
    )

    assert result.is_success is False
    assert result.text is None
    assert result.error == "AI provider request timed out"

    kwargs = orchestration_mocks["prompt_run_service"].create_prompt_run.await_args.kwargs
    assert kwargs["result"] is None
    assert kwargs["error"] == "AI provider request timed out"
    orchestration_mocks["prompt_run_service"].create_prompt_run.assert_awaited_once()


@pytest.mark.anyio
async def test_ai_reply_result_does_not_expose_final_prompt():
    field_names = {field.name for field in fields(AiReplyResult)}
    assert "final_prompt" not in field_names


def test_orchestrator_module_does_not_import_openai_directly():
    import app.services.ai_reply_orchestration_service as module

    source_path = module.__file__
    assert source_path is not None
    source = open(source_path, encoding="utf-8").read().lower()
    assert "import openai" not in source
    assert "from openai" not in source
    assert "ai_gateway._openai" not in source
    assert "httpx" not in source


def _wire_success_mocks(
    mocks: dict,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    template_id: uuid.UUID,
    assembled: AssembledPrompt | None = None,
    configuration: AiConfigurationBundle | None = None,
) -> None:
    configuration = configuration or _configuration_bundle(
        tenant_id,
        business_id,
        template_id,
    )
    assembled = assembled or _assembled_prompt()
    prompt_run = SimpleNamespace(id=uuid.uuid4())

    mocks["ai_configuration_service"].load_for_message = AsyncMock(return_value=configuration)
    mocks["knowledge_retrieval_service"].retrieve_for_message = AsyncMock(
        return_value=KnowledgeRetrievalResult.empty()
    )
    mocks["message_service"].load_recent_conversation_history = AsyncMock(
        return_value=ConversationHistory.empty()
    )
    mocks["prompt_builder_service"].build_reply_to_customer = MagicMock(return_value=assembled)
    mocks["ai_gateway_service"].complete = AsyncMock(
        return_value=AiGatewayResult(
            text="AI reply text",
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=50,
            output_tokens=10,
            latency_ms=200,
            error=None,
        )
    )
    mocks["prompt_run_service"].create_prompt_run = AsyncMock(return_value=prompt_run)
    _mock_langfuse_trace_context(mocks)
