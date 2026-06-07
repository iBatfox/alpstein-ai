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
from app.schemas.knowledge import KnowledgeRetrievalResult, KnowledgeSnippet
from app.services.prompt_builder_service import (
    CURRENT_MESSAGE_MAX_CHARS,
    PLATFORM_TASK_REGISTRY,
    PROMPT_ASSEMBLY_MAX_CHARS,
    REPLY_TO_CUSTOMER_TASK,
    TRUNCATED_MARKER,
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
            services={"haircut": {"price": 35, "currency": "CHF"}},
            city="Zurich",
        ),
        behavior=TenantBehaviorConfig(
            present=True,
            tone="friendly",
            language="de",
        ),
        channel_rules=TenantChannelRulesConfig(
            present=True,
            channel="whatsapp",
            response_style="short",
            max_response_length=500,
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
            KnowledgeSnippet(
                id=uuid.uuid4(),
                source_type="pricing",
                title="Haircut pricing",
                content="Haircut 35 CHF",
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
            ConversationHistoryMessage(
                sender_type="ai",
                message_text="Hi, how can I help?",
                created_at=datetime(2026, 5, 1, 10, 1, 0),
            ),
        )
    )


def _section_map(prompt):
    return {section.section_id: section for section in prompt.sections}


def test_section_order_is_canonical_1_to_9(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Can I book a haircut tomorrow?",
    )

    assert prompt.section_ids() == CANONICAL_SECTION_ORDER
    assert len(prompt.sections) == 9


def test_platform_sections_are_first_and_never_truncated(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    huge_description = "x" * (PROMPT_ASSEMBLY_MAX_CHARS - 1_000)
    overloaded = AiConfigurationBundle(
        tenant_id=full_configuration.tenant_id,
        business_id=full_configuration.business_id,
        channel=full_configuration.channel,
        template_key=full_configuration.template_key,
        platform_template=full_configuration.platform_template,
        business_context=TenantBusinessContextConfig(
            present=True,
            business_description=huge_description,
        ),
        behavior=full_configuration.behavior,
        channel_rules=full_configuration.channel_rules,
    )

    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=overloaded,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Need appointment",
    )
    sections = _section_map(prompt)

    assert prompt.sections[0].section_id == "platform_system"
    assert prompt.sections[1].section_id == "task_instructions"
    assert sections["platform_system"].content.endswith("Platform safety and role rules.")
    assert TRUNCATED_MARKER not in sections["platform_system"].content
    assert TRUNCATED_MARKER not in sections["task_instructions"].content


def test_task_instructions_comes_from_registry_not_tenant_config(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Price?",
    )
    task_section = _section_map(prompt)["task_instructions"]

    assert PLATFORM_TASK_REGISTRY[REPLY_TO_CUSTOMER_TASK] in task_section.content
    assert "tone: friendly" not in task_section.content
    assert task_section.kind == "system"


def test_tenant_text_is_labeled_reference_data(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Hello",
    )
    sections = _section_map(prompt)

    assert "(reference data)" in sections["business_context_source_of_truth"].label
    assert "(reference data)" in sections["tenant_business_context"].label
    assert "(reference data)" in sections["tenant_behavior"].label
    assert sections["business_context_source_of_truth"].kind == "data"
    assert sections["tenant_business_context"].kind == "data"
    assert "Barbershop in Zurich." in sections["business_context_source_of_truth"].content
    assert "Barbershop in Zurich." not in sections["tenant_business_context"].content


def test_business_context_source_of_truth_is_separate_block(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Hello",
        operator_business_context="Instagram: https://instagram.com/alpstein_ai",
    )
    sections = _section_map(prompt)

    assert "Business context is the source of truth" in sections[
        "business_context_source_of_truth"
    ].content
    assert "Barbershop in Zurich." in sections["business_context_source_of_truth"].content
    assert "https://instagram.com/alpstein_ai" in sections[
        "business_context_source_of_truth"
    ].content
    assert "https://instagram.com/alpstein_ai" not in sections[
        "tenant_business_context"
    ].content


def test_knowledge_after_tenant_config_and_before_history(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Hours?",
    )
    ids = prompt.section_ids()
    assert ids.index("business_context_source_of_truth") < ids.index("knowledge")
    assert ids.index("tenant_business_context") < ids.index("knowledge")
    assert ids.index("knowledge") < ids.index("conversation_history")
    assert "Opening hours" in _section_map(prompt)["knowledge"].content


