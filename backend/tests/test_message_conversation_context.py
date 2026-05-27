import uuid
from dataclasses import fields
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.elements import BinaryExpression

from app.models.message import Message
from app.schemas.conversation_context import ConversationHistoryMessage
from app.services.message_service import (
    CONVERSATION_HISTORY_MAX_LIMIT,
    CONVERSATION_HISTORY_MIN_LIMIT,
    MessageService,
)


def _select_filters(statement) -> dict[str, object]:
    criteria: dict[str, object] = {}
    whereclause = statement.whereclause
    if whereclause is None:
        return criteria

    clauses = getattr(whereclause, "clauses", [whereclause])
    for clause in clauses:
        if isinstance(clause, BinaryExpression) and hasattr(clause.left, "key"):
            criteria[clause.left.key] = clause.right.value
    return criteria


def _limit_value(statement) -> int | None:
    return statement._limit_clause.value if statement._limit_clause is not None else None


def _order_by_labels(statement) -> list[str]:
    labels: list[str] = []
    for order_clause in statement._order_by_clauses:
        element = order_clause.element
        while hasattr(element, "element"):
            element = element.element
        labels.append(getattr(element, "key", None))
    return labels


def _message(
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    conversation_id: uuid.UUID,
    sender_type: str,
    text: str,
    created_at: datetime,
) -> Message:
    return Message(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
        sender_type=sender_type,
        direction="incoming" if sender_type == "customer" else "outgoing",
        channel="whatsapp",
        message_text=text,
        external_message_id="ext-1",
        raw_payload={"secret": "payload"},
        ai_metadata={"model": "gpt"},
        metadata_={"internal": True},
        created_at=created_at,
    )


@pytest.fixture
def message_service() -> MessageService:
    return MessageService()


@pytest.fixture
def tenant_scope() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


@pytest.mark.anyio
async def test_load_recent_conversation_history_filters_by_tenant_business_conversation(
    message_service: MessageService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, conversation_id = tenant_scope
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: [])))

    await message_service.load_recent_conversation_history(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
    )

    statement = session.execute.await_args.args[0]
    filters = _select_filters(statement)
    assert filters == {
        "tenant_id": tenant_id,
        "business_id": business_id,
        "conversation_id": conversation_id,
    }


@pytest.mark.anyio
async def test_load_recent_conversation_history_limits_window(
    message_service: MessageService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, conversation_id = tenant_scope
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: [])))

    await message_service.load_recent_conversation_history(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
        limit=12,
    )

    statement = session.execute.await_args.args[0]
    assert _limit_value(statement) == 12


@pytest.mark.anyio
async def test_load_recent_conversation_history_rejects_limit_outside_window(
    message_service: MessageService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, conversation_id = tenant_scope
    session = AsyncMock()

    with pytest.raises(ValueError, match="limit must be between"):
        await message_service.load_recent_conversation_history(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            conversation_id=conversation_id,
            limit=CONVERSATION_HISTORY_MAX_LIMIT + 1,
        )


@pytest.mark.anyio
async def test_load_recent_conversation_history_returns_oldest_to_newest(
    message_service: MessageService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, conversation_id = tenant_scope
    older = _message(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
        sender_type="customer",
        text="First",
        created_at=datetime(2026, 5, 21, 10, 0, 0),
    )
    newer = _message(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
        sender_type="ai",
        text="Second",
        created_at=datetime(2026, 5, 21, 10, 5, 0),
    )
    session = AsyncMock()
    session.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=lambda: [newer, older]))
    )

    history = await message_service.load_recent_conversation_history(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
    )

    statement = session.execute.await_args.args[0]
    assert _order_by_labels(statement) == ["created_at"]
    assert _limit_value(statement) == CONVERSATION_HISTORY_MAX_LIMIT
    assert [item.message_text for item in history.messages] == ["First", "Second"]
    assert [item.sender_type for item in history.messages] == ["customer", "ai"]


@pytest.mark.anyio
async def test_load_recent_conversation_history_dto_excludes_internal_fields(
    message_service: MessageService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, conversation_id = tenant_scope
    row = _message(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
        sender_type="customer",
        text="Hello",
        created_at=datetime(2026, 5, 21, 10, 0, 0),
    )
    session = AsyncMock()
    session.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=lambda: [row]))
    )

    history = await message_service.load_recent_conversation_history(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
        limit=CONVERSATION_HISTORY_MIN_LIMIT,
    )

    dto_field_names = {field.name for field in fields(ConversationHistoryMessage)}
    assert dto_field_names == {"sender_type", "message_text", "created_at"}
    assert history.messages[0].message_text == "Hello"


@pytest.mark.anyio
async def test_load_recent_conversation_history_returns_empty_when_no_messages(
    message_service: MessageService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, conversation_id = tenant_scope
    session = AsyncMock()
    session.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=lambda: []))
    )

    history = await message_service.load_recent_conversation_history(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
    )

    assert history.messages == ()


def test_message_service_module_has_no_provider_imports():
    import app.services.message_service as module

    source_path = module.__file__
    assert source_path is not None
    source = open(source_path, encoding="utf-8").read().lower()
    for forbidden in ("openai", "httpx", "aiohttp", "anthropic"):
        assert forbidden not in source
