import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.elements import BinaryExpression

from app.models.conversation import Conversation
from app.services.conversation_service import (
    NEW_CONVERSATION_STATUS,
    REUSABLE_CONVERSATION_STATUSES,
    ConversationService,
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


def _status_filter_values(statement) -> set[str]:
    whereclause = statement.whereclause
    if whereclause is None:
        return set()

    clauses = getattr(whereclause, "clauses", [whereclause])
    for clause in clauses:
        if (
            isinstance(clause, BinaryExpression)
            and hasattr(clause.left, "key")
            and clause.left.key == "status"
        ):
            return set(clause.right.value)
    return set()


def _order_by_labels(statement) -> list[str]:
    labels: list[str] = []
    for order_clause in statement._order_by_clauses:
        element = order_clause.element
        while hasattr(element, "element"):
            element = element.element
        labels.append(getattr(element, "key", None))
    return labels


def _none_result() -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    return result


def _conversation_result(conversation: Conversation) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = conversation
    return result


@pytest.fixture
def conversation_service() -> ConversationService:
    return ConversationService()


@pytest.fixture
def tenant_scope() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


@pytest.mark.anyio
@pytest.mark.parametrize("status", list(REUSABLE_CONVERSATION_STATUSES))
async def test_get_or_create_open_conversation_reuses_reusable_statuses(
    conversation_service: ConversationService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
    status: str,
):
    tenant_id, business_id, customer_id = tenant_scope
    existing = Conversation(
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        channel="whatsapp",
        status=status,
    )
    session = AsyncMock()
    session.execute.return_value = _conversation_result(existing)

    conversation = await conversation_service.get_or_create_open_conversation(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        channel="whatsapp",
    )

    assert conversation is existing
    session.add.assert_not_called()
    statement = session.execute.await_args.args[0]
    filters = _select_filters(statement)
    assert filters["tenant_id"] == tenant_id
    assert filters["business_id"] == business_id
    assert filters["customer_id"] == customer_id
    assert filters["channel"] == "whatsapp"
    assert _status_filter_values(statement) == set(REUSABLE_CONVERSATION_STATUSES)


@pytest.mark.anyio
async def test_get_or_create_open_conversation_created_when_missing(
    conversation_service: ConversationService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id = tenant_scope
    session = MagicMock()
    session.execute = AsyncMock(return_value=_none_result())
    session.flush = AsyncMock()

    conversation = await conversation_service.get_or_create_open_conversation(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        channel="telegram",
    )

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    created = session.add.call_args.args[0]
    assert created.tenant_id == tenant_id
    assert created.business_id == business_id
    assert created.customer_id == customer_id
    assert created.channel == "telegram"
    assert created.status == NEW_CONVERSATION_STATUS
    assert conversation is created


@pytest.mark.anyio
@pytest.mark.parametrize("status", ["closed", "archived"])
async def test_get_or_create_open_conversation_does_not_reuse_non_reusable_status(
    conversation_service: ConversationService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
    status: str,
):
    tenant_id, business_id, customer_id = tenant_scope
    session = MagicMock()
    session.execute = AsyncMock(return_value=_none_result())
    session.flush = AsyncMock()

    conversation = await conversation_service.get_or_create_open_conversation(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        channel="whatsapp",
    )

    session.add.assert_called_once()
    statement = session.execute.await_args.args[0]
    assert status not in _status_filter_values(statement)
    assert conversation.status == NEW_CONVERSATION_STATUS


@pytest.mark.anyio
async def test_get_or_create_open_conversation_selects_latest_reusable_conversation(
    conversation_service: ConversationService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id = tenant_scope
    latest = Conversation(
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        channel="whatsapp",
        status="waiting_for_customer",
        last_message_at=datetime(2026, 5, 21, 12, 0, 0),
        created_at=datetime(2026, 5, 21, 10, 0, 0),
    )
    session = AsyncMock()
    session.execute.return_value = _conversation_result(latest)

    conversation = await conversation_service.get_or_create_open_conversation(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        channel="whatsapp",
    )

    assert conversation is latest
    statement = session.execute.await_args.args[0]
    assert _order_by_labels(statement) == ["last_message_at", "created_at"]
