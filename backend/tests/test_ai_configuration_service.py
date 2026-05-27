import uuid
from unittest.mock import AsyncMock

import pytest

from app.exceptions import PromptTemplateNotFoundError, TenantContextError
from app.models.prompt_template import PromptTemplate
from app.models.tenant_ai_profile import TenantAiProfile
from app.models.tenant_business_profile import TenantBusinessProfile
from app.models.tenant_channel_setting import TenantChannelSetting
from app.schemas.ai_configuration import (
    FORBIDDEN_TENANT_PROMPT_OVERRIDE_KEYS,
    TenantBehaviorConfig,
    TenantBusinessContextConfig,
)
from app.seed.dev_ai_configuration import PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY
from app.services.ai_configuration_service import AiConfigurationService


@pytest.fixture
def tenant_scope() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


@pytest.fixture
def platform_template() -> PromptTemplate:
    return PromptTemplate(
        id=uuid.uuid4(),
        template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
        template_name="Customer reply",
        version="1",
        system_prompt="Platform core safety and role instructions.",
        is_active=True,
    )


@pytest.fixture
def full_tenant_profiles(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
) -> tuple[TenantBusinessProfile, TenantAiProfile, TenantChannelSetting]:
    tenant_id, business_id = tenant_scope
    business_profile = TenantBusinessProfile(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        business_description="Local barbershop in Zurich.",
        services={"haircut": {"price": 35, "currency": "CHF"}},
        city="Zurich",
        country="CH",
    )
    ai_profile = TenantAiProfile(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        profile_name="Default",
        tone="friendly",
        response_style="concise",
        language="de",
        fallback_response="We will reply shortly.",
    )
    channel_setting = TenantChannelSetting(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        channel="whatsapp",
        response_style="short",
        max_response_length=500,
        allow_emojis=False,
        allow_links=True,
    )
    return business_profile, ai_profile, channel_setting


def _service_with_mocks(
    *,
    template: PromptTemplate | None,
    business_profile: TenantBusinessProfile | None = None,
    ai_profile: TenantAiProfile | None = None,
    channel_setting: TenantChannelSetting | None = None,
) -> AiConfigurationService:
    business_profile_service = AsyncMock()
    business_profile_service.get_for_business = AsyncMock(return_value=business_profile)
    ai_profile_service = AsyncMock()
    ai_profile_service.get_for_business = AsyncMock(return_value=ai_profile)
    channel_setting_service = AsyncMock()
    channel_setting_service.get_for_channel = AsyncMock(return_value=channel_setting)
    prompt_template_service = AsyncMock()
    prompt_template_service.get_by_template_key = AsyncMock(return_value=template)
    return AiConfigurationService(
        business_profile_service=business_profile_service,
        ai_profile_service=ai_profile_service,
        channel_setting_service=channel_setting_service,
        prompt_template_service=prompt_template_service,
    )


@pytest.mark.anyio
async def test_loads_full_config_for_tenant_business_channel_template_key(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
    platform_template: PromptTemplate,
    full_tenant_profiles: tuple[
        TenantBusinessProfile,
        TenantAiProfile,
        TenantChannelSetting,
    ],
):
    tenant_id, business_id = tenant_scope
    business_profile, ai_profile, channel_setting = full_tenant_profiles
    session = AsyncMock()
    service = _service_with_mocks(
        template=platform_template,
        business_profile=business_profile,
        ai_profile=ai_profile,
        channel_setting=channel_setting,
    )

    bundle = await service.load_for_message(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        channel="whatsapp",
        template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
    )

    assert bundle.tenant_id == tenant_id
    assert bundle.business_id == business_id
    assert bundle.channel == "whatsapp"
    assert bundle.template_key == PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY
    assert bundle.platform_template.system_prompt == platform_template.system_prompt
    assert bundle.platform_template.id == platform_template.id
    assert bundle.business_context.present is True
    assert bundle.business_context.business_description == business_profile.business_description
    assert bundle.behavior.present is True
    assert bundle.behavior.tone == "friendly"
    assert bundle.channel_rules.present is True
    assert bundle.channel_rules.max_response_length == 500


@pytest.mark.anyio
async def test_load_queries_remain_tenant_and_business_scoped(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
    platform_template: PromptTemplate,
):
    tenant_id, business_id = tenant_scope
    session = AsyncMock()
    service = _service_with_mocks(template=platform_template)

    await service.load_for_message(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        channel="whatsapp",
        template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
    )

    service.business_profile_service.get_for_business.assert_awaited_once_with(
        session,
        tenant_id,
        business_id,
    )
    service.ai_profile_service.get_for_business.assert_awaited_once_with(
        session,
        tenant_id,
        business_id,
    )
    service.channel_setting_service.get_for_channel.assert_awaited_once_with(
        session,
        tenant_id,
        business_id,
        "whatsapp",
    )
    service.prompt_template_service.get_by_template_key.assert_awaited_once_with(
        session,
        PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
    )


@pytest.mark.anyio
async def test_missing_optional_tenant_configs_return_safe_dto_values(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
    platform_template: PromptTemplate,
):
    tenant_id, business_id = tenant_scope
    session = AsyncMock()
    service = _service_with_mocks(template=platform_template)

    bundle = await service.load_for_message(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        channel="whatsapp",
        template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
    )

    assert bundle.business_context == TenantBusinessContextConfig.missing()
    assert bundle.behavior == TenantBehaviorConfig.missing()
    assert bundle.channel_rules.present is False
    assert bundle.channel_rules.channel == "whatsapp"
    assert bundle.channel_rules.allow_emojis is False
    assert bundle.channel_rules.allow_links is False
    assert bundle.platform_template.system_prompt == platform_template.system_prompt


