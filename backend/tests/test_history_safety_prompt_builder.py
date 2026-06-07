"""HF-1 — history safety preamble in §7 conversation_history."""

import uuid
from datetime import datetime

import pytest

from app.schemas.ai_configuration import (
    AiConfigurationBundle,
    PlatformPromptTemplateConfig,
    TenantBehaviorConfig,
    TenantBusinessContextConfig,
    TenantChannelRulesConfig,
)
from app.schemas.assembled_prompt import CANONICAL_SECTION_ORDER
from app.schemas.conversation_context import ConversationHistory, ConversationHistoryMessage
from app.schemas.knowledge import KnowledgeRetrievalResult
from app.services.history_safety_prompt_instructions import (
    AI_HISTORY_SENDER_LABEL,
    HISTORY_SAFETY_HEADER,
)
from app.services.prompt_builder_service import PromptBuilderService


@pytest.fixture
def configuration() -> AiConfigurationBundle:
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    return AiConfigurationBundle(
        tenant_id=tenant_id,
        business_id=business_id,
        channel="telegram",
        template_key="customer_reply_v1",
        platform_template=PlatformPromptTemplateConfig(
            id=uuid.uuid4(),
            template_key="customer_reply_v1",
            template_name="Customer reply",
            version="1",
            system_prompt="Platform safety rules.",
        ),
        business_context=TenantBusinessContextConfig(
            present=True,
            business_description="Current business profile.",
        ),
        behavior=TenantBehaviorConfig(present=True, language=None),
        channel_rules=TenantChannelRulesConfig.missing("telegram"),
    )


def _section_map(prompt):
    return {section.section_id: section for section in prompt.sections}


def _history_content(prompt) -> str:
    return _section_map(prompt)["conversation_history"].content


def test_history_safety_preamble_when_history_exists(configuration):
    history = ConversationHistory(
        messages=(
            ConversationHistoryMessage(
                sender_type="customer",
                message_text="What is your email?",
                created_at=datetime(2026, 5, 1, 10, 0, 0),
            ),
        )
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=history,
        current_customer_message="Thanks",
    )
    content = _history_content(prompt)

    assert HISTORY_SAFETY_HEADER in content
    assert "current context wins" in content
    assert "dialogue context only" in content
    assert content.index(HISTORY_SAFETY_HEADER) < content.index("customer:")


def test_no_history_safety_preamble_when_history_empty(configuration):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="Hello",
    )
    history_section = _section_map(prompt)["conversation_history"]
    assert "(not provided)" in history_section.content
    assert HISTORY_SAFETY_HEADER not in history_section.content


def test_stale_assistant_contact_does_not_override_operator_context(configuration):
    history = ConversationHistory(
        messages=(
            ConversationHistoryMessage(
                sender_type="ai",
                message_text="Contact us at old@example.com",
                created_at=datetime(2026, 5, 1, 10, 0, 0),
            ),
        )
    )
    operator_notes = "Business contact: new@example.com (exact spelling)."
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=history,
        current_customer_message="What is your email?",
        operator_business_context=operator_notes,
    )
    business = _section_map(prompt)["business_context_source_of_truth"].content
    history = _history_content(prompt)

    assert "new@example.com" in business
    assert "OPERATOR BUSINESS NOTES" in business
    assert "old@example.com" not in history
    assert "historical assistant reply omitted" in history
    assert f"{AI_HISTORY_SENDER_LABEL}:" in history
    assert "current context wins" in history
    assert "Do not reuse contacts" in history
    assert prompt.section_ids().index(
        "business_context_source_of_truth"
    ) < prompt.section_ids().index("conversation_history")


def test_stale_assistant_pricing_does_not_override_current_context(configuration):
    history = ConversationHistory(
        messages=(
            ConversationHistoryMessage(
                sender_type="ai",
                message_text="Haircut costs 35 CHF.",
                created_at=datetime(2026, 5, 1, 10, 0, 0),
            ),
        )
    )
    configuration = AiConfigurationBundle(
        tenant_id=configuration.tenant_id,
        business_id=configuration.business_id,
        channel=configuration.channel,
        template_key=configuration.template_key,
        platform_template=configuration.platform_template,
        business_context=TenantBusinessContextConfig(
            present=True,
            business_description="Pricing is quoted per project after scope review.",
        ),
        behavior=configuration.behavior,
        channel_rules=configuration.channel_rules,
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=history,
        current_customer_message="How much?",
        operator_business_context="Do not quote fixed prices in chat.",
    )
    business = _section_map(prompt)["business_context_source_of_truth"].content
    history_content = _history_content(prompt)

    assert "35 CHF" not in history_content
    assert "Do not reuse" in history_content and "prices" in history_content
    assert "historical assistant reply omitted" in history_content
    assert "quoted per project" in business
    assert prompt.section_ids().index(
        "business_context_source_of_truth"
    ) < prompt.section_ids().index("conversation_history")


def test_customer_message_dedupe_still_works(configuration):
    duplicate = "Same text"
    history = ConversationHistory(
        messages=(
            ConversationHistoryMessage(
                sender_type="customer",
                message_text="Earlier",
                created_at=datetime(2026, 5, 1, 9, 0, 0),
            ),
            ConversationHistoryMessage(
                sender_type="customer",
                message_text=duplicate,
                created_at=datetime(2026, 5, 1, 9, 5, 0),
            ),
        )
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=history,
        current_customer_message=duplicate,
    )
    history_content = _history_content(prompt)

    assert "customer: Earlier" in history_content
    assert duplicate not in history_content
    assert duplicate in _section_map(prompt)["current_customer_message"].content


def test_canonical_section_order_unchanged(configuration):
    history = ConversationHistory(
        messages=(
            ConversationHistoryMessage(
                sender_type="customer",
                message_text="Hi",
                created_at=datetime(2026, 5, 1, 10, 0, 0),
            ),
        )
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=history,
        current_customer_message="Follow-up",
        operator_business_context="Operator note.",
    )
    assert prompt.section_ids() == CANONICAL_SECTION_ORDER
