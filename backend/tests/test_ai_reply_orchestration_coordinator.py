import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.ai_reply import AiReplyResult
from app.services.ai_reply_orchestration_coordinator import (
    REASON_AI_CHAIN_EXECUTED,
    REASON_DUPLICATE_INCOMING_MESSAGE,
    AiReplyOrchestrationCoordinator,
)


@pytest.fixture
def orchestration_service() -> MagicMock:
    service = MagicMock()
    service.generate_reply = AsyncMock(
        return_value=(
            AiReplyResult(
                text="AI reply",
                is_success=True,
                prompt_run_id=uuid.uuid4(),
                model="gpt-4o-mini",
                provider="openai",
                error=None,
            ),
            None,
        )
    )
    return service


@pytest.fixture
def coordinator(orchestration_service: MagicMock) -> AiReplyOrchestrationCoordinator:
    return AiReplyOrchestrationCoordinator(
        orchestration_service=orchestration_service,
    )


def _invoke_kwargs():
    tenant_id = uuid.uuid4()
    business = SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_id)
    conversation = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business.id,
    )
    message = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
    )
    return {
        "session": AsyncMock(),
        "is_duplicate": False,
        "tenant_id": tenant_id,
        "business": business,
        "conversation": conversation,
        "message": message,
        "customer_message_text": "Hello",
        "channel": "whatsapp",
        "template_key": "customer_reply_v1",
    }


@pytest.mark.anyio
async def test_duplicate_incoming_message_skips_ai_chain(
    coordinator: AiReplyOrchestrationCoordinator,
    orchestration_service: MagicMock,
):
    kwargs = _invoke_kwargs()
    kwargs["is_duplicate"] = True

    outcome = await coordinator.execute_for_incoming_message(**kwargs)

    orchestration_service.generate_reply.assert_not_awaited()
    assert outcome.is_duplicate is True
    assert outcome.ai_executed is False
    assert outcome.reason == REASON_DUPLICATE_INCOMING_MESSAGE
    assert outcome.ai_reply is None


@pytest.mark.anyio
async def test_duplicate_incoming_message_skips_prompt_run_via_orchestration(
    coordinator: AiReplyOrchestrationCoordinator,
    orchestration_service: MagicMock,
):
    kwargs = _invoke_kwargs()
    kwargs["is_duplicate"] = True

    await coordinator.execute_for_incoming_message(**kwargs)

    orchestration_service.generate_reply.assert_not_awaited()


@pytest.mark.anyio
async def test_non_duplicate_path_executes_orchestration(
    coordinator: AiReplyOrchestrationCoordinator,
    orchestration_service: MagicMock,
):
    kwargs = _invoke_kwargs()

    outcome = await coordinator.execute_for_incoming_message(**kwargs)

    orchestration_service.generate_reply.assert_awaited_once()
    assert outcome.is_duplicate is False
    assert outcome.ai_executed is True
    assert outcome.reason == REASON_AI_CHAIN_EXECUTED
    assert outcome.ai_reply is not None
    assert outcome.ai_reply.text == "AI reply"


@pytest.mark.anyio
async def test_non_duplicate_passes_scope_to_orchestration(
    coordinator: AiReplyOrchestrationCoordinator,
    orchestration_service: MagicMock,
):
    kwargs = _invoke_kwargs()

    await coordinator.execute_for_incoming_message(**kwargs)

    call_kwargs = orchestration_service.generate_reply.await_args.kwargs
    assert call_kwargs["tenant_id"] == kwargs["tenant_id"]
    assert call_kwargs["business"] is kwargs["business"]
    assert call_kwargs["conversation"] is kwargs["conversation"]
    assert call_kwargs["message"] is kwargs["message"]
    assert call_kwargs["customer_message_text"] == "Hello"
    assert call_kwargs["channel"] == "whatsapp"
    assert call_kwargs["template_key"] == "customer_reply_v1"
