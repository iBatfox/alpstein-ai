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
CONVERSATION_STYLE_GUIDE_PATH = (
    ORANGE_PARK_DOCS_ROOT
    / "07_conversation_examples"
    / "orange_park_conversation_style_guide.md"
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
        sales_materials=docs["sales_materials"],
        ai_policies=docs["ai_policies"],
        conversation_style=docs["conversation_style"],
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
    await _ensure_knowledge_source(
        session,
        tenant=tenant,
        business=business,
        source_type="conversation_style",
        title="Orange Park Conversation Style Guide",
        document=_conversation_style_runtime_document(docs["conversation_style"]),
        tags=[
            "conversation_style",
            "ai_behavior",
            "qualification",
            "manager_handoff",
            "orange_park",
            "telegram_mvp",
            "not_factual_knowledge",
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
        "conversation_style": CONVERSATION_STYLE_GUIDE_PATH,
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
            "Manager confirmation is required for unstable data. Reply quality rule: "
            "do not repeat address/location after it was already answered in the current "
            "conversation; when the customer gives budget, area, payment, phone, or "
            "handoff criteria, answer only those criteria in 1-3 short Telegram sentences. "
            "Do not say the request was passed or thank for a phone number before the "
            "customer actually provides a phone number. If customer says they are "
            "waiting for the manager call, reply only: Дякую. Запит передано менеджеру. "
            "Очікуйте дзвінок. If customer agrees to handoff with short intent like "
            "давай, з'єднуй, так, ок, or добре, ask only for phone. If customer asks "
            "for phone/contact details and no official Orange Park contact is present "
            "in the current business context, ask the customer to leave their phone; "
            "do not invent contacts. Never repeat the same refusal or manager-confirmation "
            "loop twice. Orange Park Telegram stage 1 collects structured contact data "
            "before manager handoff: first_name, last_name, phone, Telegram id or username "
            "when available, and interest summary. If phone is already provided, ask only "
            "for missing first and last name. Do not create or mention external CRM leads."
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
    conversation_style: SourceDocument,
    actions: list[str],
) -> TenantAiProfile:
    profile = await _get_ai_profile(session, tenant.id, business.id)
    values = {
        "profile_name": "Orange Park Telegram MVP",
        "tone": "professional, consultative, friendly",
        "response_style": (
            "1-3 short; no repeat address; criteria only; ask phone; no loops; phone close"
        ),
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
            "перегляд",
            "відеоогляд",
            "видеообзор",
            "бронь",
            "бронювання",
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
            "payment instructions",
            "bank or card details",
            "tax, notary, registration, or service-fee amounts",
            "repeating address or location after it was already answered",
            "restating location when customer gives budget, area, payment, or handoff criteria",
            "verbose manager handoff wording",
            "open-ended closing after phone is collected",
            "saying request was passed before phone number is collected",
            "thanking for a phone number before the customer provides one",
            "open-ended extra sentence when customer is waiting for manager call",
            "long explanation after short handoff intent like давай or з'єднуй",
            "repeating the same manager-confirmation or refusal block twice",
            "inventing Orange Park phone, manager contact, or contact details",
            "giving manager phone when official contact is absent from business context",
            "English reply after Ukrainian or Russian phone number turn",
            "saying manager request was passed before first name, last name, and phone are collected",
            "external CRM lead creation or external CRM mention in Orange Park Telegram stage 1",
        ],
        "fallback_response": (
            "Дякуємо за звернення. Передаю запит менеджеру Orange Park, "
            "щоб він уточнив актуальні деталі. Очікуйте дзвінок."
        ),
        "metadata_": _metadata_for_documents(
            sales_materials,
            ai_policies,
            conversation_style,
            category="tenant_ai_profile",
            telegram_only_mvp=True,
            lead_creation_enabled=False,
            conversation_style_source="included_as_behavior_guidance",
            behavior_rules=[
                "Ukrainian /start and first greeting by default.",
                "After customer message, mirror Ukrainian or Russian.",
                "Never output English unless customer writes English.",
                "Never mix languages or use hybrid words.",
                "Answer the immediate question first, then ask one useful qualification question.",
                "Keep Telegram replies concise: 1-3 short sentences.",
                "Use conversation history to avoid repeating facts.",
                "If address or location was already answered, do not repeat it when customer gives budget, area, payment, or handoff criteria.",
                "If customer gives new buying criteria, respond only to those criteria.",
                "Do not say request was passed and do not thank for phone before customer provides a phone number.",
                "If customer says they are waiting for manager call, reply only: Дякую. Запит передано менеджеру. Очікуйте дзвінок.",
                "Do not overuse manager-confirmation wording.",
                "After phone is collected, use concise closing: Дякую. Запит передано менеджеру. Очікуйте дзвінок.",
                "Short handoff intent such as давай, з'єднуй, так, ок, or добре means: ask only for phone if phone is not collected.",
                "Contact requests such as номер телефону, дай контакти, дай дані, номер, or телефон менеджера mean: if no official contact exists in current business context, reply exactly: Залиште, будь ласка, ваш номер телефону — менеджер зв’яжеться з вами напряму.",
                "Never invent Orange Park phone numbers or manager contacts.",
                "Never repeat the same refusal or manager-confirmation loop twice.",
                "Orange Park Telegram stage 1 contact form in Russian: Пожалуйста, оставьте данные в таком формате:\n\nИмя:\nФамилия:\nТелефон:",
                "Orange Park Telegram stage 1 contact form in Ukrainian: Будь ласка, залиште дані у такому форматі:\n\nІм'я:\nПрізвище:\nТелефон:",
                "If phone is already provided in Russian context, reply: Спасибо, номер получил. Напишите, пожалуйста, имя и фамилию.",
                "If phone is already provided in Ukrainian context, reply: Дякую, номер отримав. Напишіть, будь ласка, ім'я та прізвище.",
                "Minimum Orange Park stage 1 lead fields: first_name, last_name, phone, telegram_id or telegram_username when available, and interest summary.",
                "Do not say the manager request was passed until first name, last name, and phone are collected.",
                "Do not create or mention external CRM leads in Orange Park Telegram stage 1.",
            ],
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


def _conversation_style_runtime_document(document: SourceDocument) -> SourceDocument:
    runtime_summary = """# Orange Park Conversation Style Runtime Summary

Use this as behavior guidance only, not as stable factual knowledge.

- Telegram /start and the first greeting must be Ukrainian by default.
- Use this /start greeting:
"Добрий день! 👋

Я AI-асистент ЖК Orange Park.

Можу допомогти з інформацією про комплекс, квартири, комерційні приміщення та умови придбання, а також передати ваш запит менеджеру.

Що вас цікавить?
🏡 Квартира
🏢 Комерційне приміщення
💳 Умови покупки / розтермінування"
- After the customer writes, mirror the customer's language: Ukrainian or Russian.
- Never output English unless the customer explicitly writes in English.
- Never mix languages in the same sentence and never use Ukrainian-English or Russian-English hybrid words.
- Keep Telegram replies warm, practical, concise, and consultative.
- Keep most Telegram replies to 1-3 short sentences.
- Answer the immediate question first, then ask one useful qualification question.
- Use conversation history to avoid repeating facts already provided in the current conversation.
- Do not repeat location, apartment types, payment options, or other facts unless the customer asks again.
- If address or location was already answered in this conversation, do not repeat it when the customer later gives budget, area, payment, or handoff criteria.
- If the customer gives new buying criteria, respond only to those criteria instead of restating old facts.
- If the customer agrees to handoff but has not sent a phone number, ask for the phone number; do not say the request was passed yet.
- Treat short handoff intent such as "давай", "з'єднуй", "так", "ок", "добре", "хочу консультацію", or "передайте менеджеру" as agreement to handoff. If no phone was collected, reply only: "Добре. Напишіть, будь ласка, номер телефону — менеджер зв’яжеться з вами."
- Treat contact requests such as "номер", "номер телефону", "дай номер", "дай дані", "дай контакти", "контакти", "телефон менеджера", or "як зв'язатися" as a request for official contact details. If no official Orange Park phone/contact is present in the current business context, reply only: "Залиште, будь ласка, ваш номер телефону — менеджер зв’яжеться з вами напряму."
- For Orange Park Telegram stage 1, collect a structured contact form before saying a request was passed to the manager.
- Russian contact form: "Пожалуйста, оставьте данные в таком формате:\n\nИмя:\nФамилия:\nТелефон:"
- Ukrainian contact form: "Будь ласка, залиште дані у такому форматі:\n\nІм'я:\nПрізвище:\nТелефон:"
- If the customer already sent a phone number in Russian context, reply: "Спасибо, номер получил. Напишите, пожалуйста, имя и фамилию."
- If the customer already sent a phone number in Ukrainian context, reply: "Дякую, номер отримав. Напишіть, будь ласка, ім'я та прізвище."
- Minimum stage-1 lead data: first name, last name, phone, Telegram id or username when available, and interest summary from the conversation.
- Do not thank the customer for a phone number until the customer actually provides one.
- If customer says they are waiting for manager call, reply only: "Дякую. Запит передано менеджеру. Очікуйте дзвінок."
- Never invent Orange Park phone numbers, manager contacts, contact links, or sales-office contacts.
- Never repeat the same refusal or manager-confirmation block twice; after one such message, ask for phone, ask one missing qualifier, or close after phone.
- Do not create or mention external CRM leads in stage 1.
- For apartment interest, ask about room count, purpose, budget, payment route, and viewing/video preference.
- For availability questions, do not invent exact options. Offer manager confirmation and ask what room count or format the customer wants.
- For price, discount, installment, єОселя, credit, payment, legal, documents, readiness, or reservation questions, give safe general context first, then explain that a manager will confirm current details.
- Offer a concrete next step: manager confirmation, viewing, video viewing, plan/layout review, or financing consultation.
- Do not overuse phrases like "потрібно підтвердження від менеджера" or "можу організувати консультацію".
- After collecting a phone number, acknowledge it, summarize the request briefly, and close naturally in one short reply.
- Do not mention CRM, lead creation, or internal workflow details.
- Use soft urgency only as: current terms can change, so manager confirmation is recommended.
- Never copy transcript prices, discounts, availability counts, bank/card/account details, payment instructions, legal/tax amounts, booking promises, signing dates, key handover timing, or private client details.

Safe examples:
- "ЖК Orange Park розташований у Крюківщині, вул. Одеська, 23, приблизно 5 км від Києва. У матеріалах комплексу є 1-кімнатні квартири, але актуальну наявність і вартість підтверджує менеджер. Яку площу або бюджет ви розглядаєте?"
- "Зрозуміло: шукаєте 1-кімнатну 40-45 м2 до 1 600 000 грн, бажано у розтермінування. Актуальні варіанти й умови треба перевірити у менеджера. Напишіть, будь ласка, номер телефону - передам запит."
- "Добре. Напишіть, будь ласка, номер телефону — менеджер зв’яжеться з вами."
- "Залиште, будь ласка, ваш номер телефону — менеджер зв’яжеться з вами напряму."
- "Пожалуйста, оставьте данные в таком формате:\n\nИмя:\nФамилия:\nТелефон:"
- "Будь ласка, залиште дані у такому форматі:\n\nІм'я:\nПрізвище:\nТелефон:"
- "Спасибо, номер получил. Напишите, пожалуйста, имя и фамилию."
- "Дякую, номер отримав. Напишіть, будь ласка, ім'я та прізвище."
- "Дякую. Запит передано менеджеру: 1-кімнатна 40-45 м2 до 1 600 000 грн, цікавить розтермінування. Очікуйте дзвінок."
- "Дякую. Запит передано менеджеру. Очікуйте дзвінок."
"""
    content = f"{runtime_summary.strip()}\n\n---\n\n{document.content}"
    return SourceDocument(
        path=document.path,
        relative_path=document.relative_path,
        content=content,
        sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
    )


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
    return (
        "Orange Park / ЖК Orange Park is a Comfort+ residential complex in "
        "Kriukivshchyna at Odeska/Odesskaya 23. The Telegram MVP may use stable "
        "project facts from the prepared source document, but prices, discounts, "
        "availability, financing, booking, and legal details require manager "
        "confirmation.\n\n"
        "Response quality rules for this business context:\n"
        "- If address or location was already answered in the current conversation, "
        "do not repeat it unless the customer asks about location again.\n"
        "- When the customer gives budget, area, payment, phone number, or handoff "
        "criteria, respond only to those criteria.\n"
        "- If the customer agrees to handoff but has not sent a phone number, ask for "
        "the phone number; do not say the request was passed yet.\n"
        "- Short handoff intent such as \"давай\", \"з'єднуй\", \"так\", \"ок\", "
        "or \"добре\" means: if no phone was collected, reply only: "
        "\"Добре. Напишіть, будь ласка, номер телефону — менеджер зв’яжеться з вами.\"\n"
        "- Contact requests such as \"номер телефону\", \"дай контакти\", "
        "\"дай дані\", \"номер\", or \"телефон менеджера\" mean: if no official "
        "Orange Park phone/contact is present in the current business context, "
        "reply only: \"Залиште, будь ласка, ваш номер телефону — менеджер зв’яжеться "
        "з вами напряму.\"\n"
        "- Orange Park Telegram stage 1 contact collection requires first_name, "
        "last_name, phone, Telegram id or username when available, and interest "
        "summary from the conversation before saying the request was passed. "
        "If phone is already provided, ask only for missing first and last name.\n"
        "- Russian contact form: \"Пожалуйста, оставьте данные в таком формате:\\n\\n"
        "Имя:\\nФамилия:\\nТелефон:\"\n"
        "- Ukrainian contact form: \"Будь ласка, залиште дані у такому форматі:\\n\\n"
        "Ім'я:\\nПрізвище:\\nТелефон:\"\n"
        "- If the customer already sent a phone number in Russian context, reply: "
        "\"Спасибо, номер получил. Напишите, пожалуйста, имя и фамилию.\"\n"
        "- If the customer already sent a phone number in Ukrainian context, reply: "
        "\"Дякую, номер отримав. Напишіть, будь ласка, ім'я та прізвище.\"\n"
        "- Never invent Orange Park phone numbers, manager contacts, contact links, "
        "or sales-office contacts.\n"
        "- Never repeat the same refusal or manager-confirmation block twice; after "
        "one such message, ask for phone, ask one missing qualifier, or close after phone.\n"
        "- Do not create or mention external CRM leads in Orange Park Telegram stage 1.\n"
        "- If customer says they are waiting for manager call, reply only: "
        "\"Дякую. Запит передано менеджеру. Очікуйте дзвінок.\"\n"
        "- Keep Telegram replies to 1-3 short sentences.\n"
        "- After phone is collected, close with concise wording like: "
        "\"Дякую. Запит передано менеджеру. Очікуйте дзвінок.\"\n\n"
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
