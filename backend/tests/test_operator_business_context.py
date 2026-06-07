"""T14-OC-2 — operator_business_context webhook field and Prompt Builder overlay."""

from __future__ import annotations

import json
import uuid
from dataclasses import replace
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.main import app
from app.schemas.webhook import (
    OPERATOR_BUSINESS_CONTEXT_MAX_LENGTH,
    NormalizedWebhookMessageRequest,
)
from app.schemas.webhook_response import FORBIDDEN_WEBHOOK_RESPONSE_FIELDS
from app.services.lead_signal_detection_service import LeadSignalDetectionService
from app.schemas.ai_configuration import (
    AiConfigurationBundle,
    PlatformPromptTemplateConfig,
    TenantBehaviorConfig,
    TenantBusinessContextConfig,
    TenantChannelRulesConfig,
)
from app.schemas.conversation_context import ConversationHistory, ConversationHistoryMessage
from app.schemas.knowledge import KnowledgeRetrievalResult, KnowledgeSnippet
from app.services.prompt_builder_service import (
    OPERATOR_BUSINESS_NOTES_LABEL,
    PromptBuilderService,
)
@pytest.fixture
def tenant_scope() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


@pytest.fixture
def full_configuration(tenant_scope: tuple[uuid.UUID, uuid.UUID]) -> AiConfigurationBundle:
    tenant_id, business_id = tenant_scope
    return AiConfigurationBundle(
        tenant_id=tenant_id,
        business_id=business_id,
        channel="whatsapp",
        template_key="customer_reply_v1",
        platform_template=PlatformPromptTemplateConfig(
            id=uuid.uuid4(),
            template_key="customer_reply_v1",
            template_name="Customer reply",
            version="1",
            system_prompt="Platform safety and role rules.",
        ),
        business_context=TenantBusinessContextConfig(
            present=True,
            business_description="Barbershop in Zurich.",
            city="Zurich",
        ),
        behavior=TenantBehaviorConfig(present=True, tone="friendly", language="de"),
        channel_rules=TenantChannelRulesConfig(
            present=True,
            channel="whatsapp",
            response_style="short",
        ),
    )


@pytest.fixture
def knowledge_result() -> KnowledgeRetrievalResult:
    return KnowledgeRetrievalResult(
        snippets=(
            KnowledgeSnippet(
                id=uuid.uuid4(),
                source_type="faq",
                title="Opening hours",
                content="Mon-Fri 09:00-18:00",
            ),
        )
    )


@pytest.fixture
def conversation_history() -> ConversationHistory:
    return ConversationHistory(
        messages=(
            ConversationHistoryMessage(
                sender_type="customer",
                message_text="Hello",
                created_at=datetime(2026, 5, 1, 10, 0, 0),
            ),
        )
    )


def _valid_payload(**overrides) -> dict:
    payload = {
        "business_id": "demo_barbershop_001",
        "channel": "whatsapp",
        "customer": {"phone": "+41790000000"},
        "message": {"text": "I'd like a haircut next week please."},
    }
    payload.update(overrides)
    return payload


def test_request_accepts_operator_business_context():
    notes = "Pop-up hours Sat 10:00–14:00 only."
    request = NormalizedWebhookMessageRequest.model_validate(
        _valid_payload(operator_business_context=notes)
    )

    assert request.operator_business_context == notes


def test_whitespace_only_operator_context_normalizes_to_none():
    request = NormalizedWebhookMessageRequest.model_validate(
        _valid_payload(operator_business_context="   \n\t  ")
    )

    assert request.operator_business_context is None


def test_empty_string_operator_context_normalizes_to_none():
    request = NormalizedWebhookMessageRequest.model_validate(
        _valid_payload(operator_business_context="")
    )

    assert request.operator_business_context is None


def test_operator_context_over_max_length_rejected():
    too_long = "x" * (OPERATOR_BUSINESS_CONTEXT_MAX_LENGTH + 1)

    with pytest.raises(ValidationError):
        NormalizedWebhookMessageRequest.model_validate(
            _valid_payload(operator_business_context=too_long)
        )


