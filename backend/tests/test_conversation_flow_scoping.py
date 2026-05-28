"""E2.2 — conversation lookup scoped by flow_id."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.elements import BinaryExpression

from app.exceptions import TenantContextError
from app.models.conversation import Conversation
from app.services.conversation_service import (
    NEW_CONVERSATION_STATUS,
    ConversationService,
)
from app.services.message_service import MessageService
from app.services.tenant_context_validator import validate_tenant_context


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
def scope() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


@pytest.mark.anyio
async def test_same_flow_reuses_conversation_by_customer(
    conversation_service: ConversationService,
    scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, flow_id = scope
    existing = Conversation(
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=flow_id,
        customer_id=customer_id,
        channel="telegram",
        status="open",
    )
    session = AsyncMock()
    session.execute.return_value = _conversation_result(existing)

    conversation = await conversation_service.get_or_create_open_conversation(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=flow_id,
        customer_id=customer_id,
        channel="telegram",
    )

    assert conversation is existing
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["flow_id"] == flow_id
    assert filters["customer_id"] == customer_id


@pytest.mark.anyio
async def test_different_flow_does_not_reuse_same_customer_conversation(
    conversation_service: ConversationService,
    scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, flow_a = scope
    flow_b = uuid.uuid4()
    session = MagicMock()
    session.execute = AsyncMock(return_value=_none_result())
    session.flush = AsyncMock()

    conversation = await conversation_service.get_or_create_open_conversation(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=flow_b,
        customer_id=customer_id,
        channel="website_chat",
    )

    session.add.assert_called_once()
    created = session.add.call_args.args[0]
    assert created.flow_id == flow_b
    assert conversation.flow_id == flow_b
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["flow_id"] == flow_b


@pytest.mark.anyio
async def test_external_conversation_id_lookup_is_flow_scoped(
    conversation_service: ConversationService,
    scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, flow_id = scope
    existing = Conversation(
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=flow_id,
        customer_id=customer_id,
        channel="telegram",
        external_conversation_id="tg:chat-99",
        status="open",
    )
    session = AsyncMock()
    session.execute.return_value = _conversation_result(existing)

    conversation = await conversation_service.get_or_create_open_conversation(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=flow_id,
        customer_id=customer_id,
        channel="telegram",
        external_conversation_id="tg:chat-99",
    )

    assert conversation is existing
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["flow_id"] == flow_id
    assert filters["external_conversation_id"] == "tg:chat-99"
    assert "customer_id" not in filters


@pytest.mark.anyio
async def test_new_conversation_stores_flow_and_external_id(
    conversation_service: ConversationService,
    scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, flow_id = scope
    session = MagicMock()
    session.execute = AsyncMock(return_value=_none_result())
    session.flush = AsyncMock()

    await conversation_service.get_or_create_open_conversation(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=flow_id,
        customer_id=customer_id,
        channel="website_chat",
        external_conversation_id="web:session-1",
    )

    created = session.add.call_args.args[0]
    assert created.flow_id == flow_id
    assert created.external_conversation_id == "web:session-1"
    assert created.status == NEW_CONVERSATION_STATUS


def test_validate_tenant_context_rejects_conversation_from_other_flow():
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    flow_id = uuid.uuid4()
    other_flow_id = uuid.uuid4()
    business = type("Business", (), {"id": business_id, "tenant_id": tenant_id})()
    conversation = type(
        "Conversation",
        (),
        {
            "id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "business_id": business_id,
            "flow_id": other_flow_id,
            "customer_id": uuid.uuid4(),
        },
    )()

    with pytest.raises(TenantContextError, match="conversation does not belong to flow"):
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            flow_id=flow_id,
        )


@pytest.mark.anyio
async def test_message_service_rejects_wrong_flow_conversation():
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    flow_id = uuid.uuid4()
    business = type("Business", (), {"id": business_id, "tenant_id": tenant_id})()
    conversation = type(
        "Conversation",
        (),
        {
            "id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "business_id": business_id,
            "flow_id": uuid.uuid4(),
            "channel": "telegram",
        },
    )()
    session = MagicMock()

    with pytest.raises(TenantContextError, match="conversation does not belong to flow"):
        await MessageService().save_incoming_customer_message(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            message_text="Hi",
            flow_id=flow_id,
        )
