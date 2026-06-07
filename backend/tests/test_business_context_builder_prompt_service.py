import uuid

import pytest

from app.models.business_context_builder import (
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_USER,
)
from app.services.business_context_builder_constants import STEP_TARGET_CUSTOMERS
from app.services.business_context_builder_prompt_service import (
    BCB_NEXT_QUESTION_TASK,
    BusinessContextBuilderConversationTurn,
    BusinessContextBuilderPromptInput,
    BusinessContextBuilderPromptService,
    PLATFORM_SYSTEM_PROMPT,
)


def test_prompt_builder_creates_constrained_next_question_prompt():
    prompt_input = BusinessContextBuilderPromptInput(
        session_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        next_step=STEP_TARGET_CUSTOMERS,
        messages=(
            BusinessContextBuilderConversationTurn(
                role=MESSAGE_ROLE_ASSISTANT,
                content="What is your company name?",
            ),
            BusinessContextBuilderConversationTurn(
                role=MESSAGE_ROLE_USER,
                content="Alpstein Services GmbH",
            ),
        ),
    )

    prompt = BusinessContextBuilderPromptService().build_next_question_prompt(prompt_input)

    assert prompt.task == BCB_NEXT_QUESTION_TASK
    assert prompt.section_ids()[0] == "platform_system"
    assert prompt.section_ids()[1] == "task_instructions"
    platform = prompt.sections[0].content
    task = prompt.sections[1].content
    assert "exactly one clear question" in platform.lower()
    assert "do not generate the final business context" in platform.lower()
    assert "internal system fields" in platform.lower()
    assert "sensitive" in platform.lower()
    assert "generate_next_assistant_question" in task
    assert "target customers" in task.lower()
    history = next(
        section for section in prompt.sections if section.section_id == "conversation_history"
    )
    assert "(reference data)" in history.label
    assert "user: Alpstein Services GmbH" in history.content
    serialized = "\n".join(section.content for section in prompt.sections)
    assert "raw_payload" not in serialized
    assert "ai_metadata" not in serialized


def test_prompt_builder_omits_empty_history_section():
    prompt_input = BusinessContextBuilderPromptInput(
        session_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        next_step=STEP_TARGET_CUSTOMERS,
        messages=(),
    )

    prompt = BusinessContextBuilderPromptService().build_next_question_prompt(prompt_input)

    assert "conversation_history" not in prompt.section_ids()
    step_context = next(
        section for section in prompt.sections if section.section_id == "step_context"
    )
    assert "allowed_steps" in step_context.content


def test_prompt_builder_does_not_import_openai_or_db_modules():
    import app.services.business_context_builder_prompt_service as module

    source = open(module.__file__, encoding="utf-8").read().lower()
    assert "openai" not in source
    assert "sqlalchemy" not in source
    assert "asyncsession" not in source


def test_platform_system_prompt_is_not_tenant_configurable():
    assert "final business context" in PLATFORM_SYSTEM_PROMPT.lower()
