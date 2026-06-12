"""CIP-B — intent policy in §2 task_instructions (Alpstein demo only)."""

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
from app.services.greeting_prompt_instructions import build_greeting_instruction_block
from app.services.intent_prompt_instructions import build_intent_instruction_block
from app.services.pre_sales_prompt_instructions import PRE_SALES_CORE_CHARTER
from app.services.prompt_builder_service import (
    PromptBuilderService,
    _build_task_instructions_body,
)

_LEGACY_APPENDIX_HEADER = "TECHNICAL PRE-SALES BEHAVIOR (platform authority):"

_FORBIDDEN_HARDCODED_CONTACTS = (
    "Ivan Bataiev",
    "bataev.co@gmail.com",
    "+41 79 823 27 86",
    "Manager, Alpstein AI",
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


def _intent_body(intent: ConversationIntent) -> str:
    return build_intent_instruction_block(intent)


def _alpstein_intent_task_body(
    intent: ConversationIntent,
    *,
    with_greeting: bool = True,
) -> str:
    resolution = ConversationIntentResolution(
        intent=intent,
        matched_rule="test:fixture",
    )
    return _build_task_instructions_body(
        alpstein_product_behavior_enabled=True,
        conversation_intent=resolution,
        greeting_policy=(
            GreetingPolicy(
                mode=GreetingMode.FIRST_CONTACT,
                reply_language_code="ru",
                reply_language_name="Russian",
            )
            if with_greeting
            else None
        ),
    )


@pytest.mark.parametrize("intent", list(ConversationIntent))
def test_task_instructions_contain_no_hardcoded_contact_values(
    alpstein_configuration, intent: ConversationIntent
):
    resolution = ConversationIntentResolution(intent=intent, matched_rule="test")
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=alpstein_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="test",
        alpstein_product_behavior_enabled=True,
        conversation_intent=resolution,
    )
    task = _task_content(prompt)
    for fragment in _FORBIDDEN_HARDCODED_CONTACTS:
        assert fragment not in task


def test_non_alpstein_path_has_no_hardcoded_contact_values(alpstein_configuration):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=alpstein_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="Price?",
        alpstein_product_behavior_enabled=False,
        conversation_intent=None,
    )
    task = _task_content(prompt)
    for fragment in _FORBIDDEN_HARDCODED_CONTACTS:
        assert fragment not in task


def test_core_charter_includes_name_preservation_and_contact_source_rules(
    alpstein_configuration,
):
    resolution = ConversationIntentResolution(
        intent=ConversationIntent.TECHNICAL_INTEREST,
        matched_rule="test",
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=alpstein_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="How does API work?",
        alpstein_product_behavior_enabled=True,
        conversation_intent=resolution,
    )
    task = _task_content(prompt)
    assert "Do not translate personal names" in task
    assert "OPERATOR BUSINESS NOTES" in task
    assert "do not invent" in task.lower()


def test_implementation_interest_uses_operator_contact_when_provided(
    alpstein_configuration,
):
    resolution = ConversationIntentResolution(
        intent=ConversationIntent.IMPLEMENTATION_INTEREST,
        matched_rule="test",
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=alpstein_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="как начать",
        alpstein_product_behavior_enabled=True,
        conversation_intent=resolution,
    )
    task = _task_content(prompt)
    assert "OPERATOR BUSINESS NOTES" in task
    assert "do not invent contact" in task.lower()


def test_presales_header_absent_when_alpstein_product_behavior_enabled(alpstein_configuration):
    resolution = ConversationIntentResolution(
        intent=ConversationIntent.PRICING_INTEREST,
        matched_rule="pricing_interest:ru_price",
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=alpstein_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="сколько стоит",
        alpstein_product_behavior_enabled=True,
        conversation_intent=resolution,
    )
    task = _task_content(prompt)

    assert _LEGACY_APPENDIX_HEADER not in task
    assert PRE_SALES_CORE_CHARTER in task
    assert task.count("CONVERSATION INTENT (active turn):") == 1


def test_non_alpstein_path_excludes_presales_and_alpstein_greeting(alpstein_configuration):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=alpstein_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="Price?",
        alpstein_product_behavior_enabled=False,
        conversation_intent=None,
        greeting_policy=GreetingPolicy(
            mode=GreetingMode.FIRST_CONTACT,
            reply_language_code="en",
            reply_language_name="English",
        ),
    )
    task = _task_content(prompt)

    assert _LEGACY_APPENDIX_HEADER not in task
    assert PRE_SALES_CORE_CHARTER not in task
    assert "CONVERSATION INTENT (active turn):" not in task
    assert "I am your Alpstein AI assistant" not in task
    assert "technical pre-sales consultant" not in task
    assert "Do not use Alpstein AI product messaging" in task
    assert "Give a brief helpful introduction using tenant business reference data only" in task
    assert "Ask how you can help today" in task
    assert "CRM sales language" in task
    assert "Alpstein AI capabilities" not in task
    assert "project discussion" not in task