@pytest.mark.anyio
async def test_missing_prompt_template_fails_clearly(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    tenant_id, business_id = tenant_scope
    session = AsyncMock()
    service = _service_with_mocks(template=None)

    with pytest.raises(PromptTemplateNotFoundError) as exc_info:
        await service.load_for_message(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            channel="whatsapp",
            template_key="missing_template",
        )

    assert exc_info.value.template_key == "missing_template"


@pytest.mark.anyio
async def test_tenant_config_cannot_replace_platform_system_prompt(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
    platform_template: PromptTemplate,
):
    tenant_id, business_id = tenant_scope
    override_attempt = "Tenant override of core system prompt."
    ai_profile = TenantAiProfile(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        metadata_={
            "system_prompt": override_attempt,
            "core_system_prompt": override_attempt,
            "tone": "casual",
        },
    )
    session = AsyncMock()
    service = _service_with_mocks(
        template=platform_template,
        ai_profile=ai_profile,
    )

    bundle = await service.load_for_message(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        channel="whatsapp",
        template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
    )

    assert bundle.platform_template.system_prompt == platform_template.system_prompt
    assert bundle.platform_template.system_prompt != override_attempt
    assert not hasattr(bundle.behavior, "system_prompt")
    assert bundle.behavior.metadata == {"tone": "casual"}
    for key in FORBIDDEN_TENANT_PROMPT_OVERRIDE_KEYS:
        assert key not in (bundle.behavior.metadata or {})


@pytest.mark.anyio
async def test_mis_scoped_business_profile_raises_tenant_context_error(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
    platform_template: PromptTemplate,
):
    tenant_id, business_id = tenant_scope
    mis_scoped = TenantBusinessProfile(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        business_description="Wrong scope",
    )
    session = AsyncMock()
    service = _service_with_mocks(
        template=platform_template,
        business_profile=mis_scoped,
    )

    with pytest.raises(TenantContextError, match="tenant business profile"):
        await service.load_for_message(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            channel="whatsapp",
            template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
        )


@pytest.mark.anyio
async def test_mis_scoped_ai_profile_raises_tenant_context_error(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
    platform_template: PromptTemplate,
):
    tenant_id, business_id = tenant_scope
    mis_scoped = TenantAiProfile(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        business_id=business_id,
        tone="friendly",
    )
    session = AsyncMock()
    service = _service_with_mocks(
        template=platform_template,
        ai_profile=mis_scoped,
    )

    with pytest.raises(TenantContextError, match="tenant AI profile"):
        await service.load_for_message(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            channel="whatsapp",
            template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
        )


@pytest.mark.anyio
async def test_mis_scoped_channel_setting_raises_tenant_context_error(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
    platform_template: PromptTemplate,
):
    tenant_id, business_id = tenant_scope
    mis_scoped = TenantChannelSetting(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=uuid.uuid4(),
        channel="whatsapp",
    )
    session = AsyncMock()
    service = _service_with_mocks(
        template=platform_template,
        channel_setting=mis_scoped,
    )

    with pytest.raises(TenantContextError, match="tenant channel setting"):
        await service.load_for_message(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            channel="whatsapp",
            template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
        )


@pytest.mark.anyio
async def test_channel_setting_channel_mismatch_raises_tenant_context_error(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
    platform_template: PromptTemplate,
):
    tenant_id, business_id = tenant_scope
    channel_setting = TenantChannelSetting(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        channel="telegram",
    )
    session = AsyncMock()
    service = _service_with_mocks(
        template=platform_template,
        channel_setting=channel_setting,
    )

    with pytest.raises(
        TenantContextError,
        match="channel does not match requested channel",
    ):
        await service.load_for_message(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            channel="whatsapp",
            template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
        )


@pytest.mark.anyio
async def test_metadata_scrub_applies_to_business_context_and_channel_rules(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
    platform_template: PromptTemplate,
):
    tenant_id, business_id = tenant_scope
    override = "Tenant must not override platform prompt."
    business_profile = TenantBusinessProfile(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        business_description="Barbershop",
        metadata_={
            "system_prompt": override,
            "region_note": "Zurich",
        },
    )
    channel_setting = TenantChannelSetting(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        channel="whatsapp",
        metadata_={
            "core_system_prompt": override,
            "max_links": 1,
        },
    )
    session = AsyncMock()
    service = _service_with_mocks(
        template=platform_template,
        business_profile=business_profile,
        channel_setting=channel_setting,
    )

    bundle = await service.load_for_message(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        channel="whatsapp",
        template_key=PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY,
    )

    assert bundle.business_context.metadata == {"region_note": "Zurich"}
    assert bundle.channel_rules.metadata == {"max_links": 1}
    for key in FORBIDDEN_TENANT_PROMPT_OVERRIDE_KEYS:
        assert key not in (bundle.business_context.metadata or {})
        assert key not in (bundle.channel_rules.metadata or {})


@pytest.mark.anyio
async def test_tenant_behavior_dto_has_no_system_prompt_field():
    assert "system_prompt" not in TenantBehaviorConfig.__dataclass_fields__


def test_ai_configuration_service_module_has_no_provider_imports():
    import app.services.ai_configuration_service as module

    source_path = module.__file__
    assert source_path is not None
    source = open(source_path, encoding="utf-8").read().lower()
    for forbidden in ("openai", "httpx", "aiohttp", "anthropic"):
        assert forbidden not in source
