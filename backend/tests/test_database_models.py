from sqlalchemy import Boolean, Date, DateTime, ForeignKeyConstraint, Text, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base
from app.models import (
    Business,
    Conversation,
    Customer,
    DeliveryEvent,
    Flow,
    Lead,
    Message,
    MessageTrace,
    PromptRun,
    PromptTemplate,
    Tenant,
    TenantAiProfile,
    TenantBusinessProfile,
    TenantChannelSetting,
    TenantKnowledgeSource,
)
from app.models.lead import (
    LEAD_PRIORITY_HIGH,
    LEAD_PRIORITY_LOW,
    LEAD_PRIORITY_NORMAL,
    LEAD_PRIORITY_URGENT,
    LEAD_STATUS_CLOSED,
    LEAD_STATUS_CONTACTED,
    LEAD_STATUS_IN_PROGRESS,
    LEAD_STATUS_LOST,
    LEAD_STATUS_NEW,
)


def test_metadata_contains_persistence_slice_tables():
    assert set(Base.metadata.tables) == {
        "tenants",
        "businesses",
        "customers",
        "conversations",
        "messages",
        "leads",
        "tenant_business_profiles",
        "tenant_ai_profiles",
        "tenant_knowledge_sources",
        "tenant_channel_settings",
        "prompt_templates",
        "prompt_runs",
        "flows",
        "message_traces",
        "delivery_events",
        "inbound_processing_locks",
        "replay_events",
        "retry_attempts",
        "dead_letter_events",
        "rate_limit_buckets",
        "rate_limit_violations",
        "spam_indicator_buckets",
        "spam_containments",
        "spam_decisions",
    }
    assert Tenant.__tablename__ == "tenants"
    assert Business.__tablename__ == "businesses"
    assert MessageTrace.__tablename__ == "message_traces"
    assert DeliveryEvent.__tablename__ == "delivery_events"
    assert Customer.__tablename__ == "customers"
    assert Conversation.__tablename__ == "conversations"
    assert Message.__tablename__ == "messages"
    assert TenantBusinessProfile.__tablename__ == "tenant_business_profiles"
    assert TenantAiProfile.__tablename__ == "tenant_ai_profiles"
    assert TenantKnowledgeSource.__tablename__ == "tenant_knowledge_sources"
    assert TenantChannelSetting.__tablename__ == "tenant_channel_settings"
    assert PromptTemplate.__tablename__ == "prompt_templates"
    assert PromptRun.__tablename__ == "prompt_runs"
    assert Lead.__tablename__ == "leads"


def test_lead_status_and_priority_constants_match_schema():
    assert LEAD_STATUS_NEW == "new"
    assert LEAD_STATUS_IN_PROGRESS == "in_progress"
    assert LEAD_STATUS_CONTACTED == "contacted"
    assert LEAD_STATUS_CLOSED == "closed"
    assert LEAD_STATUS_LOST == "lost"
    assert LEAD_PRIORITY_LOW == "low"
    assert LEAD_PRIORITY_NORMAL == "normal"
    assert LEAD_PRIORITY_HIGH == "high"
    assert LEAD_PRIORITY_URGENT == "urgent"


def test_tenant_model_matches_schema_foundation():
    table = Tenant.__table__

    assert isinstance(table.c.id.type, UUID)
    assert table.c.name.nullable is False
    assert table.c.slug.nullable is False
    assert table.c.status.nullable is False
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False
    assert "tenants_slug_idx" in {index.name for index in table.indexes}
    assert "tenants_status_idx" in {index.name for index in table.indexes}
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"slug"}
        for constraint in table.constraints
    )


def test_business_model_matches_schema_foundation():
    table = Business.__table__

    assert isinstance(table.c.id.type, UUID)
    assert isinstance(table.c.tenant_id.type, UUID)
    assert isinstance(table.c.working_hours.type, JSONB)
    assert table.c.tenant_id.nullable is False
    assert table.c.external_id.nullable is False
    assert table.c.name.nullable is False
    assert table.c.storage_mode.nullable is False
    assert table.c.status.nullable is False
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False
    assert "database_connection_id" not in table.c
    assert {
        "businesses_tenant_id_idx",
        "businesses_external_id_idx",
        "businesses_status_idx",
    }.issubset({index.name for index in table.indexes})
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"external_id"}
        for constraint in table.constraints
    )
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and [element.target_fullname for element in constraint.elements] == ["tenants.id"]
        for constraint in table.constraints
    )


def test_customer_model_matches_schema():
    table = Customer.__table__

    assert isinstance(table.c.id.type, UUID)
    assert isinstance(table.c.tenant_id.type, UUID)
    assert isinstance(table.c.business_id.type, UUID)
    assert table.c.tenant_id.nullable is False
    assert table.c.business_id.nullable is False
    assert table.c.name.nullable is True
    assert table.c.phone.nullable is True
    assert table.c.email.nullable is True
    assert table.c.language.nullable is True
    assert table.c.external_customer_id.nullable is True
    assert table.c.source_channel.nullable is True
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False
    assert {
        "customers_tenant_id_idx",
        "customers_business_id_idx",
        "customers_phone_idx",
        "customers_business_channel_external_id_idx",
    }.issubset({index.name for index in table.indexes})
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"business_id", "phone"}
        for constraint in table.constraints
    )
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns}
        == {"business_id", "source_channel", "external_customer_id"}
        for constraint in table.constraints
    )
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


