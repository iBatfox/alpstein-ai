from sqlalchemy import Boolean, ForeignKeyConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models import (
    PromptRun,
    PromptTemplate,
    TenantAiProfile,
    TenantBusinessProfile,
    TenantChannelSetting,
    TenantKnowledgeSource,
)

TENANT_SCOPED_AI_TABLES = (
    TenantBusinessProfile,
    TenantAiProfile,
    TenantKnowledgeSource,
    TenantChannelSetting,
)


def test_tenant_scoped_ai_tables_require_tenant_and_business_ids():
    for model in TENANT_SCOPED_AI_TABLES:
        table = model.__table__
        assert table.c.tenant_id.nullable is False
        assert table.c.business_id.nullable is False
        assert isinstance(table.c.tenant_id.type, UUID)
        assert isinstance(table.c.business_id.type, UUID)
        assert any(
            isinstance(constraint, ForeignKeyConstraint)
            and [element.target_fullname for element in constraint.elements] == ["tenants.id"]
            for constraint in table.constraints
        )
        assert any(
            isinstance(constraint, ForeignKeyConstraint)
            and [element.target_fullname for element in constraint.elements]
            == ["businesses.id"]
            for constraint in table.constraints
        )


def test_tenant_business_profile_model_matches_schema():
    table = TenantBusinessProfile.__table__

    assert isinstance(table.c.services.type, JSONB)
    assert isinstance(table.c.pricing.type, JSONB)
    assert isinstance(table.c.working_hours.type, JSONB)
    assert isinstance(table.c.metadata.type, JSONB)
    assert table.c.business_description.nullable is True
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False
    assert "api_key" not in table.c
    assert "password" not in table.c


def test_tenant_ai_profile_model_matches_schema():
    table = TenantAiProfile.__table__

    assert isinstance(table.c.handoff_keywords.type, JSONB)
    assert isinstance(table.c.forbidden_promises.type, JSONB)
    assert isinstance(table.c.fallback_response.type, Text)
    assert table.c.ask_for_name.nullable is True
    assert table.c.handoff_enabled.nullable is True
    assert "api_key" not in table.c


def test_tenant_knowledge_source_model_matches_schema():
    table = TenantKnowledgeSource.__table__

    assert table.c.source_type.nullable is False
    assert isinstance(table.c.content.type, Text)
    assert table.c.content.nullable is False
    assert isinstance(table.c.is_active.type, Boolean)
    assert table.c.is_active.nullable is False


def test_tenant_channel_setting_model_matches_schema():
    table = TenantChannelSetting.__table__

    assert table.c.channel.nullable is False
    assert isinstance(table.c.max_response_length.type, Integer)
    assert table.c.allow_emojis.nullable is True
    assert table.c.allow_links.nullable is True


def test_prompt_template_model_matches_schema():
    table = PromptTemplate.__table__

    assert table.c.template_key.nullable is False
    assert isinstance(table.c.system_prompt.type, Text)
    assert table.c.system_prompt.nullable is False
    assert table.c.is_active.nullable is False
    assert "updated_at" in table.c
    assert "tenant_id" not in table.c
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"template_key"}
        for constraint in table.constraints
    )


def test_prompt_run_model_matches_schema():
    table = PromptRun.__table__

    assert isinstance(table.c.tenant_id.type, UUID)
    assert isinstance(table.c.business_id.type, UUID)
    assert isinstance(table.c.conversation_id.type, UUID)
    assert isinstance(table.c.message_id.type, UUID)
    assert table.c.tenant_id.nullable is False
    assert table.c.business_id.nullable is False
    assert table.c.conversation_id.nullable is True
    assert table.c.message_id.nullable is True
    assert table.c.model.nullable is False
    assert isinstance(table.c.input_tokens.type, Integer)
    assert isinstance(table.c.final_prompt.type, Text)
    assert isinstance(table.c.metadata.type, JSONB)
    assert table.c.created_at.nullable is False
    assert "updated_at" not in table.c
    assert "api_key" not in table.c
    assert "password" not in table.c
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and [element.target_fullname for element in constraint.elements]
        == ["conversations.id"]
        for constraint in table.constraints
    )
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and [element.target_fullname for element in constraint.elements] == ["messages.id"]
        for constraint in table.constraints
    )
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and [element.target_fullname for element in constraint.elements]
        == ["prompt_templates.id"]
        for constraint in table.constraints
    )
