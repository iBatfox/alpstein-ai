"""Typed configuration DTOs for AI prompt building (T11.4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

# Tenant metadata must not inject platform-controlled prompt layers.
FORBIDDEN_TENANT_PROMPT_OVERRIDE_KEYS: frozenset[str] = frozenset(
    {
        "system_prompt",
        "core_system_prompt",
        "platform_prompt",
        "platform_safety_rules",
        "safety_rules",
        "prompt_template",
    }
)


def scrub_tenant_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if metadata is None:
        return None
    scrubbed = {
        key: value
        for key, value in metadata.items()
        if key not in FORBIDDEN_TENANT_PROMPT_OVERRIDE_KEYS
    }
    return scrubbed or None


@dataclass(frozen=True)
class PlatformPromptTemplateConfig:
    """Platform-controlled template; tenants cannot edit system_prompt."""

    id: uuid.UUID
    template_key: str
    template_name: str | None
    version: str | None
    system_prompt: str


@dataclass(frozen=True)
class TenantBusinessContextConfig:
    """Tenant business facts for prompt context (style/facts only)."""

    present: bool
    business_description: str | None = None
    services: dict[str, Any] | None = None
    pricing: dict[str, Any] | None = None
    working_hours: dict[str, Any] | None = None
    target_audience: str | None = None
    business_limitations: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def missing(cls) -> TenantBusinessContextConfig:
        return cls(present=False)


@dataclass(frozen=True)
class TenantBehaviorConfig:
    """Tenant AI behavior/style; must not include platform system prompt."""

    present: bool
    profile_name: str | None = None
    tone: str | None = None
    response_style: str | None = None
    language: str | None = None
    ask_for_name: bool | None = None
    ask_for_phone: bool | None = None
    ask_for_email: bool | None = None
    handoff_enabled: bool | None = None
    handoff_keywords: dict[str, Any] | list[Any] | None = None
    forbidden_promises: dict[str, Any] | list[Any] | None = None
    fallback_response: str | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def missing(cls) -> TenantBehaviorConfig:
        return cls(present=False)


@dataclass(frozen=True)
class TenantChannelRulesConfig:
    """Per-channel style rules; not messenger transport wiring."""

    present: bool
    channel: str
    response_style: str | None = None
    max_response_length: int | None = None
    allow_emojis: bool = False
    allow_links: bool = False
    metadata: dict[str, Any] | None = None

    @classmethod
    def missing(cls, channel: str) -> TenantChannelRulesConfig:
        return cls(present=False, channel=channel)


@dataclass(frozen=True)
class AiConfigurationBundle:
    """Resolved AI configuration for one inbound message turn."""

    tenant_id: uuid.UUID
    business_id: uuid.UUID
    channel: str
    template_key: str
    platform_template: PlatformPromptTemplateConfig
    business_context: TenantBusinessContextConfig
    behavior: TenantBehaviorConfig
    channel_rules: TenantChannelRulesConfig
