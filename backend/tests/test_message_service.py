import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.sql.elements import BinaryExpression

from app.exceptions import TenantContextError
from app.models.message import Message
from app.services.message_service import MessageService


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


@pytest.fixture
def message_service() -> MessageService:
    return MessageService()


def _context_entities():
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    conversation_id = uuid.uuid4()

    business = SimpleNamespace(id=business_id, tenant_id=tenant_id)
    customer = SimpleNamespace(
        id=customer_id,
        tenant_id=tenant_id,
        business_id=business_id,
    )
    conversation = SimpleNamespace(
        id=conversation_id,
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        channel="whatsapp",
    )
    return tenant_id, business, conversation, customer


@pytest.mark.anyio
async def test_find_by_external_id_finds_existing_message(message_service: MessageService):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    external_message_id = "ext-msg-001"
    existing = Message(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=uuid.uuid4(),
        sender_type="customer",
        direction="inbound",
        channel="whatsapp",
        message_text="hello",
        external_message_id=external_message_id,
    )

    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    session.execute.return_value = result

    found = await message_service.find_by_external_id(
        session,
        tenant_id,
        business_id,
        external_message_id,
    )

    assert found is existing
    session.execute.assert_awaited_once()
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["tenant_id"] == tenant_id
    assert filters["business_id"] == business_id
    assert filters["external_message_id"] == external_message_id


@pytest.mark.anyio
async def test_find_by_external_id_returns_none_when_external_message_id_missing(
    message_service: MessageService,
):
    session = AsyncMock()

    found = await message_service.find_by_external_id(
        session,
        uuid.uuid4(),
        uuid.uuid4(),
        None,
    )

    assert found is None
    session.execute.assert_not_awaited()


@pytest.mark.anyio
async def test_find_by_external_id_returns_none_for_different_tenant_id(
    message_service: MessageService,
):
    tenant_id = uuid.uuid4()
    other_tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    external_message_id = "ext-msg-002"

    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    found = await message_service.find_by_external_id(
        session,
        tenant_id,
        business_id,
        external_message_id,
    )

    assert found is None
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["tenant_id"] == tenant_id
    assert filters["tenant_id"] != other_tenant_id


