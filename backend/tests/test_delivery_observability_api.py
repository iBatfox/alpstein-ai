"""E2.6 — delivery observability API tests."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.delivery_event import (
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_PENDING,
    DeliveryEvent,
)
from app.schemas.delivery_event import FORBIDDEN_DELIVERY_RESPONSE_FIELDS

TEST_TOKEN = "delivery-observability-test-token"


@pytest.fixture(autouse=True)
def configure_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.n8n_backend_api_token", TEST_TOKEN)
    monkeypatch.setattr("app.api.webhook_auth.settings.n8n_backend_api_token", TEST_TOKEN)


@pytest.fixture
def db_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def _override() -> MagicMock:
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override
    yield session
    app.dependency_overrides.clear()


def _auth_headers() -> dict[str, str]:
    return {"X-Alpstein-Webhook-Token": TEST_TOKEN}


def _delivery(
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    conversation_id: uuid.UUID,
    status: str = DELIVERY_STATUS_PENDING,
) -> DeliveryEvent:
    now = datetime(2026, 5, 28, 12, 0, 0)
    return DeliveryEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=uuid.uuid4(),
        conversation_id=conversation_id,
        trace_id=uuid.uuid4(),
        outbound_message_id=uuid.uuid4(),
        channel="website_chat",
        status=status,
        retry_count=0,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_get_delivery_scoped_to_tenant_business(db_session: MagicMock):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    event = _delivery(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
    )

    from app.api.routes import observability as observability_routes

    service = MagicMock()

    async def _get_by_id(_session, *, tenant_id, business_id, delivery_id):
        if delivery_id != event.id:
            return None
        return event

    service.get_by_id = AsyncMock(side_effect=_get_by_id)
    observability_routes.delivery_visibility_service = service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ok = await client.get(
            f"/api/v1/observability/deliveries/{event.id}",
            params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
            headers=_auth_headers(),
        )
        missing = await client.get(
            f"/api/v1/observability/deliveries/{uuid.uuid4()}",
            params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
            headers=_auth_headers(),
        )

    assert ok.status_code == 200
    body = ok.json()
    assert body["success"] is True
    assert body["data"]["id"] == str(event.id)
    assert body["data"]["status"] == DELIVERY_STATUS_PENDING
    for forbidden in FORBIDDEN_DELIVERY_RESPONSE_FIELDS:
        assert forbidden not in body["data"]
    assert missing.status_code == 404


@pytest.mark.anyio
async def test_list_conversation_deliveries(db_session: MagicMock):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    events = [
        _delivery(
            tenant_id=tenant_id,
            business_id=business_id,
            conversation_id=conversation_id,
        )
    ]

    from app.api.routes import observability as observability_routes

    service = MagicMock()
    service.list_for_conversation = AsyncMock(return_value=events)
    observability_routes.delivery_visibility_service = service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/observability/conversations/{conversation_id}/deliveries",
            params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert len(payload["items"]) == 1
    assert payload["items"][0]["channel"] == "website_chat"


@pytest.mark.anyio
async def test_patch_delivery_reports_delivered(db_session: MagicMock):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    event = _delivery(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
    )
    delivered = _delivery(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=conversation_id,
        status=DELIVERY_STATUS_DELIVERED,
    )
    delivered.id = event.id

    from app.api.routes import observability as observability_routes

    service = MagicMock()
    service.report_status = AsyncMock(return_value=delivered)
    observability_routes.delivery_visibility_service = service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/observability/deliveries/{event.id}",
            params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
            headers=_auth_headers(),
            json={
                "status": "delivered",
                "provider_message_id": "site-msg-1",
            },
        )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == DELIVERY_STATUS_DELIVERED
    db_session.commit.assert_awaited_once()
