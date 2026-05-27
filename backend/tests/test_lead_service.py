import uuid
from datetime import date, datetime, time
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.elements import BinaryExpression

from app.exceptions import TenantContextError
from app.models.lead import (
    LEAD_PRIORITY_NORMAL,
    LEAD_PRIORITY_URGENT,
    LEAD_STATUS_CLOSED,
    LEAD_STATUS_CONTACTED,
    LEAD_STATUS_IN_PROGRESS,
    LEAD_STATUS_LOST,
    LEAD_STATUS_NEW,
    Lead,
)
from app.services.lead_service import ACTIVE_LEAD_STATUSES, LeadService


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


def _lead_result(lead: Lead | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = lead
    return result


@pytest.fixture
def lead_service() -> LeadService:
    return LeadService()


@pytest.fixture
def lead_scope() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


@pytest.mark.anyio
async def test_find_active_lead_returns_matching_lead(
    lead_service: LeadService,
    lead_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, conversation_id = lead_scope
    active = Lead(
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        status=LEAD_STATUS_IN_PROGRESS,
        source_channel="whatsapp",
    )
    session = AsyncMock()
    session.execute.return_value = _lead_result(active)

    found = await lead_service.find_active_lead(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
    )

    assert found is active
    statement = session.execute.await_args.args[0]
    filters = _select_filters(statement)
    assert filters["tenant_id"] == tenant_id
    assert filters["business_id"] == business_id
    assert filters["customer_id"] == customer_id
    assert filters["conversation_id"] == conversation_id
    assert _status_filter_values(statement) == set(ACTIVE_LEAD_STATUSES)
    assert _order_by_labels(statement) == ["updated_at", "created_at"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "status",
    [LEAD_STATUS_CLOSED, LEAD_STATUS_LOST],
)
async def test_find_active_lead_excludes_closed_and_lost_statuses(
    lead_service: LeadService,
    status: str,
):
    session = AsyncMock()
    session.execute.return_value = _lead_result(None)

    await lead_service.find_active_lead(
        session,
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
    )

    statement = session.execute.await_args.args[0]
    status_values = _status_filter_values(statement)
    assert status not in status_values
    assert status_values == set(ACTIVE_LEAD_STATUSES)


@pytest.mark.anyio
async def test_find_active_lead_orders_by_latest_updated(
    lead_service: LeadService,
    lead_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, conversation_id = lead_scope
    latest = Lead(
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        status=LEAD_STATUS_CONTACTED,
        source_channel="whatsapp",
        updated_at=datetime(2026, 5, 24, 15, 0, 0),
        created_at=datetime(2026, 5, 24, 10, 0, 0),
    )
    session = AsyncMock()
    session.execute.return_value = _lead_result(latest)

    found = await lead_service.find_active_lead(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
    )

    assert found is latest
    statement = session.execute.await_args.args[0]
    assert _order_by_labels(statement) == ["updated_at", "created_at"]
    assert statement._limit_clause.value == 1


@pytest.mark.anyio
async def test_find_active_lead_enforces_tenant_and_business_scope(
    lead_service: LeadService,
    lead_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, conversation_id = lead_scope
    other_tenant = uuid.uuid4()
    session = AsyncMock()
    session.execute.return_value = _lead_result(None)

    await lead_service.find_active_lead(
        session,
        tenant_id=other_tenant,
        business_id=business_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
    )

    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["tenant_id"] == other_tenant
    assert filters["business_id"] == business_id


@pytest.mark.anyio
async def test_create_lead_sets_defaults_and_flushes_without_commit(
    lead_service: LeadService,
    lead_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, conversation_id = lead_scope
    session = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    lead = await lead_service.create_lead(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        source_channel="whatsapp",
    )

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()

    stored = session.add.call_args.args[0]
    assert lead is stored
    assert stored.tenant_id == tenant_id
    assert stored.business_id == business_id
    assert stored.customer_id == customer_id
    assert stored.conversation_id == conversation_id
    assert stored.status == LEAD_STATUS_NEW
    assert stored.priority == LEAD_PRIORITY_NORMAL
    assert stored.source_channel == "whatsapp"
    assert stored.service_requested is None
    assert stored.customer_note is None


@pytest.mark.anyio
async def test_update_lead_updates_allowed_fields_and_updated_at(
    lead_service: LeadService,
    lead_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, conversation_id = lead_scope
    lead = Lead(
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        status=LEAD_STATUS_NEW,
        priority=LEAD_PRIORITY_NORMAL,
        source_channel="whatsapp",
        customer_note="old note",
        service_requested="haircut",
        updated_at=datetime(2026, 5, 24, 8, 0, 0),
    )
    session = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    updated = await lead_service.update_lead(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        lead=lead,
        customer_note="new note",
        priority=LEAD_PRIORITY_URGENT,
        status=LEAD_STATUS_IN_PROGRESS,
        service_requested="beard trim",
        preferred_date=date(2026, 6, 1),
        preferred_time=time(14, 30),
        ai_summary="Customer wants beard trim Friday afternoon",
    )

    assert updated is lead
    assert lead.customer_note == "new note"
    assert lead.priority == LEAD_PRIORITY_URGENT
    assert lead.status == LEAD_STATUS_IN_PROGRESS
    assert lead.service_requested == "beard trim"
    assert lead.preferred_date == date(2026, 6, 1)
    assert lead.preferred_time == time(14, 30)
    assert lead.ai_summary == "Customer wants beard trim Friday afternoon"
    assert lead.updated_at > datetime(2026, 5, 24, 8, 0, 0)
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_update_lead_leaves_unpassed_fields_unchanged(
    lead_service: LeadService,
    lead_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, conversation_id = lead_scope
    lead = Lead(
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        status=LEAD_STATUS_NEW,
        priority=LEAD_PRIORITY_NORMAL,
        source_channel="whatsapp",
        customer_note="keep me",
        service_requested="coloring",
    )
    session = MagicMock()
    session.flush = AsyncMock()

    await lead_service.update_lead(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        lead=lead,
        ai_summary="summary only",
    )

    assert lead.customer_note == "keep me"
    assert lead.service_requested == "coloring"
    assert lead.priority == LEAD_PRIORITY_NORMAL
    assert lead.status == LEAD_STATUS_NEW
    assert lead.ai_summary == "summary only"


@pytest.mark.anyio
async def test_update_lead_rejects_wrong_tenant(
    lead_service: LeadService,
    lead_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, conversation_id = lead_scope
    lead = Lead(
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        status=LEAD_STATUS_NEW,
        source_channel="whatsapp",
    )
    session = MagicMock()

    with pytest.raises(TenantContextError, match="tenant"):
        await lead_service.update_lead(
            session,
            tenant_id=uuid.uuid4(),
            business_id=business_id,
            lead=lead,
            status=LEAD_STATUS_CONTACTED,
        )

    session.flush.assert_not_called()


@pytest.mark.anyio
async def test_update_lead_rejects_wrong_business(
    lead_service: LeadService,
    lead_scope: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
):
    tenant_id, business_id, customer_id, conversation_id = lead_scope
    lead = Lead(
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        status=LEAD_STATUS_NEW,
        source_channel="whatsapp",
    )
    session = MagicMock()

    with pytest.raises(TenantContextError, match="business"):
        await lead_service.update_lead(
            session,
            tenant_id=tenant_id,
            business_id=uuid.uuid4(),
            lead=lead,
            status=LEAD_STATUS_CONTACTED,
        )

    session.flush.assert_not_called()
