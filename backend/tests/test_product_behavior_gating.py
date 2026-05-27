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
from app.services.pre_sales_prompt_instructions import PRE_SALES_TASK_APPENDIX
from app.services.prompt_builder_service import (
    PLATFORM_TASK_REGISTRY,
    REPLY_TO_CUSTOMER_TASK,
    PromptBuilderService,
    _build_task_instructions_body,
)


@pytest.fixture
def barbershop_configuration() -> AiConfigurationBundle:
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
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
        channel_rules=TenantChannelRulesConfig.missing("whatsapp"),
    )


@pytest.fixture
def alpstein_configuration() -> AiConfigurationBundle:
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
            business_description="Alpstein AI builds AI assistants.",
        ),
        behavior=TenantBehaviorConfig(present=True, language=None),
        channel_rules=TenantChannelRulesConfig.missing("telegram"),
    )


def _task_content(prompt) -> str:
    return next(s for s in prompt.sections if s.section_id == "task_instructions").content


def test_alpstein_demo_receives_intro_intent_and_charter(alpstein_configuration):
    resolution = ConversationIntentResolution(
        intent=ConversationIntent.TECHNICAL_INTEREST,
        matched_rule="test",
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=alpstein_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="How does API work?",
        greeting_policy=GreetingPolicy(
            mode=GreetingMode.FIRST_CONTACT,
            reply_language_code="en",
            reply_language_name="English",
        ),
        alpstein_product_behavior_enabled=True,
        conversation_intent=resolution,
    )
    task = _task_content(prompt)

    assert "I am your Alpstein AI assistant" in task
    assert "technical pre-sales consultant" in task
    assert "CONVERSATION INTENT (active turn): technical_interest" in task
    assert "PRE-SALES CORE CHARTER" in task


def test_non_alpstein_excludes_alpstein_contamination(barbershop_configuration):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=barbershop_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="Hello",
        greeting_policy=GreetingPolicy(
            mode=GreetingMode.FIRST_CONTACT,
            reply_language_code="de",
            reply_language_name="German",
        ),
        alpstein_product_behavior_enabled=False,
        conversation_intent=None,
    )
    task = _task_content(prompt)

    assert "I am your Alpstein AI assistant" not in task
    assert "TECHNICAL PRE-SALES BEHAVIOR" not in task
    assert "PRE-SALES CORE CHARTER" not in task
    assert "CONVERSATION INTENT" not in task
    assert "Salesforce" not in task
    assert "Do not use Alpstein AI product messaging" in task


def test_non_alpstein_task_body_smaller_than_legacy_appendix_path():
    generic = _build_task_instructions_body(
        alpstein_product_behavior_enabled=False,
        conversation_intent=None,
        greeting_policy=GreetingPolicy(
            mode=GreetingMode.FOLLOW_UP,
            reply_language_code="en",
            reply_language_name="English",
        ),
    )
    legacy = (
        f"{PLATFORM_TASK_REGISTRY[REPLY_TO_CUSTOMER_TASK]}\n\n"
        f"{PRE_SALES_TASK_APPENDIX}"
    )
    assert len(generic) < len(legacy)


def test_greeting_lifecycle_works_for_non_alpstein(barbershop_configuration):
    follow_up = PromptBuilderService().build_reply_to_customer(
        configuration=barbershop_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory(
            messages=(
                ConversationHistoryMessage(
                    sender_type="ai",
                    message_text="Welcome",
                    created_at=datetime(2026, 5, 1, 10, 0, 0),
                ),
            )
        ),
        current_customer_message="Thanks",
        greeting_policy=GreetingPolicy(
            mode=GreetingMode.FOLLOW_UP,
            reply_language_code="en",
            reply_language_name="English",
        ),
        alpstein_product_behavior_enabled=False,
    )
    task = _task_content(follow_up)

    assert "GREETING ORCHESTRATION (follow-up)" in task
    assert "Alpstein AI introduction" not in task
    assert "Do not repeat the full introduction from prior turns" in task