@pytest.mark.anyio
async def test_find_by_external_id_returns_none_for_different_business_id(
    message_service: MessageService,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    other_business_id = uuid.uuid4()
    external_message_id = "ext-msg-003"

    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    found = await message_service.find_by_external_id(
        session,
        tenant_id,
        business_id,
        external_message_id,
    )

    assert found is None
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["business_id"] == business_id
    assert filters["business_id"] != other_business_id


@pytest.mark.anyio
async def test_save_incoming_customer_message_inserts_one_message(
    message_service: MessageService,
):
    tenant_id, business, conversation, customer = _context_entities()
    session = MagicMock()
    session.flush = AsyncMock()

    with patch.object(
        message_service,
        "find_by_external_id",
        new_callable=AsyncMock,
        return_value=None,
    ) as find_mock:
        result = await message_service.save_incoming_customer_message(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            message_text="hello",
            external_message_id="ext-save-001",
            raw_payload={"provider": "test"},
        )

    find_mock.assert_awaited_once_with(
        session,
        tenant_id,
        business.id,
        "ext-save-001",
    )
    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    assert result.is_duplicate is False

    message = session.add.call_args.args[0]
    assert message.tenant_id == tenant_id
    assert message.business_id == business.id
    assert message.conversation_id == conversation.id
    assert message.sender_type == "customer"
    assert message.direction == "incoming"
    assert message.channel == "whatsapp"
    assert message.message_text == "hello"
    assert message.message_type == "text"
    assert message.external_message_id == "ext-save-001"
    assert message.raw_payload == {"provider": "test"}
    assert result.message is message


@pytest.mark.anyio
async def test_save_incoming_customer_message_returns_duplicate_without_insert(
    message_service: MessageService,
):
    tenant_id, business, conversation, customer = _context_entities()
    existing = Message(
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="whatsapp",
        message_text="hello",
        external_message_id="ext-dup-001",
    )
    session = MagicMock()
    session.flush = AsyncMock()

    with patch.object(
        message_service,
        "find_by_external_id",
        new_callable=AsyncMock,
        return_value=existing,
    ):
        result = await message_service.save_incoming_customer_message(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            message_text="hello again",
            external_message_id="ext-dup-001",
        )

    session.add.assert_not_called()
    session.flush.assert_not_awaited()
    assert result.is_duplicate is True
    assert result.message is existing


@pytest.mark.anyio
async def test_save_incoming_customer_message_skips_dedup_when_external_message_id_none(
    message_service: MessageService,
):
    tenant_id, business, conversation, customer = _context_entities()
    session = MagicMock()
    session.flush = AsyncMock()

    with patch.object(
        message_service,
        "find_by_external_id",
        new_callable=AsyncMock,
    ) as find_mock:
        result = await message_service.save_incoming_customer_message(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            message_text="no external id",
            external_message_id=None,
        )

    find_mock.assert_not_awaited()
    session.add.assert_called_once()
    assert session.add.call_args.args[0].external_message_id is None
    assert result.is_duplicate is False


@pytest.mark.anyio
async def test_save_incoming_customer_message_skips_dedup_when_external_message_id_empty(
    message_service: MessageService,
):
    tenant_id, business, conversation, customer = _context_entities()
    session = MagicMock()
    session.flush = AsyncMock()

    with patch.object(
        message_service,
        "find_by_external_id",
        new_callable=AsyncMock,
    ) as find_mock:
        result = await message_service.save_incoming_customer_message(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            message_text="empty external id",
            external_message_id="",
        )

    find_mock.assert_not_awaited()
    session.add.assert_called_once()
    assert session.add.call_args.args[0].external_message_id is None
    assert result.is_duplicate is False


@pytest.mark.anyio
async def test_save_incoming_customer_message_raises_on_tenant_mismatch(
    message_service: MessageService,
):
    tenant_id, business, conversation, customer = _context_entities()
    business.tenant_id = uuid.uuid4()
    session = MagicMock()

    with pytest.raises(TenantContextError, match="business does not belong to tenant"):
        await message_service.save_incoming_customer_message(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            message_text="hello",
        )

    session.add.assert_not_called()


@pytest.mark.anyio
async def test_save_incoming_customer_message_raises_on_context_mismatch(
    message_service: MessageService,
):
    tenant_id, business, conversation, customer = _context_entities()
    conversation.business_id = uuid.uuid4()
    session = MagicMock()

    with pytest.raises(
        TenantContextError,
        match="conversation does not belong to business",
    ):
        await message_service.save_incoming_customer_message(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            message_text="hello",
        )

    session.add.assert_not_called()


@pytest.mark.anyio
async def test_save_outgoing_ai_message_inserts_one_message(
    message_service: MessageService,
):
    tenant_id, business, conversation, customer = _context_entities()
    session = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    message = await message_service.save_outgoing_ai_message(
        session,
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        customer=customer,
        message_text="Sure. What time works for you?",
        ai_metadata={"model": "gpt-4o-mini"},
    )

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    session.commit.assert_not_called()

    stored = session.add.call_args.args[0]
    assert message is stored
    assert stored.tenant_id == tenant_id
    assert stored.business_id == business.id
    assert stored.conversation_id == conversation.id
    assert stored.sender_type == "ai"
    assert stored.direction == "outgoing"
    assert stored.channel == "whatsapp"
    assert stored.message_text == "Sure. What time works for you?"
    assert stored.message_type == "text"
    assert stored.external_message_id is None
    assert stored.raw_payload is None
    assert stored.ai_metadata == {"model": "gpt-4o-mini"}


@pytest.mark.anyio
async def test_save_outgoing_ai_message_uses_explicit_channel(
    message_service: MessageService,
):
    tenant_id, business, conversation, _customer = _context_entities()
    session = MagicMock()
    session.flush = AsyncMock()

    await message_service.save_outgoing_ai_message(
        session,
        tenant_id=tenant_id,
        business=business,
        conversation=conversation,
        message_text="Reply",
        channel="telegram",
    )

    stored = session.add.call_args.args[0]
    assert stored.channel == "telegram"


@pytest.mark.anyio
async def test_save_outgoing_ai_message_raises_on_tenant_mismatch(
    message_service: MessageService,
):
    tenant_id, business, conversation, customer = _context_entities()
    conversation.tenant_id = uuid.uuid4()
    session = MagicMock()

    with pytest.raises(
        TenantContextError,
        match="conversation does not belong to tenant",
    ):
        await message_service.save_outgoing_ai_message(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            message_text="Reply",
        )

    session.add.assert_not_called()


@pytest.mark.anyio
async def test_find_last_outgoing_ai_message_returns_latest_row(
    message_service: MessageService,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    latest = Message(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
        sender_type="ai",
        direction="outgoing",
        channel="whatsapp",
        message_text="Latest AI reply",
    )

    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = latest
    session.execute.return_value = result

    found = await message_service.find_last_outgoing_ai_message(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
    )

    assert found is latest
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["tenant_id"] == tenant_id
    assert filters["business_id"] == business_id
    assert filters["conversation_id"] == conversation_id
    assert filters["sender_type"] == "ai"
    assert filters["direction"] == "outgoing"
