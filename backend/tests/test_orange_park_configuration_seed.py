import importlib.util
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.business import Business
from app.models.tenant import Tenant
from app.models.tenant_ai_profile import TenantAiProfile
from app.models.tenant_business_profile import TenantBusinessProfile
from app.models.tenant_channel_setting import TenantChannelSetting
from app.models.tenant_knowledge_source import TenantKnowledgeSource
from app.seed.orange_park_configuration import (
    ORANGE_PARK_BUSINESS_EXTERNAL_ID,
    ORANGE_PARK_CHANNEL,
    ORANGE_PARK_TENANT_SLUG,
    OrangeParkConfigurationSeedError,
    seed_orange_park_configuration,
)


OBSOLETE_CONTACT_PHRASES = (
    "Будь ласка, залиште дані у такому форматі",
    "Пожалуйста, оставьте данные",
    "If phone is missing",
    "If phone is already provided",
    "ask only for phone",
    "ask only for first and last name",
    "Напишіть, будь ласка, номер телефону",
    "Залиште, будь ласка, ваш номер телефону",
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


def _seed_rows(session: AsyncMock) -> list[object]:
    return [call.args[0] for call in session.add.call_args_list]


@pytest.mark.anyio
async def test_orange_park_seed_creates_clean_layered_configuration():
    session = _empty_seed_session()

    result = await seed_orange_park_configuration(session)

    assert result.tenant_slug == ORANGE_PARK_TENANT_SLUG
    assert result.business_external_id == ORANGE_PARK_BUSINESS_EXTERNAL_ID
    assert session.add.call_count == 8

    rows = _seed_rows(session)
    business = next(row for row in rows if isinstance(row, Business))
    business_profile = next(
        row for row in rows if isinstance(row, TenantBusinessProfile)
    )
    ai_profile = next(row for row in rows if isinstance(row, TenantAiProfile))
    channel = next(row for row in rows if isinstance(row, TenantChannelSetting))
    knowledge = [
        row for row in rows if isinstance(row, TenantKnowledgeSource)
    ]

    assert business.external_id == "orange-park"
    assert business.language == "uk"

    assert business_profile.business_description.startswith(
        "# Orange Park — Factual Business Data"
    )
    assert "Response quality rules" not in business_profile.business_description
    assert "Current inventory, exact prices" in business_profile.business_limitations
    assert "manager_consultation" not in business_profile.services

    behavior = ai_profile.metadata_["behavior_instructions"]
    assert "behavior_rules" not in ai_profile.metadata_
    assert ai_profile.ask_for_name is None
    assert ai_profile.ask_for_phone is None
    assert "single source of truth for Orange Park AI behavior" in behavior
    assert "Use native Telegram contact sharing." in behavior
    assert "Do not ask customer to type phone manually." in behavior
    assert (
        "Для зв'язку з менеджером, будь ласка, натисніть кнопку «📱 Поділитися номером»."
        in behavior
    )
    assert "Дякуємо. Запит передано менеджеру. Очікуйте дзвінок." in behavior
    assert "exact apartment availability" in ai_profile.forbidden_promises

    assert channel.channel == ORANGE_PARK_CHANNEL
    assert channel.allow_emojis is True
    assert channel.allow_links is False
    assert channel.metadata_["start_greeting"].startswith("Добрий день! 👋")

    assert {row.source_type for row in knowledge} == {
        "faq",
        "pricing",
        "conversation_style",
    }
    style = next(row for row in knowledge if row.source_type == "conversation_style")
    assert style.content.startswith("# Orange Park — Conversation Examples")
    assert "Normative AI behavior is defined only" in style.content
    assert "Native Telegram contact flow" not in style.content

    active_text = "\n".join(
        (
            business_profile.business_description,
            business_profile.business_limitations,
            behavior,
            *(row.content for row in knowledge),
        )
    )
    assert all(phrase not in active_text for phrase in OBSOLETE_CONTACT_PHRASES)


@pytest.mark.anyio
async def test_orange_park_seed_updates_existing_rows_without_duplicates():
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
    business_profile = TenantBusinessProfile(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        business_id=business.id,
        business_description="legacy",
        business_limitations="legacy",
    )
    ai_profile = TenantAiProfile(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        business_id=business.id,
        metadata_={"behavior_rules": ["legacy"]},
    )
    channel = TenantChannelSetting(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        business_id=business.id,
        channel=ORANGE_PARK_CHANNEL,
    )
    knowledge = [
        TenantKnowledgeSource(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            source_type="faq",
            title="Orange Park FAQ",
            content="legacy",
        ),
        TenantKnowledgeSource(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            source_type="pricing",
            title="Orange Park Prices And Availability - Manager Confirmed Only",
            content="legacy",
        ),
        TenantKnowledgeSource(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            source_type="conversation_style",
            title="Orange Park Conversation Style Guide",
            content="legacy",
        ),
    ]
    existing = [
        tenant,
        business,
        business_profile,
        ai_profile,
        channel,
        *knowledge,
    ]
    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(
        side_effect=[_execute_scalar(row) for row in existing]
    )
    session.flush = AsyncMock(return_value=None)

    await seed_orange_park_configuration(session)

    session.add.assert_not_called()
    assert business_profile.business_description.startswith(
        "# Orange Park — Factual Business Data"
    )
    assert "behavior_rules" not in ai_profile.metadata_
    assert "behavior_instructions" in ai_profile.metadata_
    assert ai_profile.ask_for_name is None
    assert ai_profile.ask_for_phone is None
    assert channel.allow_emojis is True
    assert all(row.content != "legacy" for row in knowledge)


@pytest.mark.anyio
async def test_orange_park_seed_rejects_business_from_another_tenant():
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


def test_orange_park_seed_has_no_flow_or_secret_dependency():
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
        "app.models.flow",
        "_ensure_default_flow",
    )
    assert all(value not in module_source for value in forbidden)


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
