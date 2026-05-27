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
from app.schemas.conversation_context import ConversationHistory, ConversationHistoryMessage
from app.schemas.conversation_intent import ConversationIntent, ConversationIntentResolution
from app.schemas.greeting import GreetingMode, GreetingPolicy
from app.schemas.knowledge import KnowledgeRetrievalResult
from app.services.prompt_builder_service import PromptBuilderService


@pytest.fixture
def barbershop_configuration() -> AiConfigurationBundle:
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
            business_description="Neighborhood barbershop in Zurich.",
        ),
        behavior=TenantBehaviorConfig(
            present=True,
            language="de",
            ask_for_name=True,
        ),
        channel_rules=TenantChannelRulesConfig.missing("telegram"),
    )


@pytest.fixture
def alpstein_configuration(barbershop_configuration) -> AiConfigurationBundle:
    return AiConfigurationBundle(
        tenant_id=barbershop_configuration.tenant_id,
        business_id=barbershop_configuration.business_id,
        channel=barbershop_configuration.channel,
        template_key=barbershop_configuration.template_key,
        platform_template=barbershop_configuration.platform_template,
        business_context=TenantBusinessContextConfig(
            present=True,
            business_description="Alpstein AI demo.",
        ),
        behavior=TenantBehaviorConfig(present=True, language=None),
        channel_rules=barbershop_configuration.channel_rules,
    )


def _task_content(prompt) -> str:
    return next(s for s in prompt.sections if s.section_id == "task_instructions").content


@pytest.mark.parametrize(
    ("language_code", "language_name", "sample_phrase"),
    [
        ("de", "German", "technical pre-sales"),
        ("en", "English", "technical pre-sales"),
        ("ru", "Russian", "technical pre-sales"),
        ("fr", "French", "technical pre-sales"),
        ("it", "Italian", "technical pre-sales"),
        ("es", "Spanish", "technical pre-sales"),
        ("uk", "Ukrainian", "technical pre-sales"),
    ],
)
def test_alpstein_first_contact_includes_product_intro(
    alpstein_configuration,
    language_code: str,
    language_name: str,
    sample_phrase: str,
):
    policy = GreetingPolicy(
        mode=GreetingMode.FIRST_CONTACT,
        reply_language_code=language_code,
        reply_language_name=language_name,
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=alpstein_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="Hello",
        greeting_policy=policy,
        alpstein_product_behavior_enabled=True,
        conversation_intent=ConversationIntentResolution(
            intent=ConversationIntent.SOCIAL_GREETING,
            matched_rule="test",
        ),
    )
    task = _task_content(prompt)

    assert "GREETING ORCHESTRATION (first contact)" in task
    assert sample_phrase in task
    assert f"Reply in {language_name} ({language_code})" in task
    assert "Never say you only speak certain languages" in task


def test_generic_first_contact_excludes_alpstein_intro(barbershop_configuration):
    policy = GreetingPolicy(
        mode=GreetingMode.FIRST_CONTACT,
        reply_language_code="de",
        reply_language_name="German",
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=barbershop_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="Hello",
        greeting_policy=policy,
        alpstein_product_behavior_enabled=False,
    )
    task = _task_content(prompt)

    assert "GREETING ORCHESTRATION (first contact)" in task
    assert "I am your Alpstein AI assistant" not in task
    assert "tenant business reference data only" in task


def test_alpstein_follow_up_omits_full_intro(alpstein_configuration):
    policy = GreetingPolicy(
        mode=GreetingMode.FOLLOW_UP,
        reply_language_code="ru",
        reply_language_name="Russian",
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=alpstein_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory(
            messages=(
                ConversationHistoryMessage(
                    sender_type="ai",
                    message_text="Prior reply",
                    created_at=datetime(2026, 5, 1, 10, 0, 0),
                ),
            )
        ),
        current_customer_message="Спасибо",
        greeting_policy=policy,
        alpstein_product_behavior_enabled=True,
        conversation_intent=ConversationIntentResolution(
            intent=ConversationIntent.SOCIAL_GREETING,
            matched_rule="test",
        ),
    )
    task = _task_content(prompt)

    assert "GREETING ORCHESTRATION (follow-up)" in task
    assert "Do not repeat the full Alpstein AI introduction" in task
    assert "GREETING ORCHESTRATION (first contact)" not in task
