import importlib.util
from pathlib import Path


def test_initial_migration_is_tenants_and_businesses_only():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0001_create_tenants_and_businesses.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0001", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0001"
    assert module.down_revision is None
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_initial_migration_does_not_create_out_of_scope_tables():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0001_create_tenants_and_businesses.py"
    )
    migration_source = migration_path.read_text()

    assert '"tenants"' in migration_source
    assert '"businesses"' in migration_source
    assert '"customers"' not in migration_source
    assert '"conversations"' not in migration_source
    assert '"messages"' not in migration_source
    assert '"leads"' not in migration_source
    assert '"database_connections"' not in migration_source
    assert "tenant_ai_profiles" not in migration_source


def test_customers_migration_is_customers_only():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0002_create_customers.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0002", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0002"
    assert module.down_revision == "0001"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    migration_source = migration_path.read_text()
    assert '"customers"' in migration_source
    assert '"conversations"' not in migration_source
    assert '"messages"' not in migration_source
    assert '"leads"' not in migration_source
    assert '"database_connections"' not in migration_source
    assert "sa.UniqueConstraint(\"business_id\", \"phone\")" in migration_source
    assert (
        "sa.UniqueConstraint(\"business_id\", \"source_channel\", "
        "\"external_customer_id\")"
    ) in migration_source


def test_conversations_migration_is_conversations_only():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0003_create_conversations.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0003", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0003"
    assert module.down_revision == "0002"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    migration_source = migration_path.read_text()
    assert '"conversations"' in migration_source
    assert '"messages"' not in migration_source
    assert '"leads"' not in migration_source
    assert '"database_connections"' not in migration_source
    assert '"is_ai_active"' in migration_source
    assert '"metadata"' not in migration_source
    assert '"channel"' in migration_source
    assert '"status"' in migration_source


def test_messages_migration_is_messages_only():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0004_create_messages.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0004", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0004"
    assert module.down_revision == "0003"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    migration_source = migration_path.read_text()
    assert '"messages"' in migration_source
    assert '"leads"' not in migration_source
    assert '"database_connections"' not in migration_source
    assert '"sender_type"' in migration_source
    assert '"direction"' in migration_source
    assert '"message_text"' in migration_source
    assert '"message_type"' in migration_source
    assert '"external_message_id"' in migration_source
    assert '"raw_payload"' in migration_source
    assert '"ai_metadata"' in migration_source
    assert '"metadata"' in migration_source
    assert '"content"' not in migration_source
    assert '"message_status"' not in migration_source


def test_messages_business_external_message_id_unique_migration():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0005_add_messages_business_external_message_id_unique.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0005", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0005"
    assert module.down_revision == "0004"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    migration_source = migration_path.read_text()
    assert '"messages"' in migration_source
    assert "messages_business_external_message_id_unique" in migration_source
    assert '"business_id"' in migration_source
    assert '"external_message_id"' in migration_source
    assert "unique=True" in migration_source
    assert "external_message_id IS NOT NULL" in migration_source
    assert "op.create_table" not in migration_source
    assert "op.drop_table" not in migration_source


def test_ai_configuration_migration_creates_expected_tables_only():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0006_create_ai_configuration_and_prompt_runs.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0006", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0006"
    assert module.down_revision == "0005"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    migration_source = migration_path.read_text()
    expected_tables = {
        "tenant_business_profiles",
        "tenant_ai_profiles",
        "tenant_knowledge_sources",
        "tenant_channel_settings",
        "prompt_templates",
        "prompt_runs",
    }
    for table_name in expected_tables:
        assert f'"{table_name}"' in migration_source

    assert migration_source.count("op.create_table") == 6
    assert '"leads"' not in migration_source
    assert '"database_connections"' not in migration_source
    assert '"api_key"' not in migration_source
    assert '"password"' not in migration_source
    assert '"secret"' not in migration_source
    assert '"encrypted_password"' not in migration_source

    assert '"tenant_id"' in migration_source
    assert '"business_id"' in migration_source
    assert '"conversation_id"' in migration_source
    assert '"message_id"' in migration_source
    assert '"prompt_template_id"' in migration_source
    assert '"model"' in migration_source
    assert '"system_prompt"' in migration_source
    assert '"template_key"' in migration_source
    assert "UniqueConstraint(\"template_key\")" in migration_source

    downgrade_source = migration_source.split("def downgrade")[1]
    assert downgrade_source.index("prompt_runs") < downgrade_source.index("prompt_templates")