def test_conversation_model_matches_schema():
    table = Conversation.__table__

    assert isinstance(table.c.id.type, UUID)
    assert isinstance(table.c.tenant_id.type, UUID)
    assert isinstance(table.c.business_id.type, UUID)
    assert isinstance(table.c.flow_id.type, UUID)
    assert isinstance(table.c.customer_id.type, UUID)
    assert isinstance(table.c.is_ai_active.type, Boolean)
    assert isinstance(table.c.last_message_at.type, DateTime)
    assert "metadata" not in table.c
    assert table.c.tenant_id.nullable is False
    assert table.c.business_id.nullable is False
    assert table.c.flow_id.nullable is False
    assert table.c.customer_id.nullable is False
    assert table.c.channel.nullable is False
    assert table.c.status.nullable is False
    assert table.c.is_ai_active.nullable is False
    assert table.c.last_message_at.nullable is True
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False
    assert {
        "conversations_tenant_id_idx",
        "conversations_business_id_idx",
        "conversations_customer_id_idx",
        "conversations_status_idx",
        "conversations_flow_id_idx",
        "conversations_flow_channel_external_idx",
        "conversations_flow_channel_customer_idx",
    }.issubset({index.name for index in table.indexes})
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
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and [element.target_fullname for element in constraint.elements]
        == ["customers.id"]
        for constraint in table.constraints
    )
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and [element.target_fullname for element in constraint.elements]
        == ["flows.id"]
        for constraint in table.constraints
    )


def test_message_model_matches_schema():
    table = Message.__table__

    assert isinstance(table.c.id.type, UUID)
    assert isinstance(table.c.tenant_id.type, UUID)
    assert isinstance(table.c.business_id.type, UUID)
    assert isinstance(table.c.conversation_id.type, UUID)
    assert isinstance(table.c.message_text.type, Text)
    assert isinstance(table.c.raw_payload.type, JSONB)
    assert isinstance(table.c.ai_metadata.type, JSONB)
    assert isinstance(table.c.metadata.type, JSONB)
    assert table.c.tenant_id.nullable is False
    assert table.c.business_id.nullable is False
    assert table.c.conversation_id.nullable is False
    assert table.c.sender_type.nullable is False
    assert table.c.direction.nullable is False
    assert table.c.channel.nullable is False
    assert table.c.message_text.nullable is False
    assert table.c.message_type.nullable is False
    assert table.c.external_message_id.nullable is True
    assert table.c.idempotency_key.nullable is True
    assert table.c.raw_payload.nullable is True
    assert table.c.ai_metadata.nullable is True
    assert table.c.metadata.nullable is True
    assert table.c.created_at.nullable is False
    assert {
        "messages_tenant_id_idx",
        "messages_business_id_idx",
        "messages_conversation_id_idx",
        "messages_created_at_idx",
        "messages_external_message_id_idx",
        "messages_incoming_conversation_external_unique",
        "messages_incoming_conversation_idempotency_unique",
        "messages_idempotency_key_idx",
    }.issubset({index.name for index in table.indexes})
    conversation_external_unique = next(
        index
        for index in table.indexes
        if index.name == "messages_incoming_conversation_external_unique"
    )
    assert conversation_external_unique.unique is True
    assert list(conversation_external_unique.columns.keys()) == [
        "business_id",
        "conversation_id",
        "external_message_id",
    ]
    assert "sender_type = 'customer'" in str(
        conversation_external_unique.dialect_options["postgresql"]["where"]
    )
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
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and [element.target_fullname for element in constraint.elements]
        == ["conversations.id"]
        for constraint in table.constraints
    )


def test_lead_model_matches_schema():
    table = Lead.__table__

    assert isinstance(table.c.id.type, UUID)
    assert isinstance(table.c.tenant_id.type, UUID)
    assert isinstance(table.c.business_id.type, UUID)
    assert isinstance(table.c.customer_id.type, UUID)
    assert isinstance(table.c.conversation_id.type, UUID)
    assert isinstance(table.c.preferred_date.type, Date)
    assert isinstance(table.c.preferred_time.type, Time)
    assert isinstance(table.c.customer_note.type, Text)
    assert isinstance(table.c.ai_summary.type, Text)
    assert table.c.tenant_id.nullable is False
    assert table.c.business_id.nullable is False
    assert table.c.customer_id.nullable is False
    assert table.c.conversation_id.nullable is False
    assert table.c.service_requested.nullable is True
    assert table.c.preferred_date.nullable is True
    assert table.c.preferred_time.nullable is True
    assert table.c.customer_note.nullable is True
    assert table.c.status.nullable is False
    assert table.c.priority.nullable is True
    assert table.c.source_channel.nullable is True
    assert table.c.ai_summary.nullable is True
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False
    assert {
        "leads_tenant_id_idx",
        "leads_business_id_idx",
        "leads_customer_id_idx",
        "leads_status_idx",
        "leads_created_at_idx",
    } == {index.name for index in table.indexes}
    fk_targets = {
        tuple(element.target_fullname for element in constraint.elements)
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert fk_targets == {
        ("tenants.id",),
        ("businesses.id",),
        ("customers.id",),
        ("conversations.id",),
    }
    assert table.c.status.default.arg == LEAD_STATUS_NEW
    assert table.c.priority.default.arg == LEAD_PRIORITY_NORMAL
