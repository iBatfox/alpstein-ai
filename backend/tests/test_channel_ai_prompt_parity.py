"""Telegram and Instagram must share the same AI orchestration path and prompt input."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.assembled_prompt import AssembledPrompt, AssembledPromptSection
from app.schemas.conversation_context import ConversationHistory
from app.schemas.knowledge import KnowledgeRetrievalResult
from app.services.ai_reply_orchestration_coordinator import (
    AiReplyOrchestrationCoordinator,
    LOG_AI_GENERATION_STARTED,
)
from app.services.ai_reply_orchestration_service import AiReplyOrchestrationService


CUSTOMER_TEXT = "Сколько стоит бот для Instagram?"


def _assembled_prompt_with_customer_text() -> AssembledPrompt:
    return AssembledPrompt(
        task="reply_to_customer",
        sections=(
            AssembledPromptSection(
                section_id="current_customer_message",
                label="CURRENT CUSTOMER MESSAGE (reference data)",
                content=f"[CURRENT CUSTOMER MESSAGE (reference data)]\n{CUSTOMER_TEXT}",
                kind="data",
            ),
        ),
    )


def _build_orchestrator() -> tuple[AiReplyOrchestrationService, dict[str, MagicMock]]:
    mocks = {
        "ai_configuration_service": MagicMock(),
        "knowledge_retrieval_service": MagicMock(),
        "message_service": MagicMock(),
        "prompt_builder_service": MagicMock(),
        "ai_gateway_service": MagicMock(),
        "prompt_run_service": MagicMock(),
        "greeting_policy_service": MagicMock(),
        "conversation_intent_service": MagicMock(),
        "langfuse_tracing_service": MagicMock(),
    }
    orchestrator = AiReplyOrchestrationService(**mocks)
    return orchestrator, mocks


@pytest.mark.anyio
@pytest.mark.parametrize("channel", ["telegram", "instagram"])
async def test_telegram_and_instagram_share_generate_reply_path(channel: str) -> None:
    orchestrator, mocks = _build_orchestrator()
    tenant_id = uuid.uuid4()
    business = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        external_id="alpstein_ai_demo_001",
    )
    conversation = SimpleNamespace(id=uuid.uuid4())
    message = SimpleNamespace(id=uuid.uuid4())

    mocks["ai_configuration_service"].load_for_message = AsyncMock(
        return_value=MagicMock(
            template=MagicMock(id=uuid.uuid4(), version="1"),
            behavior=MagicMock(),
        )
    )
    mocks["knowledge_retrieval_service"].retrieve_for_message = AsyncMock(
        return_value=KnowledgeRetrievalResult.empty()
    )
    mocks["message_service"].load_recent_conversation_history = AsyncMock(
        return_value=ConversationHistory.empty()
    )
    mocks["greeting_policy_service"].resolve = MagicMock(return_value=MagicMock())
    mocks["conversation_intent_service"].resolve = MagicMock(return_value=None)
    mocks["prompt_builder_service"].build_reply_to_customer = MagicMock(
        return_value=_assembled_prompt_with_customer_text()
    )
    mocks["ai_gateway_service"].complete = AsyncMock(
        return_value=MagicMock(
            text="Shared AI path reply",
            succeeded=True,
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=10,
            output_tokens=12,
            error=None,
        )
    )
    mocks["prompt_run_service"].create_prompt_run = AsyncMock(
        return_value=SimpleNamespace(id=uuid.uuid4())
    )
    trace_cm = AsyncMock()
    trace_cm.__aenter__.return_value = MagicMock(langfuse_trace_id=None)
    trace_cm.__aexit__.return_value = None
    mocks["langfuse_tracing_service"].trace_ai_reply.return_value = trace_cm

    result, _trace_id = await orchestrator.generate_reply(
        AsyncMock(),
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message=message,
        customer_message_text=CUSTOMER_TEXT,
        channel=channel,
        template_key="customer_reply_v1",
        operator_business_context="Alpstein AI demo business.",
    )

    build_kwargs = mocks["prompt_builder_service"].build_reply_to_customer.call_args.kwargs
    assert build_kwargs["current_customer_message"] == CUSTOMER_TEXT
    assert build_kwargs["operator_business_context"] == "Alpstein AI demo business."
    assert result.text == "Shared AI path reply"
    mocks["ai_gateway_service"].complete.assert_awaited_once()


@pytest.mark.anyio
async def test_coordinator_logs_same_generation_event_for_both_channels(
    caplog: pytest.LogCaptureFixture,
) -> None:
    orchestration_service = MagicMock()
    orchestration_service.generate_reply = AsyncMock(
        return_value=(
            MagicMock(
                text="Reply",
                is_success=True,
                prompt_run_id=uuid.uuid4(),
                model="gpt-4o-mini",
                provider="openai",
                error=None,
            ),
            None,
        )
    )
    coordinator = AiReplyOrchestrationCoordinator(orchestration_service=orchestration_service)
    caplog.set_level("INFO", logger="app.services.ai_reply_orchestration_coordinator")

    for channel in ("telegram", "instagram"):
        await coordinator.execute_for_incoming_message(
            AsyncMock(),
            is_duplicate=False,
            tenant_id=uuid.uuid4(),
            business=SimpleNamespace(id=uuid.uuid4(), external_id="alpstein_ai_demo_001"),
            conversation=SimpleNamespace(id=uuid.uuid4()),
            message=SimpleNamespace(id=uuid.uuid4()),
            customer_message_text=CUSTOMER_TEXT,
            channel=channel,
            template_key="customer_reply_v1",
            operator_business_context="Alpstein AI demo business.",
        )

    started_logs = [
        record
        for record in caplog.records
        if record.getMessage() == LOG_AI_GENERATION_STARTED
    ]
    assert len(started_logs) == 2
    channels = {record.__dict__.get("channel") for record in started_logs}
    assert channels == {"telegram", "instagram"}
