"""E3.3b — adapter observability API tests."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.adapter_health import FORBIDDEN_ADAPTER_RESPONSE_FIELDS
from app.services.adapter_monitoring_service import AdapterHealthSnapshot
from app.services.ingress_isolation_policy import IsolationSummary

TEST_TOKEN = "e3-3-adapter-monitoring-test"


@pytest.fixture(autouse=True)
def configure_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.n8n_backend_api_token", TEST_TOKEN)
    monkeypatch.setattr("app.api.webhook_auth.settings.n8n_backend_api_token", TEST_TOKEN)


@pytest.fixture
def db_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    session = MagicMock()

    async def _override() -> MagicMock:
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override
    yield session
    app.dependency_overrides.clear()


def _auth_headers() -> dict[str, str]:
    return {"X-Alpstein-Webhook-Token": TEST_TOKEN}


def _snapshot(
    *,
    adapter: str = "telegram",
    status: str = "healthy",
) -> AdapterHealthSnapshot:
    now = datetime(2026, 5, 28, 14, 0, 0)
    return AdapterHealthSnapshot(
        adapter=adapter,
        status=status,
        status_reasons=[],
        ingress_status=status,
        delivery_status=status,
        ingress_status_reasons=[],
        delivery_status_reasons=[],
        containment_status="normal",
        recent_messages=10,
        ingress_failed_count=0,
        ingress_retry_count=0,
        ingress_dead_letter_count=0,
        delivery_success_count=9,
        delivery_failure_count=1,
        delivery_pending_count=0,
        retry_count=1,
        dead_letter_count=0,
        delivery_failure_rate=0.1,
        last_activity_at=now,
        evaluated_at=now,
        breakdown=None,
    )


@pytest.mark.anyio
async def test_list_adapters_returns_both_monitored_adapters(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    snapshots = [
        _snapshot(adapter="telegram"),
        _snapshot(adapter="website_chat", status="warning"),
    ]
    monkeypatch.setattr(
        "app.api.routes.observability.adapter_monitoring_service.list_adapters",
        AsyncMock(
            return_value=(
                24,
                snapshots,
                IsolationSummary(
                    isolation_status="intact",
                    spread_risk=False,
                    affected_adapters=[],
                    healthy_adapters=["telegram", "website_chat"],
                    inactive_adapters=[],
                    containment_notes=[],
                ),
            )
        ),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/observability/adapters",
            params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["window_hours"] == 24
    assert body["data"]["isolation_summary"]["isolation_status"] == "intact"
    assert {item["adapter"] for item in body["data"]["items"]} == {
        "telegram",
        "website_chat",
    }
    assert body["data"]["items"][0]["status"] in {
        "healthy",
        "warning",
        "degraded",
        "inactive",
    }


@pytest.mark.anyio
async def test_get_adapter_detail_includes_breakdown(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    snapshot = _snapshot(adapter="telegram")
    snapshot.ingress_status = "healthy"
    snapshot.delivery_status = "healthy"
    snapshot.ingress_status_reasons = []
    snapshot.delivery_status_reasons = []
    snapshot.containment_status = "normal"
    snapshot.ingress_failed_count = 0
    snapshot.ingress_retry_count = 0
    snapshot.ingress_dead_letter_count = 0
    snapshot.breakdown = {"delivery_by_status": {"delivered": 9, "failed": 1}}
    monkeypatch.setattr(
        "app.api.routes.observability.adapter_monitoring_service.get_adapter",
        AsyncMock(return_value=snapshot),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/observability/adapters/telegram",
            params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["adapter"] == "telegram"
    assert body["data"]["breakdown"]["delivery_by_status"]["delivered"] == 9


@pytest.mark.anyio
async def test_unknown_adapter_returns_404(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "app.api.routes.observability.adapter_monitoring_service.get_adapter",
        AsyncMock(return_value=None),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/observability/adapters/whatsapp",
            params={
                "tenant_id": str(uuid.uuid4()),
                "business_id": str(uuid.uuid4()),
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_list_adapters_requires_tenant_business():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/observability/adapters",
            headers=_auth_headers(),
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_adapter_response_schema_rejects_forbidden_fields():
    now = datetime(2026, 5, 28, 14, 0, 0)
    payload = {
        "adapter": "telegram",
        "status": "healthy",
        "status_reasons": [],
        "ingress_status": "healthy",
        "delivery_status": "healthy",
        "ingress_status_reasons": [],
        "delivery_status_reasons": [],
        "containment_status": "normal",
        "recent_messages": 1,
        "ingress_failed_count": 0,
        "ingress_retry_count": 0,
        "ingress_dead_letter_count": 0,
        "delivery_success_count": 1,
        "delivery_failure_count": 0,
        "delivery_pending_count": 0,
        "retry_count": 0,
        "dead_letter_count": 0,
        "delivery_failure_rate": None,
        "last_activity_at": now,
        "evaluated_at": now,
    }
    for field in FORBIDDEN_ADAPTER_RESPONSE_FIELDS:
        bad = dict(payload)
        bad[field] = "secret-value"
        with pytest.raises(ValueError, match="Forbidden adapter response fields"):
            from app.schemas.adapter_health import AdapterHealthResponse

            AdapterHealthResponse.model_validate(bad)
