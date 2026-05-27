"""Load tenant/business AI configuration for prompt building (T11.4)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import PromptTemplateNotFoundError, TenantContextError
from app.models.prompt_template import PromptTemplate
from app.models.tenant_ai_profile import TenantAiProfile
from app.models.tenant_business_profile import TenantBusinessProfile
from app.models.tenant_channel_setting import TenantChannelSetting
from app.schemas.ai_configuration import (
    AiConfigurationBundle,
    PlatformPromptTemplateConfig,
    TenantBehaviorConfig,
    TenantBusinessContextConfig,
    TenantChannelRulesConfig,
    scrub_tenant_metadata,
)
from app.services.prompt_template_service import PromptTemplateService
from app.services.tenant_ai_profile_service import TenantAiProfileService
from app.services.tenant_business_profile_service import TenantBusinessProfileService
from app.services.tenant_channel_setting_service import TenantChannelSettingService


class AiConfigurationService:
    def __init__(
        self,
        business_profile_service: TenantBusinessProfileService | None = None,
        ai_profile_service: TenantAiProfileService | None = None,
        channel_setting_service: TenantChannelSettingService | None = None,
        prompt_template_service: PromptTemplateService | None = None,
    ) -> None:
        self.business_profile_service = (
            business_profile_service or TenantBusinessProfileService()
        )
        self.ai_profile_service = ai_profile_service or TenantAiProfileService()
        self.channel_setting_service = (
            channel_setting_service or TenantChannelSettingService()
        )
        self.prompt_template_service = (
            prompt_template_service or PromptTemplateService()
        )

    async def load_for_message(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
        template_key: str,
    ) -> AiConfigurationBundle:
        platform_template = await self._load_platform_template(session, template_key)

        business_profile = await self.business_profile_service.get_for_business(
            session,
            tenant_id,
            business_id,
        )
        ai_profile = await self.ai_profile_service.get_for_business(
            session,
            tenant_id,
            business_id,
        )
        channel_setting = await self.channel_setting_service.get_for_channel(
            session,
            tenant_id,
            business_id,
            channel,
        )

        if business_profile is not None:
            _assert_row_scope(
                business_profile,
                tenant_id=tenant_id,
                business_id=business_id,
                label="tenant business profile",
            )
        if ai_profile is not None:
            _assert_row_scope(
                ai_profile,
                tenant_id=tenant_id,
                business_id=business_id,
                label="tenant AI profile",
            )
        if channel_setting is not None:
            _assert_row_scope(
                channel_setting,
                tenant_id=tenant_id,
                business_id=business_id,
                label="tenant channel setting",
            )
            if channel_setting.channel != channel:
                raise TenantContextError(
                    "Tenant channel setting channel does not match requested channel"
                )

        return AiConfigurationBundle(
            tenant_id=tenant_id,
            business_id=business_id,
            channel=channel,
            template_key=template_key,
            platform_template=platform_template,
            business_context=_map_business_profile(business_profile),
            behavior=_map_ai_profile(ai_profile),
            channel_rules=_map_channel_setting(channel_setting, channel),
        )

    async def _load_platform_template(
        self,
        session: AsyncSession,
        template_key: str,
    ) -> PlatformPromptTemplateConfig:
        template = await self.prompt_template_service.get_by_template_key(
            session,
            template_key,
        )
        if template is None:
            raise PromptTemplateNotFoundError(template_key)
        return _map_platform_template(template)


def _assert_row_scope(
    row: TenantBusinessProfile | TenantAiProfile | TenantChannelSetting,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    label: str,
) -> None:
    if row.tenant_id != tenant_id or row.business_id != business_id:
        raise TenantContextError(
            f"{label} is not scoped to tenant_id={tenant_id} and business_id={business_id}"
        )


def _map_platform_template(template: PromptTemplate) -> PlatformPromptTemplateConfig:
    return PlatformPromptTemplateConfig(
        id=template.id,
        template_key=template.template_key,
        template_name=template.template_name,
        version=template.version,
        system_prompt=template.system_prompt,
    )


def _map_business_profile(
    profile: TenantBusinessProfile | None,
) -> TenantBusinessContextConfig:
    if profile is None:
        return TenantBusinessContextConfig.missing()

    return TenantBusinessContextConfig(
        present=True,
        business_description=profile.business_description,
        services=profile.services,
        pricing=profile.pricing,
        working_hours=profile.working_hours,
        target_audience=profile.target_audience,
        business_limitations=profile.business_limitations,
        city=profile.city,
        region=profile.region,
        country=profile.country,
        metadata=scrub_tenant_metadata(profile.metadata_),
    )


def _map_ai_profile(profile: TenantAiProfile | None) -> TenantBehaviorConfig:
    if profile is None:
        return TenantBehaviorConfig.missing()

    return TenantBehaviorConfig(
        present=True,
        profile_name=profile.profile_name,
        tone=profile.tone,
        response_style=profile.response_style,
        language=profile.language,
        ask_for_name=profile.ask_for_name,
        ask_for_phone=profile.ask_for_phone,
        ask_for_email=profile.ask_for_email,
        handoff_enabled=profile.handoff_enabled,
        handoff_keywords=profile.handoff_keywords,
        forbidden_promises=profile.forbidden_promises,
        fallback_response=profile.fallback_response,
        metadata=scrub_tenant_metadata(profile.metadata_),
    )


def _map_channel_setting(
    setting: TenantChannelSetting | None,
    channel: str,
) -> TenantChannelRulesConfig:
    if setting is None:
        return TenantChannelRulesConfig.missing(channel)

    return TenantChannelRulesConfig(
        present=True,
        channel=setting.channel,
        response_style=setting.response_style,
        max_response_length=setting.max_response_length,
        allow_emojis=bool(setting.allow_emojis),
        allow_links=bool(setting.allow_links),
        metadata=scrub_tenant_metadata(setting.metadata_),
    )