def test_history_is_oldest_to_newest_before_current_message(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
):
    history = ConversationHistory(
        messages=(
            ConversationHistoryMessage(
                sender_type="customer",
                message_text="First",
                created_at=datetime(2026, 5, 1, 9, 0, 0),
            ),
            ConversationHistoryMessage(
                sender_type="ai",
                message_text="Second",
                created_at=datetime(2026, 5, 1, 9, 1, 0),
            ),
        )
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=history,
        current_customer_message="Third",
    )
    history_content = _section_map(prompt)["conversation_history"].content
    first_index = history_content.index("customer: First")
    second_index = history_content.index("ai (dialogue only, not business facts): Second")

    assert first_index < second_index
    assert prompt.section_ids()[-1] == "current_customer_message"
    assert "Third" in _section_map(prompt)["current_customer_message"].content


def test_current_customer_message_always_last_and_capped(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    long_message = "m" * (CURRENT_MESSAGE_MAX_CHARS + 100)
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message=long_message,
    )

    current = _section_map(prompt)["current_customer_message"]
    assert prompt.sections[-1].section_id == "current_customer_message"
    assert TRUNCATED_MARKER in current.content
    assert len(current.content) <= CURRENT_MESSAGE_MAX_CHARS + 200


def test_truncation_is_deterministic(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    overloaded = AiConfigurationBundle(
        tenant_id=full_configuration.tenant_id,
        business_id=full_configuration.business_id,
        channel=full_configuration.channel,
        template_key=full_configuration.template_key,
        platform_template=full_configuration.platform_template,
        business_context=TenantBusinessContextConfig(
            present=True,
            business_description="y" * 20_000,
        ),
        behavior=full_configuration.behavior,
        channel_rules=full_configuration.channel_rules,
    )
    builder = PromptBuilderService()
    kwargs = {
        "configuration": overloaded,
        "knowledge": knowledge_result,
        "history": conversation_history,
        "current_customer_message": "Book now",
    }
    first = builder.build_reply_to_customer(**kwargs)
    second = builder.build_reply_to_customer(**kwargs)

    assert first == second
    assert first.total_chars() <= PROMPT_ASSEMBLY_MAX_CHARS


def test_forbidden_internal_fields_are_not_present(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Hello",
    )
    serialized = "\n".join(section.content for section in prompt.sections).lower()

    assert "raw_payload" not in serialized
    assert "ai_metadata" not in serialized
    assert '"metadata"' not in serialized
    assert "messages[]" not in serialized


def test_output_is_provider_neutral_without_openai_messages(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Hello",
    )

    assert prompt.task == REPLY_TO_CUSTOMER_TASK
    assert not hasattr(prompt, "messages")
    assert all(section.section_id for section in prompt.sections)
    assert all(section.kind in ("system", "data") for section in prompt.sections)


def test_duplicate_final_customer_turn_removed_from_history_only(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
):
    duplicate_text = "Same as current"
    history = ConversationHistory(
        messages=(
            ConversationHistoryMessage(
                sender_type="customer",
                message_text="Earlier",
                created_at=datetime(2026, 5, 1, 9, 0, 0),
            ),
            ConversationHistoryMessage(
                sender_type="customer",
                message_text=duplicate_text,
                created_at=datetime(2026, 5, 1, 9, 5, 0),
            ),
        )
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=history,
        current_customer_message=duplicate_text,
    )
    history_content = _section_map(prompt)["conversation_history"].content

    assert "customer: Earlier" in history_content
    assert duplicate_text not in history_content
    assert duplicate_text in _section_map(prompt)["current_customer_message"].content


def test_platform_system_comes_from_template_not_tenant(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    configuration = AiConfigurationBundle(
        tenant_id=full_configuration.tenant_id,
        business_id=full_configuration.business_id,
        channel=full_configuration.channel,
        template_key=full_configuration.template_key,
        platform_template=full_configuration.platform_template,
        business_context=full_configuration.business_context,
        behavior=TenantBehaviorConfig(
            present=True,
            tone="friendly",
            language="de",
            metadata={"system_prompt": "Tenant override attempt"},
        ),
        channel_rules=full_configuration.channel_rules,
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Hi",
    )
    platform = _section_map(prompt)["platform_system"].content

    assert "Platform safety and role rules." in platform
    assert "Tenant override attempt" not in platform


def test_platform_system_excludes_known_business_contact_markers(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
    conversation_history: ConversationHistory,
):
    configuration = AiConfigurationBundle(
        tenant_id=full_configuration.tenant_id,
        business_id=full_configuration.business_id,
        channel=full_configuration.channel,
        template_key=full_configuration.template_key,
        platform_template=PlatformPromptTemplateConfig(
            id=uuid.uuid4(),
            template_key="customer_reply_v1",
            template_name="Customer reply",
            version="1",
            system_prompt=(
                "Platform safety rules.\n"
                "LinkedIn:\n"
                "https://www.linkedin.com/in/ibatfox/\n"
                "Email: admin@alpstein-ai.ch\n"
                "Instagram: https://instagram.com/alpstein_ai"
            ),
        ),
        business_context=full_configuration.business_context,
        behavior=full_configuration.behavior,
        channel_rules=full_configuration.channel_rules,
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=configuration,
        knowledge=knowledge_result,
        history=conversation_history,
        current_customer_message="Hi",
    )
    platform = _section_map(prompt)["platform_system"].content.lower()

    assert "platform safety rules" in platform
    assert "linkedin.com/in/ibatfox" not in platform
    assert "linkedin:" not in platform
    assert "admin@alpstein-ai.ch" not in platform
    assert "instagram.com" not in platform


def test_current_business_context_overrides_stale_history_contacts(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
):
    history = ConversationHistory(
        messages=(
            ConversationHistoryMessage(
                sender_type="ai",
                message_text="Old contact was https://www.linkedin.com/in/ibatfox/",
                created_at=datetime(2026, 5, 1, 10, 1, 0),
            ),
        )
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=history,
        current_customer_message="How can I contact you?",
        operator_business_context="Current contact: https://instagram.com/alpstein_ai",
    )
    sections = _section_map(prompt)
    source = sections["business_context_source_of_truth"].content
    history_content = sections["conversation_history"].content

    assert "https://instagram.com/alpstein_ai" in source
    assert "linkedin.com/in/ibatfox" not in history_content
    assert "historical assistant reply omitted" in history_content
    assert "Never use business contact data from conversation history unless it exists" in source
    assert prompt.section_ids().index(
        "business_context_source_of_truth"
    ) < prompt.section_ids().index("conversation_history")


def test_stale_ai_history_contact_reply_is_omitted_from_prompt(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
):
    history = ConversationHistory(
        messages=(
            ConversationHistoryMessage(
                sender_type="customer",
                message_text="Как связаться с командой?",
                created_at=datetime(2026, 5, 1, 10, 0, 0),
            ),
            ConversationHistoryMessage(
                sender_type="ai",
                message_text=(
                    "Вы можете связаться по admin@alpstein-ai.ch и LinkedIn: "
                    "https://www.linkedin.com/in/ibatfox/"
                ),
                created_at=datetime(2026, 5, 1, 10, 1, 0),
            ),
        )
    )
    prompt = PromptBuilderService().build_reply_to_customer(
        configuration=full_configuration,
        knowledge=knowledge_result,
        history=history,
        current_customer_message="Пришли актуальные контакты",
        operator_business_context="Instagram: https://www.instagram.com/alpstein_ai/",
    )
    serialized = "\n\n".join(section.content for section in prompt.sections).lower()
    sections = _section_map(prompt)

    assert "https://www.instagram.com/alpstein_ai/" in sections[
        "business_context_source_of_truth"
    ].content
    assert "linkedin.com/in/ibatfox" not in serialized
    assert "admin@alpstein-ai.ch" not in serialized
    assert "historical assistant reply omitted" in sections[
        "conversation_history"
    ].content
    assert "Как связаться с командой?" in sections["conversation_history"].content


def test_same_business_context_source_of_truth_for_telegram_and_instagram(
    full_configuration: AiConfigurationBundle,
    knowledge_result: KnowledgeRetrievalResult,
):
    operator_context = "Instagram: https://www.instagram.com/alpstein_ai/"
    outputs = []
    for channel in ("telegram", "instagram"):
        configuration = AiConfigurationBundle(
            tenant_id=full_configuration.tenant_id,
            business_id=full_configuration.business_id,
            channel=channel,
            template_key=full_configuration.template_key,
            platform_template=full_configuration.platform_template,
            business_context=full_configuration.business_context,
            behavior=full_configuration.behavior,
            channel_rules=TenantChannelRulesConfig.missing(channel),
        )
        prompt = PromptBuilderService().build_reply_to_customer(
            configuration=configuration,
            knowledge=knowledge_result,
            history=ConversationHistory.empty(),
            current_customer_message="Contacts?",
            operator_business_context=operator_context,
        )
        outputs.append(_section_map(prompt)["business_context_source_of_truth"].content)

    assert outputs[0] == outputs[1]
    assert "https://www.instagram.com/alpstein_ai/" in outputs[0]


def test_prompt_builder_module_has_no_provider_imports():
    import app.services.prompt_builder_service as module

    source_path = module.__file__
    assert source_path is not None
    source = open(source_path, encoding="utf-8").read().lower()
    for forbidden in ("openai", "httpx", "aiohttp", "anthropic"):
        assert forbidden not in source
