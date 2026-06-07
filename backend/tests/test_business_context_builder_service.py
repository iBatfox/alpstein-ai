import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.elements import BinaryExpression

from app.models.business_context_builder import (
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_USER,
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_IN_PROGRESS,
    BusinessContextBuilderMessage,
    BusinessContextBuilderResult,
    BusinessContextBuilderSession,
)
from app.services.business_context_builder_service import (
    STEP_BUSINESS_DESCRIPTION,
    STEP_COMPANY_INFORMATION,
    BusinessContextBuilderService,
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


def _result(*, scalar=None, scalars=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    result.scalars.return_value.all.return_value = scalars or []
    return result


@pytest.fixture
def service() -> BusinessContextBuilderService:
    return BusinessContextBuilderService()


@pytest.mark.anyio
async def test_create_session_saves_session_and_first_assistant_message(
    service: BusinessContextBuilderService,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session = MagicMock()
    session.execute = AsyncMock(return_value=_result(scalar=business_id))
    session.flush = AsyncMock()

    builder_session, first_message = await service.create_session(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
    )

    assert builder_session.tenant_id == tenant_id
    assert builder_session.business_id == business_id
    assert builder_session.status == SESSION_STATUS_IN_PROGRESS
    assert builder_session.current_step == STEP_COMPANY_INFORMATION
    assert first_message.tenant_id == tenant_id
    assert first_message.business_id == business_id
    assert first_message.session_id == builder_session.id
    assert first_message.role == MESSAGE_ROLE_ASSISTANT
    assert "What is the name of your company?" in first_message.content
    assert session.add.call_count == 2
    assert session.flush.await_count == 2
    session.execute.assert_not_awaited()


@pytest.mark.anyio
async def test_save_user_message_saves_user_and_assistant_placeholder_reply(
    service: BusinessContextBuilderService,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session_id = uuid.uuid4()
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        status=SESSION_STATUS_IN_PROGRESS,
        current_step=STEP_COMPANY_INFORMATION,
    )
    db_session = MagicMock()
    db_session.execute = AsyncMock(return_value=_result(scalar=builder_session))
    db_session.flush = AsyncMock()

    (
        updated_session,
        user_message,
        assistant_message,
    ) = await service.save_user_message(
        db_session,
        session_id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        content=" We are a local service business. ",
    )

    assert updated_session.current_step == STEP_BUSINESS_DESCRIPTION
    assert user_message.role == MESSAGE_ROLE_USER
    assert user_message.content == "We are a local service business."
    assert assistant_message.role == MESSAGE_ROLE_ASSISTANT
    assert assistant_message.content == "What does your company do?"
    assert db_session.add.call_count == 2
    assert db_session.flush.await_count == 1

    filters = _select_filters(db_session.execute.await_args.args[0])
    assert filters["id"] == session_id
    assert filters["tenant_id"] == tenant_id
    assert filters["business_id"] == business_id


@pytest.mark.anyio
async def test_get_session_returns_session_messages_and_result_scoped_to_business(
    service: BusinessContextBuilderService,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session_id = uuid.uuid4()
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        status=SESSION_STATUS_IN_PROGRESS,
    )
    messages = [
        BusinessContextBuilderMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
            role=MESSAGE_ROLE_ASSISTANT,
            content="Question",
        )
    ]
    result = None
    db_session = MagicMock()
    db_session.execute = AsyncMock(
        side_effect=[
            _result(scalar=builder_session),
            _result(scalars=messages),
            _result(scalar=result),
        ]
    )

    snapshot = await service.get_session(
        db_session,
        session_id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
    )

    assert snapshot.session is builder_session
    assert snapshot.messages == messages
    assert snapshot.result is None
    for call in db_session.execute.await_args_list:
        filters = _select_filters(call.args[0])
        assert filters["tenant_id"] == tenant_id
        assert filters["business_id"] == business_id


@pytest.mark.anyio
async def test_complete_session_creates_result_in_business_context_builder_schema(
    service: BusinessContextBuilderService,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session_id = uuid.uuid4()
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        status=SESSION_STATUS_IN_PROGRESS,
        current_step=STEP_BUSINESS_DESCRIPTION,
    )
    user_messages = [
        BusinessContextBuilderMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
            role=MESSAGE_ROLE_USER,
            content="Local services.",
        )
    ]
    db_session = MagicMock()
    db_session.execute = AsyncMock(
        side_effect=[
            _result(scalar=builder_session),
            _result(scalar=None),
            _result(scalars=user_messages),
        ]
    )
    db_session.flush = AsyncMock()

    completed_session, result = await service.complete_session(
        db_session,
        session_id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
    )

    assert completed_session.status == SESSION_STATUS_COMPLETED
    assert completed_session.current_step == "completed"
    assert result.tenant_id == tenant_id
    assert result.business_id == business_id
    assert result.session_id == session_id
    assert result.generated_prompt == "Draft placeholder prompt text."
    assert "company" in result.structured_context
    assert BusinessContextBuilderResult.__table__.schema == "business_context_builder"
    db_session.add.assert_called_once_with(result)
    db_session.flush.assert_awaited_once()


@pytest.mark.anyio
async def test_list_contexts_filters_by_tenant_and_business(
    service: BusinessContextBuilderService,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    result = BusinessContextBuilderResult(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        session_id=uuid.uuid4(),
        structured_context={"company": {}},
        generated_prompt="Draft placeholder prompt text.",
    )
    db_session = MagicMock()
    db_session.execute = AsyncMock(return_value=_result(scalars=[result]))

    contexts = await service.list_contexts(
        db_session,
        tenant_id=tenant_id,
        business_id=business_id,
        limit=25,
        offset=5,
    )

    assert contexts == [result]
    list_filters = _select_filters(db_session.execute.await_args.args[0])
    assert list_filters["tenant_id"] == tenant_id
    assert list_filters["business_id"] == business_id


def test_business_context_builder_service_does_not_import_production_assistant_models():
    import app.services.business_context_builder_service as module

    imported_names = set(module.__dict__)
    assert "TenantBusinessProfile" not in imported_names
    assert "TenantAiProfile" not in imported_names
    assert "TenantKnowledgeSource" not in imported_names
    assert "PromptTemplate" not in imported_names
    assert "PromptRun" not in imported_names
    assert "Business" not in imported_names