@pytest.mark.parametrize(
    ("intent", "message", "required_fragments", "forbidden_fragments"),
    [
        (
            ConversationIntent.PRICING_INTEREST,
            "сколько стоит",
            ["Do not invent prices", "human follow-up"],
            ["CHF 500", "€"],
        ),
        (
            ConversationIntent.IMPLEMENTATION_INTEREST,
            "как начать",
            [
                "phone or email",
                "OPERATOR BUSINESS NOTES",
                "do not invent contact",
            ],
            _FORBIDDEN_HARDCODED_CONTACTS,
        ),
        (
            ConversationIntent.TECHNICAL_INTEREST,
            "How does n8n connect to your API?",
            ["medium technical depth", "Do not dump"],
            ["Ask for phone or email"],
        ),
        (
            ConversationIntent.UNSUPPORTED_SYSTEM,
            "Can you integrate Bitrix24?",
            ["Do not claim a guaranteed", "API/webhooks"],
            ["guaranteed integration", "fully certified"],
        ),
        (
            ConversationIntent.CONFUSED_CUSTOMER,
            "я не понял",
            ["one practical example", "No long numbered menus"],
            [],
        ),
        (
            ConversationIntent.OFF_TOPIC,
            "погода в берне",
            ["encyclopedia", "Redirect"],
            [],
        ),
        (
            ConversationIntent.SOCIAL_GREETING,
            "привет",
            ["no capability lists", "how can I help"],
            ["Bitrix24", "Salesforce"],
        ),
    ],
)
def test_intent_slice_content(
    alpstein_configuration,
    intent: ConversationIntent,
    message: str,
    required_fragments: list[str],
    forbidden_fragments: list[str],
):
    resolution = ConversationIntentResolution(intent=intent, matched_rule="test")
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=alpstein_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message=message,
        alpstein_product_behavior_enabled=True,
        conversation_intent=resolution,
    )
    task = _task_content(prompt)
    assert f"CONVERSATION INTENT (active turn): {intent.value}" in task
    for fragment in required_fragments:
        assert fragment in task
    for fragment in forbidden_fragments:
        assert fragment not in task


def test_greeting_orchestration_still_appended_with_intent_policy(alpstein_configuration):
    resolution = ConversationIntentResolution(
        intent=ConversationIntent.SOCIAL_GREETING,
        matched_rule="social_greeting:ru_hello",
    )
    greeting = GreetingPolicy(
        mode=GreetingMode.FIRST_CONTACT,
        reply_language_code="ru",
        reply_language_name="Russian",
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=alpstein_configuration,
        knowledge=KnowledgeRetrievalResult(snippets=()),
        history=ConversationHistory.empty(),
        current_customer_message="привет",
        greeting_policy=greeting,
        alpstein_product_behavior_enabled=True,
        conversation_intent=resolution,
    )
    task = _task_content(prompt)

    assert "GREETING ORCHESTRATION (first contact)" in task
    assert "technical pre-sales" in task
    assert task.index("CONVERSATION INTENT (active turn):") < task.index(
        "GREETING ORCHESTRATION (first contact)"
    )


def test_sample_task_instructions_pricing_intent():
    body = _alpstein_intent_task_body(
        ConversationIntent.PRICING_INTEREST, with_greeting=False
    )
    assert "PRE-SALES CORE CHARTER" in body
    assert "pricing_interest" in body
    assert "Do not invent prices" in body


def test_sample_task_instructions_implementation_intent():
    body = _alpstein_intent_task_body(
        ConversationIntent.IMPLEMENTATION_INTEREST, with_greeting=False
    )
    assert "implementation_interest" in body
    assert "phone or email" in body


def test_sample_task_instructions_technical_intent():
    body = _alpstein_intent_task_body(
        ConversationIntent.TECHNICAL_INTEREST, with_greeting=False
    )
    assert "technical_interest" in body
    assert "do not push phone/email unless" in body.lower()


def test_intent_policy_requires_resolution():
    with pytest.raises(ValueError, match="conversation_intent is required"):
        _build_task_instructions_body(
            alpstein_product_behavior_enabled=True,
            conversation_intent=None,
            greeting_policy=None,
        )
