import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.exceptions import TenantContextError
from app.models.tenant_knowledge_source import TenantKnowledgeSource
from app.services.knowledge_retrieval_service import (
    MAX_KNOWLEDGE_SNIPPETS,
    MAX_SNIPPET_CONTENT_CHARS,
    MAX_TOTAL_SNIPPET_CONTENT_CHARS,
    KnowledgeRetrievalService,
)


@pytest.fixture
def tenant_scope() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


def _source(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
    *,
    title: str,
    content: str,
    is_active: bool = True,
    source_type: str = "faq",
    created_at: datetime | None = None,
) -> TenantKnowledgeSource:
    tenant_id, business_id = tenant_scope
    return TenantKnowledgeSource(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        source_type=source_type,
        title=title,
        content=content,
        is_active=is_active,
        created_at=created_at or datetime(2026, 5, 1, 12, 0, 0),
    )


def _service_with_sources(sources: list[TenantKnowledgeSource]) -> KnowledgeRetrievalService:
    knowledge_source_service = AsyncMock()
    knowledge_source_service.list_active_for_business = AsyncMock(return_value=sources)
    return KnowledgeRetrievalService(knowledge_source_service=knowledge_source_service)


@pytest.mark.anyio
async def test_retrieve_preserves_tenant_and_business_scope(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    tenant_id, business_id = tenant_scope
    session = AsyncMock()
    service = _service_with_sources([])

    await service.retrieve_for_message(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
    )

    service.knowledge_source_service.list_active_for_business.assert_awaited_once_with(
        session,
        tenant_id,
        business_id,
    )


@pytest.mark.anyio
async def test_inactive_knowledge_is_not_returned(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    inactive = _source(
        tenant_scope,
        title="Inactive",
        content="Should not appear",
        is_active=False,
    )
    session = AsyncMock()
    service = _service_with_sources([inactive])

    result = await service.retrieve_for_message(
        session,
        tenant_id=tenant_scope[0],
        business_id=tenant_scope[1],
    )

    assert result.snippets == ()


@pytest.mark.anyio
async def test_empty_knowledge_returns_empty_list(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    session = AsyncMock()
    service = _service_with_sources([])

    result = await service.retrieve_for_message(
        session,
        tenant_id=tenant_scope[0],
        business_id=tenant_scope[1],
    )

    assert result.snippets == ()


@pytest.mark.anyio
async def test_returns_bounded_snippets(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    many_sources = [
        _source(
            tenant_scope,
            title=f"FAQ {index}",
            content=f"Content block {index} " + ("x" * 200),
            created_at=datetime(2026, 5, 1, 12, index, 0),
        )
        for index in range(MAX_KNOWLEDGE_SNIPPETS + 3)
    ]
    session = AsyncMock()
    service = _service_with_sources(many_sources)

    result = await service.retrieve_for_message(
        session,
        tenant_id=tenant_scope[0],
        business_id=tenant_scope[1],
    )

    assert len(result.snippets) == MAX_KNOWLEDGE_SNIPPETS
    assert all(len(snippet.content) <= MAX_SNIPPET_CONTENT_CHARS for snippet in result.snippets)
    total_chars = sum(len(snippet.content) for snippet in result.snippets)
    assert total_chars <= MAX_TOTAL_SNIPPET_CONTENT_CHARS


@pytest.mark.anyio
async def test_truncates_long_snippet_content(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    long_content = "a" * (MAX_SNIPPET_CONTENT_CHARS + 50)
    source = _source(tenant_scope, title="Long", content=long_content)
    session = AsyncMock()
    service = _service_with_sources([source])

    result = await service.retrieve_for_message(
        session,
        tenant_id=tenant_scope[0],
        business_id=tenant_scope[1],
    )

    assert len(result.snippets) == 1
    assert result.snippets[0].truncated is True
    assert len(result.snippets[0].content) <= MAX_SNIPPET_CONTENT_CHARS
    assert result.snippets[0].content.endswith("...")


@pytest.mark.anyio
async def test_simple_text_match_prefers_relevant_snippets(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    opening_hours = _source(
        tenant_scope,
        title="Opening hours",
        content="Monday to Friday 09:00-18:00",
        created_at=datetime(2026, 5, 1, 12, 0, 0),
    )
    pricing = _source(
        tenant_scope,
        title="Haircut pricing",
        content="Haircut costs 35 CHF",
        created_at=datetime(2026, 5, 1, 12, 1, 0),
    )
    session = AsyncMock()
    service = _service_with_sources([opening_hours, pricing])

    result = await service.retrieve_for_message(
        session,
        tenant_id=tenant_scope[0],
        business_id=tenant_scope[1],
        query_text="haircut price",
    )

    assert result.snippets[0].title == "Haircut pricing"


@pytest.mark.anyio
async def test_mismatched_tenant_scope_raises(
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    other_tenant = uuid.uuid4()
    wrong_scope = _source(
        (other_tenant, tenant_scope[1]),
        title="Wrong tenant",
        content="Out of scope",
    )
    session = AsyncMock()
    service = _service_with_sources([wrong_scope])

    with pytest.raises(TenantContextError):
        await service.retrieve_for_message(
            session,
            tenant_id=tenant_scope[0],
            business_id=tenant_scope[1],
        )


def test_knowledge_retrieval_service_module_has_no_provider_imports():
    import app.services.knowledge_retrieval_service as module

    source_path = module.__file__
    assert source_path is not None
    source = open(source_path, encoding="utf-8").read().lower()
    for forbidden in ("openai", "httpx", "aiohttp", "anthropic", "prompt_builder"):
        assert forbidden not in source


def test_knowledge_dtos_have_no_prompt_builder_fields():
    from app.schemas.knowledge import KnowledgeRetrievalResult, KnowledgeSnippet

    assert "system_prompt" not in KnowledgeSnippet.__dataclass_fields__
    assert "messages" not in KnowledgeRetrievalResult.__dataclass_fields__