def test_leads_migration_is_leads_only():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0007_create_leads.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0007", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0007"
    assert module.down_revision == "0006"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    migration_source = migration_path.read_text()
    assert migration_source.count("op.create_table") == 1
    assert '"leads"' in migration_source
    assert '"tenant_id"' in migration_source
    assert '"business_id"' in migration_source
    assert '"customer_id"' in migration_source
    assert '"conversation_id"' in migration_source
    assert '"service_requested"' in migration_source
    assert '"preferred_date"' in migration_source
    assert '"preferred_time"' in migration_source
    assert '"customer_note"' in migration_source
    assert '"status"' in migration_source
    assert '"priority"' in migration_source
    assert '"source_channel"' in migration_source
    assert '"ai_summary"' in migration_source
    assert 'server_default="new"' in migration_source
    assert 'server_default="normal"' in migration_source
    assert "leads_tenant_id_idx" in migration_source
    assert "leads_business_id_idx" in migration_source
    assert "leads_customer_id_idx" in migration_source
    assert "leads_status_idx" in migration_source
    assert "leads_created_at_idx" in migration_source
    assert '"database_connections"' not in migration_source
    assert '"prompt_templates"' not in migration_source
    assert '"api_key"' not in migration_source
    assert '"password"' not in migration_source

    downgrade_source = migration_source.split("def downgrade")[1]
    assert "op.drop_table(\"leads\")" in downgrade_source or 'op.drop_table("leads")' in downgrade_source


def test_flows_migration_is_flows_only():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0008_create_flows.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0008", migration_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0008"
    assert module.down_revision == "0007"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    migration_source = migration_path.read_text()
    assert migration_source.count("op.create_table") == 1
    assert '"flows"' in migration_source
    assert '"tenant_id"' in migration_source
    assert '"business_id"' in migration_source
    assert '"flow_key"' in migration_source
    assert '"flow_name"' in migration_source
    assert '"is_default"' in migration_source
    assert "flows_business_flow_key_unique" in migration_source
    assert "flows_business_default_unique" in migration_source
    assert '"conversations"' not in migration_source
    assert '"messages"' not in migration_source

    downgrade_source = migration_source.split("def downgrade")[1]
    assert 'op.drop_table("flows")' in downgrade_source


def test_conversations_flow_id_migration_is_additive():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0009_conversations_flow_id.py"
    )
    migration_source = migration_path.read_text()
    assert 'revision: str = "0009"' in migration_source
    assert 'down_revision: str | None = "0008"' in migration_source
    assert 'op.add_column(\n        "conversations"' in migration_source or (
        '"conversations"' in migration_source and "flow_id" in migration_source
    )
    assert "is_default = true" in migration_source
    assert "conversations_flow_channel_external_idx" in migration_source
    assert "conversations_flow_channel_customer_idx" in migration_source
    downgrade_source = migration_source.split("def downgrade")[1]
    assert 'op.drop_column("conversations", "flow_id")' in downgrade_source


def test_message_inbound_idempotency_migration():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0010_message_inbound_idempotency.py"
    )
    migration_source = migration_path.read_text()
    assert 'revision: str = "0010"' in migration_source
    assert 'down_revision: str | None = "0009"' in migration_source
    assert "idempotency_key" in migration_source
    assert "messages_incoming_conversation_external_unique" in migration_source
    assert "messages_incoming_conversation_idempotency_unique" in migration_source
    assert "messages_business_external_message_id_unique" in migration_source
    downgrade_source = migration_source.split("def downgrade")[1]
    assert "op.drop_column" in downgrade_source and "idempotency_key" in downgrade_source
