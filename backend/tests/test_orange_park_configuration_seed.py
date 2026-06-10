import importlib.util
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.business import Business
from app.models.flow import Flow
from app.models.tenant import Tenant
from app.models.tenant_ai_profile import TenantAiProfile
from app.models.tenant_business_profile import TenantBusinessProfile
from app.models.tenant_channel_setting import TenantChannelSetting
from app.models.tenant_knowledge_source import TenantKnowledgeSource
from app.seed.orange_park_configuration import (
    ORANGE_PARK_BUSINESS_EXTERNAL_ID,
    ORANGE_PARK_CHANNEL,
    ORANGE_PARK_FLOW_KEY,
    ORANGE_PARK_TENANT_SLUG,
    OrangeParkConfigurationSeedError,
    seed_orange_park_configuration,
)


def _execute_scalar(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _empty_seed_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(return_value=_execute_scalar(None))
    session.flush = AsyncMock(return_value=None)
    return session


@pytest.mark.anyio
async def test_orange_park_seed_first_run_inserts_all_entities():
    session = _empty_seed_session()

    result = await seed_orange_park_configuration(session)

    assert result.tenant_slug == ORANGE_PARK_TENANT_SLUG
    assert result.business_external_id == ORANGE_PARK_BUSINESS_EXTERNAL_ID

    added_models = {type(call.args[0]) for call in session.add.call_args_list}
    assert added_models == {
        Tenant,
        Business,
        Flow,
        TenantBusinessProfile,
        TenantAiProfile,
        TenantChannelSetting,
        TenantKnowledgeSource,
    }
    assert session.add.call_count == 8

    added_rows = [call.args[0] for call in session.add.call_args_list]
    business = next(row for row in added_rows if isinstance(row, Business))
    flow = next(row for row in added_rows if isinstance(row, Flow))
    channel = next(row for row in added_rows if isinstance(row, TenantChannelSetting))
    knowledge = [
        row for row in added_rows if isinstance(row, TenantKnowledgeSource)
    ]

    assert business.external_id == ORANGE_PARK_BUSINESS_EXTERNAL_ID
    assert business.business_type == "real_estate"
    assert flow.tenant_id == business.tenant_id
    assert flow.business_id == business.id
    assert flow.flow_key == ORANGE_PARK_FLOW_KEY
    assert flow.flow_name == "Orange Park Telegram MVP"
    assert flow.is_default is True
    assert flow.status == "active"
    assert channel.channel == ORANGE_PARK_CHANNEL
    assert channel.allow_links is False
    assert channel.allow_emojis is False
    assert len(knowledge) == 2
    assert {row.source_type for row in knowledge} == {"faq", "pricing"}


@pytest.mark.anyio
async def test_orange_park_seed_second_run_updates_without_duplicates():
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Old name",
        slug=ORANGE_PARK_TENANT_SLUG,
        status="active",
    )
    business = Business(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        external_id=ORANGE_PARK_BUSINESS_EXTERNAL_ID,
        name="Old business",
        storage_mode="shared",
        status="active",
    )
    rows = [
        tenant,
        business,
        Flow(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            flow_key=ORANGE_PARK_FLOW_KEY,
            flow_name="Old flow",
            is_default=False,
            status="inactive",
        ),
        TenantBusinessProfile(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
        ),
        TenantAiProfile(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
        ),
        TenantChannelSetting(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            channel=ORANGE_PARK_CHANNEL,
        ),
        TenantKnowledgeSource(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            source_type="faq",
            title="Orange Park FAQ",
            content="old faq",
        ),
        TenantKnowledgeSource(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            source_type="pricing",
            title="Orange Park Prices And Availability - Manager Confirmed Only",
            content="old pricing",
        ),
    ]

    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(
        side_effect=[_execute_scalar(row) for row in rows]
    )
    session.flush = AsyncMock(return_value=None)

    result = await seed_orange_park_configuration(session)

    assert result.tenant_id == tenant.id
    assert result.business_id == business.id
    session.add.assert_not_called()
    assert business.name == "Orange Park / ЖК Orange Park"
    assert rows[2].is_default is True
    assert rows[2].status == "active"
    assert rows[5].allow_links is False
    assert rows[6].content.startswith("# Orange Park")
    assert "requires_manager_confirmation" in rows[7].tags


@pytest.mark.anyio
async def test_orange_park_seed_fails_if_business_belongs_to_wrong_tenant():
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Orange Park",
        slug=ORANGE_PARK_TENANT_SLUG,
        status="active",
    )
    business = Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id=ORANGE_PARK_BUSINESS_EXTERNAL_ID,
        name="Wrong tenant business",
        storage_mode="shared",
        status="active",
    )

    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(
        side_effect=[_execute_scalar(tenant), _execute_scalar(business)]
    )
    session.flush = AsyncMock(return_value=None)

    with pytest.raises(OrangeParkConfigurationSeedError, match="belongs to tenant"):
        await seed_orange_park_configuration(session)


def test_orange_park_seed_source_contains_no_secrets_or_bitrix_config():
    module_source = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "seed"
        / "orange_park_configuration.py"
    ).read_text(encoding="utf-8").lower()
    forbidden = (
        "telegram_bot_token",
        "bitrix",
        "sk-",
        "api_key",
        "password",
        "secret",
        "bearer ",
        "webhook_url",
    )
    for value in forbidden:
        assert value not in module_source

    assert "lead_creation_enabled" in module_source
    assert "app.models.flow" in module_source
    assert "orange_park_flow_key" in module_source


@pytest.mark.anyio
async def test_orange_park_runner_dry_run_rolls_back_instead_of_commit():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "seed_orange_park_configuration.py"
    )
    spec = importlib.util.spec_from_file_location(
        "seed_orange_park_configuration_script",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)

    session = AsyncMock()
    session.rollback = AsyncMock(return_value=None)
    session.commit = AsyncMock(return_value=None)

    class _SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    with patch.object(script, "AsyncSessionLocal", return_value=_SessionContext()):
        with patch.object(script, "seed_orange_park_configuration") as seed:
            seed.return_value = AsyncMock()
            seed.return_value.tenant_slug = ORANGE_PARK_TENANT_SLUG
            seed.return_value.business_external_id = ORANGE_PARK_BUSINESS_EXTERNAL_ID
            seed.return_value.tenant_id = uuid.uuid4()
            seed.return_value.business_id = uuid.uuid4()
            seed.return_value.actions = ("updated tenant",)
            await script.run_seed(
                dry_run=True,
                tenant_slug=ORANGE_PARK_TENANT_SLUG,
                tenant_name="Orange Park",
            )

    session.rollback.assert_awaited_once()
    session.commit.assert_not_called()
