import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.elements import BinaryExpression

from app.models.prompt_template import PromptTemplate
from app.models.tenant_ai_profile import TenantAiProfile
from app.models.tenant_business_profile import TenantBusinessProfile
from app.models.tenant_channel_setting import TenantChannelSetting
from app.models.tenant_knowledge_source import TenantKnowledgeSource
from app.services.prompt_template_service import PromptTemplateService
from app.services.tenant_ai_profile_service import TenantAiProfileService
from app.services.tenant_business_profile_service import TenantBusinessProfileService
from app.services.tenant_channel_setting_service import TenantChannelSettingService
from app.services.tenant_knowledge_source_service import TenantKnowledgeSourceService


def _select_filters(statement) -> dict[str, object]:
    criteria: dict[str, object] = {}
    whereclause = statement.whereclause
    if whereclause is None:
        return criteria

    clauses = getattr(whereclause, "clauses", [whereclause])
    for clause in clauses:
        if isinstance(clause, BinaryExpression) and hasattr(clause.left, "key"):
            right = clause.right
            if hasattr(right, "value"):
                criteria[clause.left.key] = right.value
            elif isinstance(right, bool):
                criteria[clause.left.key] = right
            else:
                criteria[clause.left.key] = True
    return criteria


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_result(values: list):
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


@pytest.fixture
def tenant_scope() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("service_cls", "method_name", "extra_args"),
    [
        (TenantBusinessProfileService, "get_for_business", ()),
        (TenantAiProfileService, "get_for_business", ()),
    ],
)
async def test_tenant_scoped_profile_services_filter_by_tenant_and_business(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
    service_cls: type,
    method_name: str,
    extra_args: tuple,
):
    tenant_id, business_id = tenant_scope
    session = AsyncMock()
    session.execute.return_value = _scalar_result(None)
    service = service_cls()

    await getattr(service, method_name)(session, tenant_id, business_id, *extra_args)

    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["tenant_id"] == tenant_id
    assert filters["business_id"] == business_id


@pytest.mark.anyio
async def test_tenant_business_profile_returns_none_when_missing(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    tenant_id, business_id = tenant_scope
    session = AsyncMock()
    session.execute.return_value = _scalar_result(None)
    service = TenantBusinessProfileService()

    profile = await service.get_for_business(session, tenant_id, business_id)

    assert profile is None


@pytest.mark.anyio
async def test_tenant_channel_setting_filters_by_tenant_business_and_channel(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    tenant_id, business_id = tenant_scope
    setting = TenantChannelSetting(
        tenant_id=tenant_id,
        business_id=business_id,
        channel="whatsapp",
    )
    session = AsyncMock()
    session.execute.return_value = _scalar_result(setting)
    service = TenantChannelSettingService()

    result = await service.get_for_channel(session, tenant_id, business_id, "whatsapp")

    assert result is setting
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters == {
        "tenant_id": tenant_id,
        "business_id": business_id,
        "channel": "whatsapp",
    }


@pytest.mark.anyio
async def test_tenant_knowledge_source_lists_only_active_for_tenant(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    tenant_id, business_id = tenant_scope
    active = TenantKnowledgeSource(
        tenant_id=tenant_id,
        business_id=business_id,
        source_type="faq",
        content="Active content",
        is_active=True,
    )
    session = AsyncMock()
    session.execute.return_value = _scalars_result([active])
    service = TenantKnowledgeSourceService()

    sources = await service.list_active_for_business(session, tenant_id, business_id)

    assert sources == [active]
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["tenant_id"] == tenant_id
    assert filters["business_id"] == business_id
    assert filters["is_active"] is True


@pytest.mark.anyio
async def test_tenant_knowledge_source_excludes_inactive_via_query_filter(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    tenant_id, business_id = tenant_scope
    session = AsyncMock()
    session.execute.return_value = _scalars_result([])

    await TenantKnowledgeSourceService().list_active_for_business(
        session,
        tenant_id,
        business_id,
    )

    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["is_active"] is True
    assert "tenant_id" in filters
    assert "business_id" in filters


@pytest.mark.anyio
async def test_prompt_template_lookup_by_template_key():
    template = PromptTemplate(
        template_key="incoming_message",
        system_prompt="You are a helpful assistant.",
    )
    session = AsyncMock()
    session.execute.return_value = _scalar_result(template)
    service = PromptTemplateService()

    result = await service.get_by_template_key(session, "incoming_message")

    assert result is template
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["template_key"] == "incoming_message"
    assert filters["is_active"] is True
    assert "tenant_id" not in filters
    assert "business_id" not in filters


@pytest.mark.anyio
async def test_prompt_template_returns_none_when_missing():
    session = AsyncMock()
    session.execute.return_value = _scalar_result(None)
    service = PromptTemplateService()

    result = await service.get_by_template_key(session, "missing_template")

    assert result is None


@pytest.mark.anyio
async def test_tenant_scoped_services_do_not_query_without_business_scope(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    tenant_id, business_id = tenant_scope
    session = AsyncMock()
    session.execute.return_value = _scalars_result([])

    await TenantKnowledgeSourceService().list_active_for_business(
        session,
        tenant_id,
        business_id,
    )

    statement = session.execute.await_args.args[0]
    filters = _select_filters(statement)
    assert "tenant_id" in filters
    assert "business_id" in filters
