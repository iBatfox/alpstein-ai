import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.models.business_context_builder import (
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_USER,
    BusinessContextBuilderMessage,
)
from app.schemas.ai_gateway import AiGatewayResult
from app.services.business_context_builder_ai_service import BusinessContextBuilderAiService
from app.services.business_context_builder_constants import STEP_BUSINESS_DESCRIPTION


@pytest.fixture
def tenant_scope() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


@pytest.fixture
def messages(tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID]) -> list[BusinessContextBuilderMessage]:
    _, tenant_id, business_id = tenant_scope
    session_id = tenant_scope[0]
    return [
        BusinessContextBuilderMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
            role=MESSAGE_ROLE_ASSISTANT,
            content="What is your company name?",
        ),
        BusinessContextBuilderMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
            role=MESSAGE_ROLE_USER,
            content="Alpstein Services GmbH",
        ),
    ]


@pytest.mark.anyio
async def test_ai_service_returns_gateway_text_when_successful(
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
    messages: list[BusinessContextBuilderMessage],
):
    session_id, tenant_id, business_id = tenant_scope
    gateway = AsyncMock()
    gateway.complete = AsyncMock(
        return_value=AiGatewayResult(
            text="What industry are you in?",
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
            error=None,
        )
    )
    service = BusinessContextBuilderAiService(
        app_settings=Settings(
            openai_api_key="test-key",
            bcb_ai_enabled=True,
        ),
        ai_gateway_service=gateway,
    )

    question = await service.generate_next_question(
        session_id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        next_step=STEP_BUSINESS_DESCRIPTION,
        messages=messages,
        fallback_question="What does your company do?",
    )

    assert question == "What industry are you in?"
    gateway.complete.assert_awaited_once()


@pytest.mark.anyio
async def test_ai_service_uses_fallback_when_gateway_fails(
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
    messages: list[BusinessContextBuilderMessage],
):
    session_id, tenant_id, business_id = tenant_scope
    gateway = AsyncMock()
    gateway.complete = AsyncMock(
        return_value=AiGatewayResult(
            text=None,
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=None,
            output_tokens=None,
            latency_ms=50,
            error="AI provider request timed out",
        )
    )
    service = BusinessContextBuilderAiService(
        app_settings=Settings(openai_api_key="test-key", bcb_ai_enabled=True),
        ai_gateway_service=gateway,
    )

    question = await service.generate_next_question(
        session_id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        next_step=STEP_BUSINESS_DESCRIPTION,
        messages=messages,
        fallback_question="What does your company do?",
    )

    assert question == "What does your company do?"


@pytest.mark.anyio
async def test_ai_service_uses_fallback_when_disabled(
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
    messages: list[BusinessContextBuilderMessage],
):
    session_id, tenant_id, business_id = tenant_scope
    gateway = AsyncMock()
    service = BusinessContextBuilderAiService(
        app_settings=Settings(openai_api_key="test-key", bcb_ai_enabled=False),
        ai_gateway_service=gateway,
    )

    question = await service.generate_next_question(
        session_id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        next_step=STEP_BUSINESS_DESCRIPTION,
        messages=messages,
        fallback_question="What does your company do?",
    )

    assert question == "What does your company do?"
    gateway.complete.assert_not_awaited()


@pytest.mark.anyio
async def test_ai_service_uses_fallback_when_api_key_missing(
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
    messages: list[BusinessContextBuilderMessage],
):
    session_id, tenant_id, business_id = tenant_scope
    gateway = AsyncMock()
    service = BusinessContextBuilderAiService(
        app_settings=Settings(openai_api_key="", bcb_ai_enabled=True),
        ai_gateway_service=gateway,
    )

    question = await service.generate_next_question(
        session_id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        next_step=STEP_BUSINESS_DESCRIPTION,
        messages=messages,
        fallback_question="What does your company do?",
    )

    assert question == "What does your company do?"
    gateway.complete.assert_not_awaited()


def test_ai_service_module_has_no_db_imports():
    import app.services.business_context_builder_ai_service as module

    source = open(module.__file__, encoding="utf-8").read().lower()
    assert "sqlalchemy" not in source
    assert "asyncsession" not in source
    assert "app.db" not in source
