"""Seed Orange Park Telegram-only MVP configuration."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.flow import FLOW_STATUS_ACTIVE, Flow
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
ORANGE_PARK_LANGUAGE = "ru"
ORANGE_PARK_TIMEZONE = "Europe/Kyiv"
ORANGE_PARK_CHANNEL = "telegram"
ORANGE_PARK_FLOW_KEY = "orange_park_telegram_mvp"
ORANGE_PARK_FLOW_NAME = "Orange Park Telegram MVP"

REPO_ROOT = Path(__file__).resolve().parents[3]
ORANGE_PARK_DOCS_ROOT = REPO_ROOT / "docs" / "businesses" / "orange-park"

FACTS_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "01_business_profile_facts"
    / "orange_park_facts.md"
)
SALES_MATERIALS_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "02_ai_behavior_and_sales_materials"
    / "orange_park_sales_materials.md"
)
AI_POLICIES_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "05_policies_and_rules"
    / "orange_park_ai_policies.md"
)
FAQ_PATH = ORANGE_PARK_DOCS_ROOT / "03_faq" / "orange_park_faq.md"
PRICES_AVAILABILITY_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "04_prices_and_availability"
    / "orange_park_prices_and_availability.md"
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
    await _ensure_default_flow(session, tenant=tenant, business=business, actions=actions)
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
        sales_materials=docs["sales_materials"],
        ai_policies=docs["ai_policies"],
        actions=actions,
    )
    await _ensure_channel_setting(
        session,
        tenant=tenant,
        business=business,
        actions=actions,
    )
    await _ensure_knowledge_source(
        session,
        tenant=tenant,
        business=business,
        source_type="faq",
        title="Orange Park FAQ",
        document=docs["faq"],
        tags=["faq", "orange_park", "telegram_mvp"],
        actions=actions,
    )
    await _ensure_knowledge_source(
        session,
        tenant=tenant,
        business=business,
        source_type="pricing",
        title="Orange Park Prices And Availability - Manager Confirmed Only",
        document=docs["prices_availability"],
        tags=[
            "pricing",
            "availability",
            "requires_manager_confirmation",
            "time_sensitive",
            "orange_park",
            "telegram_mvp",
        ],
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
        "sales_materials": SALES_MATERIALS_PATH,
        "ai_policies": AI_POLICIES_PATH,
        "faq": FAQ_PATH,
        "prices_availability": PRICES_AVAILABILITY_PATH,
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
            description="Orange Park residential complex Telegram-only MVP business.",
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
        business.description = (
            "Orange Park residential complex Telegram-only MVP business."
        )
        business.language = ORANGE_PARK_LANGUAGE
        business.timezone = ORANGE_PARK_TIMEZONE
        business.storage_mode = "shared"
        business.status = "active"
        actions.append("updated business")
    await session.flush()
    return business


async def _ensure_default_flow(
    session: AsyncSession,
    *,
    tenant: Tenant,
    business: Business,
    actions: list[str],
) -> Flow:
    flow = await _get_flow_by_key(
        session,
        tenant_id=tenant.id,
        business_id=business.id,
        flow_key=ORANGE_PARK_FLOW_KEY,
    )
    values = {
        "flow_name": ORANGE_PARK_FLOW_NAME,
        "status": FLOW_STATUS_ACTIVE,
        "is_default": True,
        "metadata_": {
            "seed": "orange_park_configuration",
            "business_external_id": ORANGE_PARK_BUSINESS_EXTERNAL_ID,
            "stage": "telegram_only_mvp",
            "lead_creation_enabled": False,
        },
    }
    if flow is None:
        flow = Flow(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            business_id=business.id,
            flow_key=ORANGE_PARK_FLOW_KEY,
            **values,
        )
        session.add(flow)
        actions.append("created default flow")
    else:
        _assert_row_scope(flow, tenant_id=tenant.id, business_id=business.id)
        flow.flow_key = ORANGE_PARK_FLOW_KEY
        for field_name, value in values.items():
            setattr(flow, field_name, value)
        actions.append("updated default flow")
    await session.flush()
    return flow


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
            "policy": "Do not provide live prices or active discounts. Manager confirmation required.",
            "source": "See TenantKnowledgeSource pricing row for time-sensitive extracted claims.",
        },
        "working_hours": None,
        "target_audience": (
            "Apartment buyers, families, investors, and commercial premises buyers "
            "interested in Orange Park."
        ),
        "business_limitations": (
            "Telegram MVP only. No booking, no live pricing, no live availability, "
            "no CRM integration, no credit/єОселя/voucher approval, no legal guarantees. "
            "Manager confirmation is required for unstable data."
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
    sales_materials: SourceDocument,
    ai_policies: SourceDocument,
    actions: list[str],
) -> TenantAiProfile:
    profile = await _get_ai_profile(session, tenant.id, business.id)
    values = {
        "profile_name": "Orange Park Telegram MVP",
        "tone": "professional, consultative, friendly",
        "response_style": "concise Telegram real estate sales assistant",
        "language": ORANGE_PARK_LANGUAGE,
        "ask_for_name": True,
        "ask_for_phone": True,
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
        ],
        "forbidden_promises": [
            "exact price",
            "apartment availability",
            "reservation or booking",
            "active discount",
            "credit approval",
            "єОселя approval",
            "housing voucher approval",
            "legal guarantees",
            "live pricing",
            "live availability",
            "external CRM lead creation",
        ],
        "fallback_response": (
            "Дякуємо за звернення. Я передам запит менеджеру Orange Park, "
            "щоб він підтвердив актуальні деталі."
        ),
        "metadata_": _metadata_for_documents(
            sales_materials,
            ai_policies,
            category="tenant_ai_profile",
            telegram_only_mvp=True,
            lead_creation_enabled=False,
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
        "allow_emojis": False,
        "allow_links": False,
        "metadata_": {
            "stage": "telegram_only_mvp",
            "credential_storage": "external_runtime_only",
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


async def _get_flow_by_key(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    flow_key: str,
) -> Flow | None:
    result = await session.execute(
        select(Flow)
        .where(
            Flow.tenant_id == tenant_id,
            Flow.business_id == business_id,
            Flow.flow_key == flow_key,
        )
        .limit(1)
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
    row: Flow
    | TenantBusinessProfile
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
    return (
        "Orange Park / ЖК Orange Park is a Comfort+ residential complex in "
        "Kriukivshchyna at Odeska/Odesskaya 23. The Telegram MVP may use stable "
        "project facts from the prepared source document, but prices, discounts, "
        "availability, financing, booking, and legal details require manager "
        "confirmation.\n\n"
        f"Prepared factual source:\n{facts.content}"
    )


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
        "manager_consultation": {
            "required_for": [
                "price",
                "availability",
                "discount",
                "installment",
                "єОселя",
                "PrivatBank credit",
                "housing voucher",
                "commercial premises",
                "booking",
                "legal details",
            ]
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
        "stage": "telegram_only_mvp",
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
