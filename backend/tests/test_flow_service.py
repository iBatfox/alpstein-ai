import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import DBAPIError

from app.exceptions import FlowNotFoundError
from app.models.flow import Flow
from app.services.flow_service import LEGACY_WEBHOOK_FLOW_KEY, FlowService, LegacyWebhookFlow

TENANT_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
BUSINESS_ID = uuid.UUID("22222222-2222-4222-8222-222222222223")


def _flow(*, flow_key: str = "default", is_default: bool = True) -> Flow:
    return Flow(
        id=uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa11"),
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        flow_key=flow_key,
        flow_name="Alpstein AI demo flow",
        status="active",
        is_default=is_default,
    )


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


@pytest.mark.anyio
async def test_resolve_explicit_flow_key():
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(True))
    service = FlowService()
    expected = _flow(flow_key="alpstein_assistant", is_default=False)
    service.get_by_flow_key = AsyncMock(return_value=expected)

    resolved = await service.resolve_for_webhook(
        session,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        flow_key="alpstein_assistant",
    )

    assert resolved is expected
    service.get_by_flow_key.assert_awaited_once_with(
        session,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        flow_key="alpstein_assistant",
    )


@pytest.mark.anyio
async def test_resolve_missing_flow_key_uses_default():
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(True))
    service = FlowService()
    expected = _flow()
    service.get_default_for_business = AsyncMock(return_value=expected)

    resolved = await service.resolve_for_webhook(
        session,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        flow_key=None,
    )

    assert resolved is expected
    service.get_default_for_business.assert_awaited_once()


@pytest.mark.anyio
async def test_resolve_unknown_flow_key_raises():
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(True))
    service = FlowService()
    service.get_by_flow_key = AsyncMock(return_value=None)

    with pytest.raises(FlowNotFoundError) as exc_info:
        await service.resolve_for_webhook(
            session,
            tenant_id=TENANT_ID,
            business_id=BUSINESS_ID,
            flow_key="unknown_flow",
        )

    assert exc_info.value.flow_key == "unknown_flow"


@pytest.mark.anyio
async def test_resolve_empty_flow_key_uses_default():
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(True))
    service = FlowService()
    expected = _flow()
    service.get_default_for_business = AsyncMock(return_value=expected)

    resolved = await service.resolve_for_webhook(
        session,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        flow_key="   ",
    )

    assert resolved is expected
    service.get_default_for_business.assert_awaited_once()


@pytest.mark.anyio
async def test_resolve_uses_legacy_fallback_when_flows_table_absent(caplog):
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(False))
    service = FlowService()
    service.get_default_for_business = AsyncMock()

    resolved = await service.resolve_for_webhook(
        session,
        tenant_id=TENANT_ID,
        business_id=BUSINESS_ID,
        flow_key=None,
    )

    assert isinstance(resolved, LegacyWebhookFlow)
    assert resolved.tenant_id == TENANT_ID
    assert resolved.business_id == BUSINESS_ID
    assert resolved.flow_key == LEGACY_WEBHOOK_FLOW_KEY
    service.get_default_for_business.assert_not_awaited()
    assert "flows table unavailable; using legacy webhook flow fallback" in caplog.text


@pytest.mark.anyio
async def test_resolve_does_not_swallow_unrelated_db_errors():
    session = MagicMock()
    session.execute = AsyncMock(return_value=_scalar_result(True))
    service = FlowService()
    unrelated = DBAPIError("select", {}, RuntimeError("database unavailable"))
    service.get_default_for_business = AsyncMock(side_effect=unrelated)

    with pytest.raises(DBAPIError) as exc_info:
        await service.resolve_for_webhook(
            session,
            tenant_id=TENANT_ID,
            business_id=BUSINESS_ID,
            flow_key=None,
        )

    assert exc_info.value is unrelated
