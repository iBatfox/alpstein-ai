import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.elements import BinaryExpression

from app.exceptions import BusinessNotFoundError
from app.models.business import Business
from app.services.business_service import BusinessService


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
def business_service() -> BusinessService:
    return BusinessService()


@pytest.mark.anyio
async def test_get_by_external_id_returns_business(business_service: BusinessService):
    external_id = "demo_barbershop_001"
    business = Business(
        tenant_id=uuid.uuid4(),
        external_id=external_id,
        name="Demo Barbershop",
    )

    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = business
    session.execute.return_value = result

    found = await business_service.get_by_external_id(session, external_id)

    assert found is business
    session.execute.assert_awaited_once()
    filters = _select_filters(session.execute.await_args.args[0])
    assert filters == {"external_id": external_id}


@pytest.mark.anyio
async def test_get_by_external_id_raises_when_not_found(
    business_service: BusinessService,
):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    with pytest.raises(BusinessNotFoundError):
        await business_service.get_by_external_id(session, "missing-business")

    filters = _select_filters(session.execute.await_args.args[0])
    assert filters == {"external_id": "missing-business"}


@pytest.mark.anyio
async def test_get_by_external_id_query_filters_by_external_id_only(
    business_service: BusinessService,
):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    with pytest.raises(BusinessNotFoundError):
        await business_service.get_by_external_id(session, "biz-only-filter")

    statement = session.execute.await_args.args[0]
    filters = _select_filters(statement)
    assert set(filters) == {"external_id"}
    assert "tenant_id" not in filters
