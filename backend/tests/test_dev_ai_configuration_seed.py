import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.business import Business
from app.models.prompt_template import PromptTemplate
from app.models.tenant import Tenant
from app.models.tenant_ai_profile import TenantAiProfile
from app.models.tenant_business_profile import TenantBusinessProfile
from app.models.tenant_channel_setting import TenantChannelSetting
from app.models.tenant_knowledge_source import TenantKnowledgeSource
from app.seed.dev_ai_configuration import (
    DEMO_AI_PROFILE_ID,
    DEMO_BUSINESS_EXTERNAL_ID,
    DEMO_BUSINESS_PROFILE_ID,
    DEMO_CHANNEL_SETTING_ID,
    DEMO_KNOWLEDGE_OPENING_HOURS_ID,
    DEMO_TENANT_SLUG,
    DevAiConfigurationSeedError,
    PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
    PROMPT_TEMPLATE_DEFINITIONS,
    PROMPT_TEMPLATE_FALLBACK_KEY,
    seed_dev_ai_configuration,
)


def _session_get_map(existing: dict) -> AsyncMock:
    async def _get(model, row_id):
        return existing.get((model, row_id))

    return AsyncMock(side_effect=_get)


def _execute_scalar(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _execute_scalars(values: list):
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


@pytest.mark.anyio
async def test_seed_refuses_production_environment():
    session = AsyncMock()
    with patch("app.seed.dev_ai_configuration.settings") as mock_settings:
        mock_settings.environment = "production"
        with pytest.raises(RuntimeError, match="development environments"):
            await seed_dev_ai_configuration(session)

    session.add.assert_not_called()


@pytest.mark.anyio
async def test_prompt_template_definitions_have_unique_template_keys():
    keys = [definition["template_key"] for definition in PROMPT_TEMPLATE_DEFINITIONS]
    assert len(keys) == len(set(keys))
    assert PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY in keys
    assert PROMPT_TEMPLATE_FALLBACK_KEY in keys


def test_seed_constants_contain_no_secrets():
    module_source = (
        Path(__file__).resolve().parents[1] / "app" / "seed" / "dev_ai_configuration.py"
    ).read_text().lower()
    for forbidden in ("api_key", "sk-", "password", "secret", "bearer "):
        assert forbidden not in module_source


def _empty_seed_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.get = _session_get_map({})
    session.execute = AsyncMock(return_value=_execute_scalar(None))
    session.flush = AsyncMock(return_value=None)
    return session


@pytest.mark.anyio
async def test_seed_first_run_inserts_all_entities():
    session = _empty_seed_session()

    with patch("app.seed.dev_ai_configuration.settings") as mock_settings:
        mock_settings.environment = "development"
        result = await seed_dev_ai_configuration(session)

    assert result.tenant_slug == DEMO_TENANT_SLUG
    assert result.business_external_id == DEMO_BUSINESS_EXTERNAL_ID
    assert len(result.prompt_template_keys) == 2

    added_models = {type(call.args[0]) for call in session.add.call_args_list}
    assert added_models == {
        Tenant,
        Business,
        PromptTemplate,
        TenantBusinessProfile,
        TenantAiProfile,
        TenantChannelSetting,
        TenantKnowledgeSource,
    }
    assert session.add.call_count == 9


@pytest.mark.anyio
async def test_seed_second_run_does_not_insert_duplicates():
    tenant = Tenant(id=uuid.uuid4(), name="Demo", slug=DEMO_TENANT_SLUG, status="active")
    business = Business(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        external_id=DEMO_BUSINESS_EXTERNAL_ID,
        name="Demo",
        storage_mode="shared",
        status="active",
    )
    templates = [
        PromptTemplate(
            template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
            system_prompt="existing",
        ),
        PromptTemplate(
            template_key=PROMPT_TEMPLATE_FALLBACK_KEY,
            system_prompt="existing",
        ),
    ]
    business_profile = TenantBusinessProfile(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        business_id=business.id,
    )
    ai_profile = TenantAiProfile(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        business_id=business.id,
    )
    channel_setting = TenantChannelSetting(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        business_id=business.id,
        channel="whatsapp",
    )
    knowledge = [
        TenantKnowledgeSource(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            source_type="faq",
            title="Opening hours",
            content="Already seeded",
        ),
        TenantKnowledgeSource(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            source_type="pricing",
            title="Haircut pricing",
            content="Already seeded",
        ),
    ]

    session = AsyncMock()
    session.add = MagicMock()

    async def _execute(statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is Tenant:
            return _execute_scalar(tenant)
        if entity is Business:
            return _execute_scalar(business)
        if entity is PromptTemplate:
            key = statement._where_criteria[0].right.value
            match = next(t for t in templates if t.template_key == key)
            return _execute_scalar(match)
        if entity is TenantBusinessProfile:
            return _execute_scalar(business_profile)
        if entity is TenantAiProfile:
            return _execute_scalar(ai_profile)
        if entity is TenantChannelSetting:
            return _execute_scalar(channel_setting)
        if entity is TenantKnowledgeSource:
            title = statement._where_criteria[2].right.value
            match = next(k for k in knowledge if k.title == title)
            return _execute_scalar(match)
        return _execute_scalar(None)

    session.execute = AsyncMock(side_effect=_execute)
    session.get = _session_get_map(
        {
            (TenantBusinessProfile, business_profile.id): business_profile,
            (TenantAiProfile, ai_profile.id): ai_profile,
            (TenantChannelSetting, channel_setting.id): channel_setting,
            (TenantKnowledgeSource, knowledge[0].id): knowledge[0],
            (TenantKnowledgeSource, knowledge[1].id): knowledge[1],
        }
    )
    session.flush = AsyncMock(return_value=None)

    with patch("app.seed.dev_ai_configuration.settings") as mock_settings:
        mock_settings.environment = "development"
        result = await seed_dev_ai_configuration(session)

    assert result.tenant_id == tenant.id
    assert result.business_id == business.id
    session.add.assert_not_called()


@pytest.mark.anyio
async def test_seed_tenant_owned_rows_use_demo_tenant_scope():
    session = _empty_seed_session()

    with patch("app.seed.dev_ai_configuration.settings") as mock_settings:
        mock_settings.environment = "test"
        await seed_dev_ai_configuration(session)

    tenant = session.add.call_args_list[0].args[0]
    business = session.add.call_args_list[1].args[0]

    for call in session.add.call_args_list[2:]:
        row = call.args[0]
        if isinstance(row, PromptTemplate):
            assert not hasattr(row, "tenant_id")
            continue
        assert row.tenant_id == tenant.id
        assert row.business_id == business.id


@pytest.mark.anyio
async def test_seed_fails_when_existing_business_has_wrong_tenant():
    demo_tenant = Tenant(
        id=uuid.uuid4(),
        name="Demo",
        slug=DEMO_TENANT_SLUG,
        status="active",
    )
    other_tenant_id = uuid.uuid4()
    business = Business(
        id=uuid.uuid4(),
        tenant_id=other_tenant_id,
        external_id=DEMO_BUSINESS_EXTERNAL_ID,
        name="Other tenant business",
        storage_mode="shared",
        status="active",
    )

    session = AsyncMock()
    session.add = MagicMock()

    async def _execute(statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is Tenant:
            return _execute_scalar(demo_tenant)
        if entity is Business:
            return _execute_scalar(business)
        return _execute_scalar(None)

    session.execute = AsyncMock(side_effect=_execute)
    session.get = _session_get_map({})
    session.flush = AsyncMock(return_value=None)

    with patch("app.seed.dev_ai_configuration.settings") as mock_settings:
        mock_settings.environment = "development"
        with pytest.raises(DevAiConfigurationSeedError, match="belongs to tenant"):
            await seed_dev_ai_configuration(session)


@pytest.mark.anyio
async def test_seed_fails_when_fixed_uuid_row_has_wrong_tenant_scope():
    tenant = Tenant(id=uuid.uuid4(), name="Demo", slug=DEMO_TENANT_SLUG, status="active")
    business = Business(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        external_id=DEMO_BUSINESS_EXTERNAL_ID,
        name="Demo",
        storage_mode="shared",
        status="active",
    )
    wrong_scope_profile = TenantBusinessProfile(
        id=DEMO_BUSINESS_PROFILE_ID,
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
    )

    session = AsyncMock()
    session.add = MagicMock()

    async def _execute(statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is Tenant:
            return _execute_scalar(tenant)
        if entity is Business:
            return _execute_scalar(business)
        return _execute_scalar(None)

    session.execute = AsyncMock(side_effect=_execute)
    session.get = _session_get_map(
        {(TenantBusinessProfile, DEMO_BUSINESS_PROFILE_ID): wrong_scope_profile}
    )
    session.flush = AsyncMock(return_value=None)

    with patch("app.seed.dev_ai_configuration.settings") as mock_settings:
        mock_settings.environment = "development"
        with pytest.raises(DevAiConfigurationSeedError, match="tenant business profile"):
            await seed_dev_ai_configuration(session)


@pytest.mark.anyio
async def test_seed_fails_when_fixed_uuid_channel_setting_has_wrong_channel():
    tenant = Tenant(id=uuid.uuid4(), name="Demo", slug=DEMO_TENANT_SLUG, status="active")
    business = Business(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        external_id=DEMO_BUSINESS_EXTERNAL_ID,
        name="Demo",
        storage_mode="shared",
        status="active",
    )
    business_profile = TenantBusinessProfile(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        business_id=business.id,
    )
    ai_profile = TenantAiProfile(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        business_id=business.id,
    )
    wrong_channel = TenantChannelSetting(
        id=DEMO_CHANNEL_SETTING_ID,
        tenant_id=tenant.id,
        business_id=business.id,
        channel="telegram",
    )
    templates = [
        PromptTemplate(
            template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
            system_prompt="existing",
        ),
        PromptTemplate(
            template_key=PROMPT_TEMPLATE_FALLBACK_KEY,
            system_prompt="existing",
        ),
    ]

    session = AsyncMock()
    session.add = MagicMock()

    async def _execute(statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is Tenant:
            return _execute_scalar(tenant)
        if entity is Business:
            return _execute_scalar(business)
        if entity is PromptTemplate:
            key = statement._where_criteria[0].right.value
            match = next(t for t in templates if t.template_key == key)
            return _execute_scalar(match)
        if entity is TenantBusinessProfile:
            return _execute_scalar(business_profile)
        if entity is TenantAiProfile:
            return _execute_scalar(ai_profile)
        return _execute_scalar(None)

    session.execute = AsyncMock(side_effect=_execute)
    session.get = _session_get_map(
        {
            (TenantBusinessProfile, DEMO_BUSINESS_PROFILE_ID): business_profile,
            (TenantAiProfile, DEMO_AI_PROFILE_ID): ai_profile,
            (TenantChannelSetting, DEMO_CHANNEL_SETTING_ID): wrong_channel,
        }
    )
    session.flush = AsyncMock(return_value=None)

    with patch("app.seed.dev_ai_configuration.settings") as mock_settings:
        mock_settings.environment = "development"
        with pytest.raises(DevAiConfigurationSeedError, match="channel"):
            await seed_dev_ai_configuration(session)


@pytest.mark.anyio
async def test_seed_fails_when_fixed_uuid_knowledge_source_has_wrong_title():
    tenant = Tenant(id=uuid.uuid4(), name="Demo", slug=DEMO_TENANT_SLUG, status="active")
    business = Business(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        external_id=DEMO_BUSINESS_EXTERNAL_ID,
        name="Demo",
        storage_mode="shared",
        status="active",
    )
    templates = [
        PromptTemplate(
            template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
            system_prompt="existing",
        ),
        PromptTemplate(
            template_key=PROMPT_TEMPLATE_FALLBACK_KEY,
            system_prompt="existing",
        ),
    ]
    business_profile = TenantBusinessProfile(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        business_id=business.id,
    )
    ai_profile = TenantAiProfile(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        business_id=business.id,
    )
    channel_setting = TenantChannelSetting(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        business_id=business.id,
        channel="whatsapp",
    )
    wrong_title_knowledge = TenantKnowledgeSource(
        id=DEMO_KNOWLEDGE_OPENING_HOURS_ID,
        tenant_id=tenant.id,
        business_id=business.id,
        source_type="faq",
        title="Wrong title",
        content="content",
    )

    session = AsyncMock()
    session.add = MagicMock()

    async def _execute(statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is Tenant:
            return _execute_scalar(tenant)
        if entity is Business:
            return _execute_scalar(business)
        if entity is PromptTemplate:
            key = statement._where_criteria[0].right.value
            match = next(t for t in templates if t.template_key == key)
            return _execute_scalar(match)
        if entity is TenantBusinessProfile:
            return _execute_scalar(business_profile)
        if entity is TenantAiProfile:
            return _execute_scalar(ai_profile)
        if entity is TenantChannelSetting:
            return _execute_scalar(channel_setting)
        return _execute_scalar(None)

    session.execute = AsyncMock(side_effect=_execute)
    session.get = _session_get_map(
        {
            (TenantBusinessProfile, DEMO_BUSINESS_PROFILE_ID): business_profile,
            (TenantAiProfile, DEMO_AI_PROFILE_ID): ai_profile,
            (TenantChannelSetting, DEMO_CHANNEL_SETTING_ID): channel_setting,
            (TenantKnowledgeSource, DEMO_KNOWLEDGE_OPENING_HOURS_ID): wrong_title_knowledge,
        }
    )
    session.flush = AsyncMock(return_value=None)

    with patch("app.seed.dev_ai_configuration.settings") as mock_settings:
        mock_settings.environment = "development"
        with pytest.raises(DevAiConfigurationSeedError, match="title"):
            await seed_dev_ai_configuration(session)
