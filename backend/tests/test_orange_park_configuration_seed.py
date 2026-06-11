import importlib.util
import ast
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
        TenantBusinessProfile,
        TenantAiProfile,
        TenantChannelSetting,
        TenantKnowledgeSource,
    }
    assert session.add.call_count == 8

    added_rows = [call.args[0] for call in session.add.call_args_list]
    business = next(row for row in added_rows if isinstance(row, Business))
    business_profile = next(
        row for row in added_rows if isinstance(row, TenantBusinessProfile)
    )
    ai_profile = next(row for row in added_rows if isinstance(row, TenantAiProfile))
    channel = next(row for row in added_rows if isinstance(row, TenantChannelSetting))
    knowledge = [
        row for row in added_rows if isinstance(row, TenantKnowledgeSource)
    ]

    assert business.external_id == ORANGE_PARK_BUSINESS_EXTERNAL_ID
    assert business.business_type == "real_estate"
    assert business.language == "uk"
    assert "Response quality rules for this business context" in (
        business_profile.business_description
    )
    assert "do not repeat it unless the customer asks about location again" in (
        business_profile.business_description
    )
    assert "давай" in business_profile.business_description
    assert "з'єднуй" in business_profile.business_description
    assert "номер телефону" in business_profile.business_description
    assert "дай контакти" in business_profile.business_description
    assert (
        "Залиште, будь ласка, ваш номер телефону — менеджер зв’яжеться з вами напряму."
        in business_profile.business_description
    )
    assert "Never invent Orange Park phone numbers" in (
        business_profile.business_description
    )
    assert ai_profile.language == "uk"
    assert len(ai_profile.response_style) <= 100
    assert "no repeat address" in ai_profile.response_style
    assert "criteria only" in ai_profile.response_style
    assert "ask phone" in ai_profile.response_style
    assert "no loops" in ai_profile.response_style
    assert "phone close" in ai_profile.response_style
    assert "Ukrainian /start and first greeting by default." in (
        ai_profile.metadata_["behavior_rules"]
    )
    assert "Never output English unless customer writes English." in (
        ai_profile.metadata_["behavior_rules"]
    )
    assert channel.channel == ORANGE_PARK_CHANNEL
    assert channel.allow_links is False
    assert channel.allow_emojis is False
    assert channel.metadata_["default_start_language"] == "uk"
    assert channel.metadata_["start_greeting"].startswith("Вітаю!")
    assert len(knowledge) == 3
    assert {row.source_type for row in knowledge} == {
        "conversation_style",
        "faq",
        "pricing",
    }
    style = next(row for row in knowledge if row.source_type == "conversation_style")
    assert style.title == "Orange Park Conversation Style Guide"
    assert "Use this as behavior guidance only" in style.content
    assert "not_factual_knowledge" in style.tags


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
        TenantKnowledgeSource(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            source_type="conversation_style",
            title="Orange Park Conversation Style Guide",
            content="old style",
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
    assert business.language == "uk"
    assert rows[3].language == "uk"
    assert len(rows[3].response_style) <= 100
    assert "no repeat address" in rows[3].response_style
    assert "criteria only" in rows[3].response_style
    assert "ask phone" in rows[3].response_style
    assert "no loops" in rows[3].response_style
    assert "phone close" in rows[3].response_style
    assert "repeating address or location after it was already answered" in (
        rows[3].forbidden_promises
    )
    assert "saying request was passed before phone number is collected" in (
        rows[3].forbidden_promises
    )
    assert "Use conversation history to avoid repeating facts." in (
        rows[3].metadata_["behavior_rules"]
    )
    assert rows[4].allow_links is False
    assert rows[4].metadata_["default_start_language"] == "uk"
    assert rows[5].content.startswith("# Orange Park")
    assert "requires_manager_confirmation" in rows[6].tags
    assert "Use this as behavior guidance only" in rows[7].content
    assert "After collecting a phone number" in rows[7].content
    assert "not_factual_knowledge" in rows[7].tags


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


def test_orange_park_seed_has_no_flow_dependency():
    module_source = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "seed"
        / "orange_park_configuration.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "app.models.flow",
        "from app.models import Flow",
        "Flow(",
        "select(Flow",
        "_ensure_default_flow",
        "_get_flow_by_key",
        "ORANGE_PARK_FLOW_KEY",
        "ORANGE_PARK_FLOW_NAME",
        "\"flows\"",
        "'flows'",
    )
    for value in forbidden:
        assert value not in module_source


def test_orange_park_seed_test_does_not_import_flow_model():
    parsed = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    for node in ast.walk(parsed):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "app.models.flow"
            assert not (
                node.module == "app.models"
                and any(alias.name == "Flow" for alias in node.names)
            )


