"""Retrieve tenant/business knowledge snippets for prompt building (T11.5)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import TenantContextError
from app.models.tenant_knowledge_source import TenantKnowledgeSource
from app.schemas.knowledge import KnowledgeRetrievalResult, KnowledgeSnippet
from app.services.tenant_knowledge_source_service import TenantKnowledgeSourceService

# MVP bounds to limit prompt injection surface and token use.
MAX_KNOWLEDGE_SNIPPETS = 5
MAX_SNIPPET_CONTENT_CHARS = 1_000
MAX_TOTAL_SNIPPET_CONTENT_CHARS = 4_000


class KnowledgeRetrievalService:
    def __init__(
        self,
        knowledge_source_service: TenantKnowledgeSourceService | None = None,
    ) -> None:
        self.knowledge_source_service = (
            knowledge_source_service or TenantKnowledgeSourceService()
        )

    async def retrieve_for_message(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        query_text: str | None = None,
    ) -> KnowledgeRetrievalResult:
        sources = await self.knowledge_source_service.list_active_for_business(
            session,
            tenant_id,
            business_id,
        )
        if not sources:
            return KnowledgeRetrievalResult.empty()

        active_sources = [
            source
            for source in sources
            if source.is_active and _is_scoped_to(source, tenant_id, business_id)
        ]
        if not active_sources:
            return KnowledgeRetrievalResult.empty()

        ranked = _rank_sources(active_sources, query_text)
        return _build_bounded_result(ranked)


def _is_scoped_to(
    source: TenantKnowledgeSource,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
) -> bool:
    if source.tenant_id != tenant_id or source.business_id != business_id:
        raise TenantContextError(
            "Knowledge source is not scoped to the requested tenant and business"
        )
    return True


def _rank_sources(
    sources: list[TenantKnowledgeSource],
    query_text: str | None,
) -> list[TenantKnowledgeSource]:
    normalized_query = query_text.strip().lower() if query_text and query_text.strip() else None
    if normalized_query is None:
        return sources

    return sorted(
        sources,
        key=lambda source: (
            -_text_match_score(source, normalized_query),
            source.created_at,
        ),
    )


def _text_match_score(source: TenantKnowledgeSource, query: str) -> int:
    tokens = [token for token in query.split() if token]
    if not tokens:
        return 0

    title_lower = source.title.lower() if source.title else ""
    content_lower = source.content.lower()
    combined = f"{title_lower} {content_lower}".strip()

    score = 0
    for token in tokens:
        if token in combined:
            score += 1
        if token in title_lower:
            score += 1
    return score


def _build_bounded_result(sources: list[TenantKnowledgeSource]) -> KnowledgeRetrievalResult:
    snippets: list[KnowledgeSnippet] = []
    total_content_chars = 0

    for source in sources:
        if len(snippets) >= MAX_KNOWLEDGE_SNIPPETS:
            break
        if total_content_chars >= MAX_TOTAL_SNIPPET_CONTENT_CHARS:
            break

        remaining_total = MAX_TOTAL_SNIPPET_CONTENT_CHARS - total_content_chars
        per_snippet_limit = min(MAX_SNIPPET_CONTENT_CHARS, remaining_total)
        content, truncated = _truncate_content(source.content, per_snippet_limit)
        if not content:
            continue

        snippets.append(
            KnowledgeSnippet(
                id=source.id,
                source_type=source.source_type,
                title=source.title,
                content=content,
                tags=source.tags,
                truncated=truncated,
            )
        )
        total_content_chars += len(content)

    return KnowledgeRetrievalResult(snippets=tuple(snippets))


def _truncate_content(content: str, max_chars: int) -> tuple[str, bool]:
    stripped = content.strip()
    if not stripped:
        return "", False
    if len(stripped) <= max_chars:
        return stripped, False
    if max_chars <= 3:
        return stripped[:max_chars], True
    return stripped[: max_chars - 3] + "...", True