def test_prompt_includes_labeled_operator_notes_after_db_profile(
    full_configuration,
    knowledge_result,
    conversation_history,
):
    operator_notes = "Student discount 10% this week."
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Hello",
        operator_business_context=operator_notes,
    )
    business_section = next(
        s for s in prompt.sections if s.section_id == "business_context_source_of_truth"
    )

    profile_index = business_section.content.index("Barbershop in Zurich.")
    notes_index = business_section.content.index(OPERATOR_BUSINESS_NOTES_LABEL)
    assert profile_index < notes_index
    assert operator_notes in business_section.content


def test_prompt_omits_operator_block_when_null(
    full_configuration,
    knowledge_result,
    conversation_history,
):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Hello",
        operator_business_context=None,
    )
    business_section = next(
        s for s in prompt.sections if s.section_id == "business_context_source_of_truth"
    )

    assert OPERATOR_BUSINESS_NOTES_LABEL not in business_section.content


def test_prompt_operator_notes_only_when_no_db_profile(
    full_configuration,
    knowledge_result,
    conversation_history,
):
    config = replace(
        full_configuration,
        business_context=replace(
            full_configuration.business_context,
            present=False,
        ),
    )
    operator_notes = "Temporary pop-up location at Bahnhofstrasse 1."
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=config,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Where are you?",
        operator_business_context=operator_notes,
    )
    business_section = next(
        s for s in prompt.sections if s.section_id == "business_context_source_of_truth"
    )

    assert OPERATOR_BUSINESS_NOTES_LABEL in business_section.content
    assert operator_notes in business_section.content
    assert "description: Barbershop" not in business_section.content
    assert "Barbershop in Zurich." not in business_section.content


def test_operator_context_stays_in_tenant_business_section_not_system(
    full_configuration,
    knowledge_result,
    conversation_history,
):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Hi",
        operator_business_context="Weekend hours extended.",
    )
    sections = {s.section_id: s for s in prompt.sections}

    assert OPERATOR_BUSINESS_NOTES_LABEL in sections[
        "business_context_source_of_truth"
    ].content
    assert "Weekend hours extended." in sections[
        "business_context_source_of_truth"
    ].content
    assert OPERATOR_BUSINESS_NOTES_LABEL not in sections["platform_system"].content
    assert "Weekend hours extended." not in sections["task_instructions"].content
    assert sections["business_context_source_of_truth"].kind == "data"


def test_lead_detection_ignores_operator_context_keywords():
    service = LeadSignalDetectionService()
    result = service.detect(
        customer_message_text="I'd like a haircut next Tuesday at 2pm, thanks.",
    )

    assert result.urgent_detected is False
    assert result.handoff_requested is False
    assert result.matched_keywords == []


def test_webhook_success_response_never_exposes_operator_business_context():
    assert "operator_business_context" in FORBIDDEN_WEBHOOK_RESPONSE_FIELDS


@pytest.fixture
def configure_webhook_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "oc2-response-token"
    monkeypatch.setattr("app.core.config.settings.n8n_backend_api_token", token)
    monkeypatch.setattr("app.api.webhook_auth.settings.n8n_backend_api_token", token)


@pytest.mark.anyio
async def test_http_webhook_response_omits_operator_business_context(
    configure_webhook_token,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.api.routes import webhook as webhook_route
    from app.db.session import get_db_session
    conversation = MagicMock()
    conversation.id = uuid.uuid4()
    conversation.status = "open"
    message = MagicMock()
    message.id = uuid.uuid4()
    session = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def _override_session():
        yield session

    app.dependency_overrides[get_db_session] = _override_session

    service = MagicMock()
    flow = MagicMock()
    flow.id = uuid.uuid4()
    flow.flow_key = "default"
    service.process_incoming_message = AsyncMock(
        return_value=MagicMock(
            conversation=conversation,
            message=message,
            flow=flow,
            is_duplicate=False,
            reply_to_customer="Thanks for reaching out.",
            lead_created=False,
            lead_updated=False,
            notify_owner=False,
            lead=None,
            notification=None,
        )
    )
    monkeypatch.setattr(webhook_route, "webhook_message_service", service)

    payload = _valid_payload(
        operator_business_context="Secret promo: URGENT manager call me ASAP",
        message={"text": "Normal booking question"},
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/webhook/message",
                json=payload,
                headers={"X-Alpstein-Webhook-Token": "oc2-response-token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    dumped = json.dumps(body)
    assert "operator_business_context" not in dumped
    assert "OPERATOR BUSINESS NOTES" not in dumped