@pytest.mark.anyio
async def test_orange_park_seed_enforces_language_repetition_and_phone_closing_rules():
    session = _empty_seed_session()

    await seed_orange_park_configuration(session)

    added_rows = [call.args[0] for call in session.add.call_args_list]
    business = next(row for row in added_rows if isinstance(row, Business))
    business_profile = next(
        row for row in added_rows if isinstance(row, TenantBusinessProfile)
    )
    ai_profile = next(row for row in added_rows if isinstance(row, TenantAiProfile))
    channel = next(row for row in added_rows if isinstance(row, TenantChannelSetting))
    style = next(
        row
        for row in added_rows
        if isinstance(row, TenantKnowledgeSource)
        and row.source_type == "conversation_style"
    )

    assert business.external_id == ORANGE_PARK_BUSINESS_EXTERNAL_ID
    assert business_profile.tenant_id == ai_profile.tenant_id == style.tenant_id
    assert business_profile.business_id == ai_profile.business_id == style.business_id
    assert ai_profile.language == "uk"
    assert len(ai_profile.response_style) <= 100
    assert "no repeat address" in ai_profile.response_style
    assert "criteria only" in ai_profile.response_style
    assert "ask phone" in ai_profile.response_style
    assert "no loops" in ai_profile.response_style
    assert "phone close" in ai_profile.response_style
    assert "repeating address or location after it was already answered" in (
        ai_profile.forbidden_promises
    )
    assert "verbose manager handoff wording" in ai_profile.forbidden_promises
    assert "open-ended closing after phone is collected" in ai_profile.forbidden_promises
    assert "thanking for a phone number before the customer provides one" in (
        ai_profile.forbidden_promises
    )
    assert "open-ended extra sentence when customer is waiting for manager call" in (
        ai_profile.forbidden_promises
    )
    assert "long explanation after short handoff intent like давай or з'єднуй" in (
        ai_profile.forbidden_promises
    )
    assert "repeating the same manager-confirmation or refusal block twice" in (
        ai_profile.forbidden_promises
    )
    assert "inventing Orange Park phone, manager contact, or contact details" in (
        ai_profile.forbidden_promises
    )
    assert "giving manager phone when official contact is absent from business context" in (
        ai_profile.forbidden_promises
    )
    assert "Ukrainian /start and first greeting by default." in (
        ai_profile.metadata_["behavior_rules"]
    )
    assert "Never output English unless customer writes English." in (
        ai_profile.metadata_["behavior_rules"]
    )
    assert "Never mix languages or use hybrid words." in (
        ai_profile.metadata_["behavior_rules"]
    )
    assert "Keep Telegram replies concise: 1-3 short sentences." in (
        ai_profile.metadata_["behavior_rules"]
    )
    assert (
        "If address or location was already answered, do not repeat it when customer gives budget, area, payment, or handoff criteria."
        in ai_profile.metadata_["behavior_rules"]
    )
    assert "If customer gives new buying criteria, respond only to those criteria." in (
        ai_profile.metadata_["behavior_rules"]
    )
    assert (
        "After phone is collected, use concise closing: Дякую. Запит передано менеджеру. Очікуйте дзвінок."
        in ai_profile.metadata_["behavior_rules"]
    )
    assert (
        "Short handoff intent such as давай, з'єднуй, так, ок, or добре means: ask only for phone if phone is not collected."
        in ai_profile.metadata_["behavior_rules"]
    )
    assert (
        "Contact requests such as номер телефону, дай контакти, дай дані, номер, or телефон менеджера mean: if no official contact exists in current business context, reply exactly: Залиште, будь ласка, ваш номер телефону — менеджер зв’яжеться з вами напряму."
        in ai_profile.metadata_["behavior_rules"]
    )
    assert "Never invent Orange Park phone numbers or manager contacts." in (
        ai_profile.metadata_["behavior_rules"]
    )
    assert "Never repeat the same refusal or manager-confirmation loop twice." in (
        ai_profile.metadata_["behavior_rules"]
    )
    assert "hesitуйте" not in ai_profile.response_style

    assert channel.metadata_["default_start_language"] == "uk"
    assert "Hello! Welcome" not in channel.metadata_["start_greeting"]
    assert channel.metadata_["start_greeting"].startswith("Вітаю!")

    assert "Telegram /start and the first greeting must be Ukrainian" in style.content
    assert "Never output English unless the customer explicitly writes in English" in (
        style.content
    )
    assert "Never mix languages in the same sentence" in style.content
    assert "hybrid words" in style.content
    assert "Keep most Telegram replies to 1-3 short sentences" in style.content
    assert "Use conversation history to avoid repeating facts" in style.content
    assert "Do not repeat location, apartment types, payment options" in style.content
    assert "If address or location was already answered" in style.content
    assert "respond only to those criteria" in style.content
    assert '"давай"' in style.content
    assert '"з\'єднуй"' in style.content
    assert '"номер телефону"' in style.content
    assert '"дай контакти"' in style.content
    assert (
        "Добре. Напишіть, будь ласка, номер телефону — менеджер зв’яжеться з вами."
        in style.content
    )
    assert (
        "Залиште, будь ласка, ваш номер телефону — менеджер зв’яжеться з вами напряму."
        in style.content
    )
    assert "Never invent Orange Park phone numbers" in style.content
    assert "Never repeat the same refusal or manager-confirmation block twice" in (
        style.content
    )
    assert "do not say the request was passed yet" in style.content
    assert "Do not thank the customer for a phone number" in style.content
    assert 'reply only: "Дякую. Запит передано менеджеру. Очікуйте дзвінок."' in (
        style.content
    )
    assert "After collecting a phone number, acknowledge it" in style.content
    assert "Дякую. Запит передано менеджеру. Очікуйте дзвінок." in style.content
    assert "Hello! Welcome" not in style.content
    assert "hesitуйте" not in style.content


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
