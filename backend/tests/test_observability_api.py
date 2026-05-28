"""E2.5 — observability read API tests."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.message_trace import (
    TRACE_STATUS_COMPLETED,
    TRACE_STATUS_FAILED,
    TRACE_STATUS_SKIPPED_DUPLICATE,
    MessageTrace,
)
from app.schemas.message_trace import FORBIDDEN_TRACE_RESPONSE_FIELDS

TEST_TOKEN = "observability-api-test-token"


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


def _trace(
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    conversation_id: uuid.UUID,
    inbound_message_id: uuid.UUID,
    status: str = TRACE_STATUS_COMPLETED,
    external_message_id: str | None = "ext-1",
) -> MessageTrace:
    now = datetime(2026, 5, 28, 12, 0, 0)
    return MessageTrace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        flow_id=uuid.uuid4(),
        conversation_id=conversation_id,
        inbound_message_id=inbound_message_id,
        outbound_message_id=uuid.uuid4(),
        channel="telegram",
        status=status,
        flow_key="default",
        external_conversation_id="tg:1",
        external_message_id=external_message_id,
        idempotency_key="ext:ext-1",
        external_trace_id=str(uuid.uuid4()),
        langfuse_trace_id="lf-trace-optional",
        error_type=None,
        error_message=None,
        metadata_={
            "correlation_id": str(uuid.uuid4()),
            "n8n_execution_id": "exec-99",
            "prompt_run_id": str(uuid.uuid4()),
        },
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_get_trace_by_id_scoped_to_tenant_business(db_session: MagicMock):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    other_business_id = uuid.uuid4()
    trace = _trace(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=uuid.uuid4(),
        inbound_message_id=uuid.uuid4(),
    )

    from app.api.routes import observability as observability_routes

    service = MagicMock()

    async def _get_trace(_session, *, tenant_id, business_id, trace_id):
        if business_id == other_business_id:
            return None
        return trace

    service.get_trace_by_id = AsyncMock(side_effect=_get_trace)
    observability_routes.message_trace_service = service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ok = await client.get(
            f"/api/v1/observability/traces/{trace.id}",
            params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
            headers=_auth_headers(),
        )
        missing = await client.get(
            f"/api/v1/observability/traces/{trace.id}",
            params={
                "tenant_id": str(tenant_id),
                "business_id": str(other_business_id),
            },
            headers=_auth_headers(),
        )

    assert ok.status_code == 200
    body = ok.json()
    assert body["success"] is True
    assert body["data"]["id"] == str(trace.id)
    assert body["data"]["status"] == TRACE_STATUS_COMPLETED
    assert body["data"]["langfuse_trace_id"] == "lf-trace-optional"
    assert missing.status_code == 404
    service.get_trace_by_id.assert_awaited()


@pytest.mark.anyio
async def test_lookup_trace_by_inbound_message_id(db_session: MagicMock):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    inbound_id = uuid.uuid4()
    trace = _trace(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=uuid.uuid4(),
        inbound_message_id=inbound_id,
    )

    from app.api.routes import observability as observability_routes

    service = MagicMock()
    service.find_by_inbound_message_id = AsyncMock(return_value=trace)
    observability_routes.message_trace_service = service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/observability/traces",
            params={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
                "inbound_message_id": str(inbound_id),
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json()["data"]["inbound_message_id"] == str(inbound_id)


@pytest.mark.anyio
async def test_list_conversation_traces(db_session: MagicMock):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    traces = [
        _trace(
            tenant_id=tenant_id,
            business_id=business_id,
            conversation_id=conversation_id,
            inbound_message_id=uuid.uuid4(),
        )
    ]

    from app.api.routes import observability as observability_routes

    service = MagicMock()
    service.list_traces_for_conversation = AsyncMock(return_value=traces)
    observability_routes.message_trace_service = service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/observability/conversations/{conversation_id}/traces",
            params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["conversation_id"] == str(conversation_id)


@pytest.mark.anyio
async def test_failed_trace_serializes_error_fields(db_session: MagicMock):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    trace = _trace(
        tenant_id=tenant_id,
        business_id=business_id,
        conversation_id=uuid.uuid4(),
        inbound_message_id=uuid.uuid4(),
        status=TRACE_STATUS_FAILED,
    )
    trace.error_type = "RuntimeError"
    trace.error_message = "provider timeout"
    trace.langfuse_trace_id = None

    from app.api.routes import observability as observability_routes

    service = MagicMock()
    service.get_trace_by_id = AsyncMock(return_value=trace)
    observability_routes.message_trace_service = service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/observability/traces/{trace.id}",
            params={"tenant_id": str(tenant_id), "business_id": str(business_id)},
            headers=_auth_headers(),
        )

    data = response.json()["data"]
    assert data["status"] == TRACE_STATUS_FAILED
    assert data["error_type"] == "RuntimeError"
    assert data["error_message"] == "provider timeout"
    serialized = json.dumps(response.json()).lower()
    for forbidden in FORBIDDEN_TRACE_RESPONSE_FIELDS:
        assert forbidden not in serialized


@pytest.mark.anyio
async def test_observability_requires_auth(db_session: MagicMock):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/observability/traces/{uuid.uuid4()}",
            params={
                "tenant_id": str(uuid.uuid4()),
                "business_id": str(uuid.uuid4()),
            },
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_duplicate_trace_status_exposed(db_session: MagicMock):
    trace = _trace(
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        inbound_message_id=uuid.uuid4(),
        status=TRACE_STATUS_SKIPPED_DUPLICATE,
    )

    from app.schemas.message_trace_mapper import message_trace_to_response

    response = message_trace_to_response(trace)
    assert response.status == TRACE_STATUS_SKIPPED_DUPLICATE
