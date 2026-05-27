import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.elements import BinaryExpression

from app.models.customer import Customer
from app.services.customer_service import CustomerService


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


def _customer_result(customer: Customer) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = customer
    return result


@pytest.fixture
def customer_service() -> CustomerService:
    return CustomerService()


@pytest.fixture
def tenant_scope() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


@pytest.mark.anyio
async def test_get_or_create_customer_found_by_phone(
    customer_service: CustomerService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    tenant_id, business_id = tenant_scope
    existing = Customer(
        tenant_id=tenant_id,
        business_id=business_id,
        phone="+41791234567",
        source_channel="whatsapp",
    )
    session = AsyncMock()
    session.execute.return_value = _customer_result(existing)

    customer = await customer_service.get_or_create_customer(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        source_channel="whatsapp",
        phone="+41791234567",
    )

    assert customer is existing
    session.add.assert_not_called()
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["tenant_id"] == tenant_id
    assert filters["business_id"] == business_id
    assert filters["phone"] == "+41791234567"


@pytest.mark.anyio
async def test_get_or_create_customer_found_by_external_customer_id(
    customer_service: CustomerService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    tenant_id, business_id = tenant_scope
    existing = Customer(
        tenant_id=tenant_id,
        business_id=business_id,
        external_customer_id="wa_001",
        source_channel="whatsapp",
    )
    session = AsyncMock()
    session.execute.return_value = _customer_result(existing)

    customer = await customer_service.get_or_create_customer(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        source_channel="whatsapp",
        external_customer_id="wa_001",
    )

    assert customer is existing
    session.add.assert_not_called()
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters["tenant_id"] == tenant_id
    assert filters["business_id"] == business_id
    assert filters["source_channel"] == "whatsapp"
    assert filters["external_customer_id"] == "wa_001"


@pytest.mark.anyio
async def test_get_or_create_customer_created_when_missing(
    customer_service: CustomerService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    tenant_id, business_id = tenant_scope
    session = MagicMock()
    session.execute = AsyncMock(return_value=_none_result())
    session.flush = AsyncMock()

    customer = await customer_service.get_or_create_customer(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        source_channel="whatsapp",
        phone="+41790000001",
        external_customer_id="wa_new",
        name="Alex",
        email=None,
    )

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    created = session.add.call_args.args[0]
    assert created.tenant_id == tenant_id
    assert created.business_id == business_id
    assert created.phone == "+41790000001"
    assert created.external_customer_id == "wa_new"
    assert created.source_channel == "whatsapp"
    assert created.name == "Alex"
    assert created.email is None
    assert customer is created


@pytest.mark.anyio
async def test_get_or_create_customer_does_not_duplicate(
    customer_service: CustomerService,
    tenant_scope: tuple[uuid.UUID, uuid.UUID],
):
    tenant_id, business_id = tenant_scope
    session = MagicMock()
    session.execute = AsyncMock(return_value=_none_result())
    session.flush = AsyncMock()

    first = await customer_service.get_or_create_customer(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        source_channel="whatsapp",
        phone="+41790000002",
    )
    persisted = session.add.call_args.args[0]

    session.execute = AsyncMock(return_value=_customer_result(persisted))
    second = await customer_service.get_or_create_customer(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        source_channel="whatsapp",
        phone="+41790000002",
    )

    assert first is persisted
    assert second is persisted
    session.add.assert_called_once()
