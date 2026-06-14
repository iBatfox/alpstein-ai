"""Seed Orange Park Dialog Engine v3 configuration."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.tenant import Tenant
from app.models.tenant_ai_profile import TenantAiProfile
from app.models.tenant_business_profile import TenantBusinessProfile
from app.models.tenant_channel_setting import TenantChannelSetting
from app.models.tenant_knowledge_source import TenantKnowledgeSource

ORANGE_PARK_TENANT_SLUG = "orange-park"
ORANGE_PARK_TENANT_NAME = "Orange Park"
ORANGE_PARK_BUSINESS_EXTERNAL_ID = "orange-park"
ORANGE_PARK_BUSINESS_NAME = "Orange Park / ЖК Orange Park"
ORANGE_PARK_BUSINESS_TYPE = "real_estate"
ORANGE_PARK_LANGUAGE = "uk"
ORANGE_PARK_TIMEZONE = "Europe/Kyiv"
ORANGE_PARK_CHANNEL = "telegram"
ORANGE_PARK_DIALOG_ENGINE_VERSION = "orange_park_v3"

REPO_ROOT = Path(__file__).resolve().parents[3]
ORANGE_PARK_DOCS_ROOT = REPO_ROOT / "docs" / "businesses" / "orange-park"

FACTS_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "01_business_profile"
    / "orange_park_business_profile.md"
)
AI_POLICIES_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "03_sales_scenarios"
    / "orange_park_sales_scenarios.md"
)
SALES_PRESENTATION_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "02_sales_presentation"
    / "orange_park_sales_presentation.md"
)
SALES_SCENARIOS_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "03_sales_scenarios"
    / "orange_park_sales_scenarios.md"
)
PURCHASE_RULES_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "04_purchase_rules"
    / "orange_park_purchase_rules.md"
)
APARTMENT_CATALOG_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "05_apartment_catalog"
    / "orange_park_apartment_catalog.md"
)
COMMERCIAL_CATALOG_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "06_commercial_catalog"
    / "orange_park_commercial_catalog.md"
)


class OrangeParkConfigurationSeedError(Exception):
    """Raised when Orange Park seed cannot preserve tenant/business isolation."""


@dataclass(frozen=True)
class OrangeParkSeedResult:
    tenant_id: uuid.UUID
    business_id: uuid.UUID
    tenant_slug: str
    business_external_id: str
    actions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SourceDocument:
    path: Path
    relative_path: str
    content: str
    sha256: str


async def seed_orange_park_configuration(
    session: AsyncSession,
    *,
    tenant_slug: str = ORANGE_PARK_TENANT_SLUG,
    tenant_name: str = ORANGE_PARK_TENANT_NAME,
) -> OrangeParkSeedResult:
    """Create or update Orange Park Telegram-only AI configuration."""

    docs = _load_source_documents()
    actions: list[str] = []

    tenant = await _ensure_tenant(
        session,
        slug=tenant_slug,
        name=tenant_name,
        actions=actions,
    )
    business = await _ensure_business(session, tenant=tenant, actions=actions)
    await _ensure_business_profile(
        session,
        tenant=tenant,
        business=business,
        facts=docs["facts"],
        actions=actions,
    )
    await _ensure_ai_profile(
        session,
        tenant=tenant,
        business=business,
        ai_policies=docs["ai_policies"],
        actions=actions,
    )
    await _ensure_channel_setting(
        session,
        tenant=tenant,
        business=business,
        actions=actions,
    )
    source_definitions = (
        (
            "business_profile",
            "01_business_profile",
            docs["facts"],
            ["stable_facts"],
        ),
        (
            "sales_presentation",
            "02_sales_presentation",
            docs["sales_presentation"],
            ["sales"],
        ),
        (
            "sales_scenarios",
            "03_sales_scenarios",
            docs["sales_scenarios"],
            ["dialog_v3"],
        ),
        (
            "purchase_rules",
            "04_purchase_rules",
            docs["purchase_rules"],
            ["requires_manager_confirmation"],
        ),
        (
            "apartment_catalog",
            "05_apartment_catalog",
            docs["apartment_catalog"],
            ["extension_point"],
        ),
        (
            "commercial_catalog",
            "06_commercial_catalog",
            docs["commercial_catalog"],
            ["extension_point"],
        ),
    )
    for source_type, title, document, tags in source_definitions:
        await _ensure_knowledge_source(
            session,
            tenant=tenant,
            business=business,
            source_type=source_type,
            title=title,
            document=document,
            tags=[*tags, "orange_park", "orange_park_v3"],
            actions=actions,
        )
    await _deactivate_obsolete_knowledge_sources(
        session,
        tenant=tenant,
        business=business,
        active_titles={definition[1] for definition in source_definitions},
        actions=actions,
    )
    await _update_orange_park_flow_metadata(
        session,
        tenant=tenant,
        business=business,
        actions=actions,
    )

    return OrangeParkSeedResult(
        tenant_id=tenant.id,
        business_id=business.id,
        tenant_slug=tenant.slug,
        business_external_id=business.external_id,
        actions=tuple(actions),
    )


def _load_source_documents() -> dict[str, SourceDocument]:
    paths = {
        "facts": FACTS_PATH,
        "ai_policies": AI_POLICIES_PATH,
        "sales_presentation": SALES_PRESENTATION_PATH,
        "sales_scenarios": SALES_SCENARIOS_PATH,
        "purchase_rules": PURCHASE_RULES_PATH,
        "apartment_catalog": APARTMENT_CATALOG_PATH,
        "commercial_catalog": COMMERCIAL_CATALOG_PATH,
    }
    return {key: _read_source_document(path) for key, path in paths.items()}


def _read_source_document(path: Path) -> SourceDocument:
    if not path.exists():
        raise OrangeParkConfigurationSeedError(f"Required source document missing: {path}")
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise OrangeParkConfigurationSeedError(f"Required source document is empty: {path}")
    return SourceDocument(
        path=path,
        relative_path=path.relative_to(REPO_ROOT).as_posix(),
        content=content,
        sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
    )


async def _ensure_tenant(
    session: AsyncSession,
    *,
    slug: str,
    name: str,
    actions: list[str],
) -> Tenant:
    tenant = await _get_tenant_by_slug(session, slug)
    if tenant is None:
        tenant = Tenant(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            status="active",
        )
        session.add(tenant)
        actions.append("created tenant")
    else:
        tenant.name = name
        tenant.status = "active"
        actions.append("updated tenant")
    await session.flush()
    return tenant


async def _ensure_business(
    session: AsyncSession,
    *,
    tenant: Tenant,
    actions: list[str],
) -> Business:
    business = await _get_business_by_external_id(
        session,
        ORANGE_PARK_BUSINESS_EXTERNAL_ID,
    )
    if business is None:
        business = Business(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            external_id=ORANGE_PARK_BUSINESS_EXTERNAL_ID,
            name=ORANGE_PARK_BUSINESS_NAME,
            business_type=ORANGE_PARK_BUSINESS_TYPE,
            description="Orange Park residential complex with Dialog Engine v3.",
            language=ORANGE_PARK_LANGUAGE,
            timezone=ORANGE_PARK_TIMEZONE,
            storage_mode="shared",
            status="active",
        )
        session.add(business)
        actions.append("created business")
    else:
        _assert_business_belongs_to_tenant(business, tenant)
        business.name = ORANGE_PARK_BUSINESS_NAME
        business.business_type = ORANGE_PARK_BUSINESS_TYPE
        business.description = "Orange Park residential complex with Dialog Engine v3."
        business.language = ORANGE_PARK_LANGUAGE
        business.timezone = ORANGE_PARK_TIMEZONE
        business.storage_mode = "shared"
        business.status = "active"
        actions.append("updated business")
    await session.flush()
    return business


async def _ensure_business_profile(
    session: AsyncSession,
    *,
    tenant: Tenant,
    business: Business,
    facts: SourceDocument,
    actions: list[str],
) -> TenantBusinessProfile:
    profile = await _get_business_profile(session, tenant.id, business.id)
    values = {
        "business_description": _business_description(facts),
        "services": _orange_park_services(),
        "pricing": {
            "current_values_available": False,
            "source": "See TenantKnowledgeSource pricing row for time-sensitive extracted claims.",
        },
        "working_hours": None,
        "target_audience": (
            "Apartment buyers, families, investors, and commercial premises buyers "
            "interested in Orange Park."
        ),
        "business_limitations": (
            "Current inventory, exact prices, active discounts, financing terms, "
            "building readiness, sales-office contacts, and working hours are not "
            "available as stable business facts."
        ),
        "city": "Kriukivshchyna",
        "region": "Kyiv Oblast",
        "country": "Ukraine",
        "metadata_": _metadata_for_documents(
            facts,
            category="tenant_business_profile",
        ),
    }
    if profile is None:
        profile = TenantBusinessProfile(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            **values,
        )
        session.add(profile)
        actions.append("created tenant business profile")
    else:
        _assert_row_scope(profile, tenant_id=tenant.id, business_id=business.id)
        for field_name, value in values.items():
            setattr(profile, field_name, value)
        actions.append("updated tenant business profile")
    await session.flush()
    return profile


async def _ensure_ai_profile(
    session: AsyncSession,
    *,
    tenant: Tenant,
    business: Business,
    ai_policies: SourceDocument,
    actions: list[str],
) -> TenantAiProfile:
    profile = await _get_ai_profile(session, tenant.id, business.id)
    values = {
        "profile_name": "Orange Park Dialog Engine v3",
        "tone": "professional, consultative, friendly",
        "response_style": "scenario-based; concise; one question; explicit handoff",
        "language": ORANGE_PARK_LANGUAGE,
        "ask_for_name": None,
        "ask_for_phone": None,
        "ask_for_email": False,
        "handoff_enabled": True,
        "handoff_keywords": [
            "менеджер",
            "консультация",
            "консультація",
            "цена",
            "ціна",
            "наличие",
            "наявність",
            "скидка",
            "знижка",
            "єоселя",
            "кредит",
            "рассрочка",
            "розтермінування",
            "перегляд",
            "відеоогляд",
            "видеообзор",
            "бронь",
            "бронювання",
        ],
        "forbidden_promises": [
            "exact price",
            "exact apartment availability",
            "reservation or booking",
            "active discount",
            "credit approval",
            "єОселя approval",
            "housing voucher approval",
            "legal guarantees",
            "live pricing",
            "live availability",
            "payment instructions",
            "bank or card details",
            "tax, notary, registration, or service-fee amounts",
            "unconfirmed commissioning, key, or renovation dates",
        ],
        "fallback_response": (
            "Уточніть, будь ласка, що саме вас цікавить: квартира, комерційне "
            "приміщення чи умови придбання?"
        ),
        "metadata_": _metadata_for_documents(
            ai_policies,
            category="tenant_ai_profile",
            dialog_engine_version=ORANGE_PARK_DIALOG_ENGINE_VERSION,
            language=ORANGE_PARK_LANGUAGE,
            bitrix_contact_sync_enabled=True,
            behavior_instructions=ai_policies.content,
        ),
    }
    if profile is None:
        profile = TenantAiProfile(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            **values,
        )
        session.add(profile)
        actions.append("created tenant AI profile")
    else:
        _assert_row_scope(profile, tenant_id=tenant.id, business_id=business.id)
        for field_name, value in values.items():
            setattr(profile, field_name, value)
        actions.append("updated tenant AI profile")
    await session.flush()
    return profile


async def _ensure_channel_setting(
    session: AsyncSession,
    *,
    tenant: Tenant,
    business: Business,
    actions: list[str],
) -> TenantChannelSetting:
    setting = await _get_channel_setting(
        session,
        tenant.id,
        business.id,
        ORANGE_PARK_CHANNEL,
    )
    values = {
        "response_style": "concise",
        "max_response_length": 900,
        "allow_emojis": True,
        "allow_links": False,
        "metadata_": {
            "dialog_engine_version": ORANGE_PARK_DIALOG_ENGINE_VERSION,
            "language": ORANGE_PARK_LANGUAGE,
            "credential_storage": "external_runtime_only",
            "bitrix_contact_sync_enabled": True,
            "default_start_language": ORANGE_PARK_LANGUAGE,
            "start_greeting": (
                "Добрий день! 👋\n\n"
                "Я AI-асистент ЖК Orange Park.\n\n"
                "Можу допомогти з інформацією про комплекс, квартири, "
                "комерційні приміщення та умови придбання, а також передати "
                "ваш запит менеджеру.\n\n"
                "Що вас цікавить?\n"
                "🏡 Квартира\n"
                "🏢 Комерційне приміщення\n"
                "💳 Умови покупки / розтермінування"
            ),
        },
    }
    if setting is None:
        setting = TenantChannelSetting(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            channel=ORANGE_PARK_CHANNEL,
            **values,
        )
        session.add(setting)
        actions.append("created Telegram channel setting")
    else:
        _assert_row_scope(setting, tenant_id=tenant.id, business_id=business.id)
        setting.channel = ORANGE_PARK_CHANNEL
        for field_name, value in values.items():
            setattr(setting, field_name, value)
        actions.append("updated Telegram channel setting")
    await session.flush()
    return setting


async def _ensure_knowledge_source(
    session: AsyncSession,
    *,
    tenant: Tenant,
    business: Business,
    source_type: str,
    title: str,
    document: SourceDocument,
    tags: list[str],
    actions: list[str],
) -> TenantKnowledgeSource:
    source = await _get_knowledge_source(
        session,
        tenant_id=tenant.id,
        business_id=business.id,
        source_type=source_type,
        title=title,
    )
    values = {
        "content": document.content,
        "tags": tags,
        "metadata_": _metadata_for_documents(
            document,
            category="tenant_knowledge_source",
            source_type=source_type,
            requires_manager_confirmation=(
                "requires_manager_confirmation" in tags
            ),
            time_sensitive=("time_sensitive" in tags),
        ),
        "is_active": True,
    }
    if source is None:
        source = TenantKnowledgeSource(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            source_type=source_type,
            title=title,
            **values,
        )
        session.add(source)
        actions.append(f"created knowledge source {title!r}")
    else:
        _assert_row_scope(source, tenant_id=tenant.id, business_id=business.id)
        source.source_type = source_type
        source.title = title
        for field_name, value in values.items():
            setattr(source, field_name, value)
        actions.append(f"updated knowledge source {title!r}")
    await session.flush()
    return source


async def _deactivate_obsolete_knowledge_sources(
    session: AsyncSession,
    *,
    tenant: Tenant,
    business: Business,
    active_titles: set[str],
    actions: list[str],
) -> None:
    await session.execute(
        update(TenantKnowledgeSource)
        .where(
            TenantKnowledgeSource.tenant_id == tenant.id,
            TenantKnowledgeSource.business_id == business.id,
            TenantKnowledgeSource.title.not_in(active_titles),
            TenantKnowledgeSource.is_active.is_(True),
        )
        .values(is_active=False)
    )
    actions.append("deactivated obsolete Orange Park knowledge sources")


async def _update_orange_park_flow_metadata(
    session: AsyncSession,
    *,
    tenant: Tenant,
    business: Business,
    actions: list[str],
) -> None:
    await session.execute(
        text(
            """
            update flows
            set metadata = coalesce(metadata, '{}'::jsonb)
                || jsonb_build_object(
                    'dialog_engine_version', cast(:dialog_engine_version as text),
                    'language', cast(:language as text),
                    'crm',
                    coalesce(metadata->'crm', '{}'::jsonb)
                        || jsonb_build_object(
                            'bitrix',
                            coalesce(metadata->'crm'->'bitrix', '{}'::jsonb)
                                || '{"enabled": true}'::jsonb
                        )
                )
            where tenant_id = :tenant_id
              and business_id = :business_id
            """
        ),
        {
            "dialog_engine_version": ORANGE_PARK_DIALOG_ENGINE_VERSION,
            "language": ORANGE_PARK_LANGUAGE,
            "tenant_id": tenant.id,
            "business_id": business.id,
        },
    )
    actions.append("updated Orange Park flow metadata")


async def _get_tenant_by_slug(session: AsyncSession, slug: str) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.slug == slug).limit(1))
    return result.scalar_one_or_none()


async def _get_business_by_external_id(
    session: AsyncSession,
    external_id: str,
) -> Business | None:
    result = await session.execute(
        select(Business).where(Business.external_id == external_id).limit(1)
    )
    return result.scalar_one_or_none()


async def _get_business_profile(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
) -> TenantBusinessProfile | None:
    result = await session.execute(
        select(TenantBusinessProfile)
        .where(
            TenantBusinessProfile.tenant_id == tenant_id,
            TenantBusinessProfile.business_id == business_id,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_ai_profile(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
) -> TenantAiProfile | None:
    result = await session.execute(
        select(TenantAiProfile)
        .where(
            TenantAiProfile.tenant_id == tenant_id,
            TenantAiProfile.business_id == business_id,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_channel_setting(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    channel: str,
) -> TenantChannelSetting | None:
    result = await session.execute(
        select(TenantChannelSetting)
        .where(
            TenantChannelSetting.tenant_id == tenant_id,
            TenantChannelSetting.business_id == business_id,
            TenantChannelSetting.channel == channel,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_knowledge_source(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    source_type: str,
    title: str,
) -> TenantKnowledgeSource | None:
    result = await session.execute(
        select(TenantKnowledgeSource)
        .where(
            TenantKnowledgeSource.tenant_id == tenant_id,
            TenantKnowledgeSource.business_id == business_id,
            TenantKnowledgeSource.source_type == source_type,
            TenantKnowledgeSource.title == title,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


def _assert_business_belongs_to_tenant(business: Business, tenant: Tenant) -> None:
    if business.tenant_id != tenant.id:
        raise OrangeParkConfigurationSeedError(
            "Existing orange-park business belongs to tenant_id="
            f"{business.tenant_id}; expected tenant_id={tenant.id}"
        )


def _assert_row_scope(
    row: TenantBusinessProfile
    | TenantAiProfile
    | TenantChannelSetting
    | TenantKnowledgeSource,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
) -> None:
    if row.tenant_id != tenant_id or row.business_id != business_id:
        raise OrangeParkConfigurationSeedError(
            "Existing Orange Park row has wrong scope: "
            f"tenant_id={row.tenant_id}, business_id={row.business_id}; "
            f"expected tenant_id={tenant_id}, business_id={business_id}"
        )


def _business_description(facts: SourceDocument) -> str:
    return facts.content


def _orange_park_services() -> dict[str, Any]:
    return {
        "residential_apartments": {
            "types": [
                "1-room",
                "2-room",
                "3-room",
                "4-room",
                "two-level",
                "patio apartments",
            ],
            "availability_policy": "manager_confirmation_required",
        },
        "commercial_premises": {
            "available_in_source_materials": True,
            "availability_policy": "manager_confirmation_required",
        },
        "white_box_completion": {
            "included_in_source_materials": True,
            "details": [
                "floor screed",
                "plastered walls",
                "energy-efficient windows",
                "entrance doors",
                "individual heating",
                "gas boiler",
                "meters",
            ],
        },
    }


def _metadata_for_documents(
    *documents: SourceDocument,
    category: str,
    **extra: Any,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "seed": "orange_park_configuration",
        "category": category,
        "business_external_id": ORANGE_PARK_BUSINESS_EXTERNAL_ID,
        "dialog_engine_version": ORANGE_PARK_DIALOG_ENGINE_VERSION,
        "source_documents": [
            {
                "path": document.relative_path,
                "sha256": document.sha256,
            }
            for document in documents
        ],
    }
    metadata.update(extra)
    return metadata
