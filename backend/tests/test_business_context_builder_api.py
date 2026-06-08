import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.business_context_builder import (
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_USER,
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_COMPLETED,
    BusinessContextBuilderResult,
    BusinessContextBuilderMessage,
    BusinessContextBuilderSession,
)
from app.services.business_context_builder_service import (
    BusinessContextBuilderInvalidStatusTransitionError,
    BusinessContextBuilderScopeMismatchError,
    BusinessContextBuilderSessionClosedError,
    BusinessContextBuilderSessionNotFoundError,
)

TEST_TOKEN = "bcb-api-test-token"


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


@pytest.mark.anyio
async def test_create_business_context_builder_session_route(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session_id = uuid.uuid4()
    message_id = uuid.uuid4()
    now = datetime(2026, 6, 8, 12, 0, 0)
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        status=SESSION_STATUS_ACTIVE,
        current_step="company_information",
        created_at=now,
        updated_at=now,
    )
    first_message = BusinessContextBuilderMessage(
        id=message_id,
        tenant_id=tenant_id,
        business_id=business_id,
        session_id=session_id,
        role=MESSAGE_ROLE_ASSISTANT,
        content="Hello. I will help you create a draft Business Context.",
        created_at=now,
    )

    from app.api.routes import business_context_builder as bcb_routes

    service = MagicMock()
    service.create_session = AsyncMock(return_value=(builder_session, first_message))
    monkeypatch.setattr(bcb_routes, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/business-context-builder/sessions",
            json={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["session"]["id"] == str(session_id)
    assert body["data"]["message"]["id"] == str(message_id)
    assert body["data"]["message"]["role"] == MESSAGE_ROLE_ASSISTANT
    db_session.commit.assert_awaited_once()
    service.create_session.assert_awaited_once()


@pytest.mark.anyio
async def test_business_context_builder_requires_auth(db_session: MagicMock):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/business-context-builder/sessions/{uuid.uuid4()}",
            params={
                "tenant_id": str(uuid.uuid4()),
                "business_id": str(uuid.uuid4()),
            },
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_send_message_route_returns_ai_generated_assistant_reply(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime(2026, 6, 8, 12, 0, 0)
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        status=SESSION_STATUS_ACTIVE,
        current_step="business_description",
        created_at=now,
        updated_at=now,
    )
    user_message = BusinessContextBuilderMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        session_id=session_id,
        role=MESSAGE_ROLE_USER,
        content="Alpstein Services GmbH",
        created_at=now,
    )
    assistant_message = BusinessContextBuilderMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        session_id=session_id,
        role=MESSAGE_ROLE_ASSISTANT,
        content="What industry is your company in?",
        created_at=now,
    )

    from app.api.routes import business_context_builder as bcb_routes

    service = MagicMock()
    service.save_user_message = AsyncMock(
        return_value=(builder_session, user_message, assistant_message)
    )
    monkeypatch.setattr(bcb_routes, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/business-context-builder/sessions/{session_id}/messages",
            json={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
                "content": "Alpstein Services GmbH",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["assistant_message"]["content"] == "What industry is your company in?"
    assert body["data"]["user_message"]["content"] == "Alpstein Services GmbH"
    db_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_get_unfinished_session_returns_status_step_messages_and_null_result(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime(2026, 6, 8, 12, 0, 0)
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        status=SESSION_STATUS_ACTIVE,
        current_step="business_description",
        created_at=now,
        updated_at=now,
    )
    message = BusinessContextBuilderMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        session_id=session_id,
        role=MESSAGE_ROLE_ASSISTANT,
        content="What does your company do?",
        created_at=now,
    )

    from app.api.routes import business_context_builder as bcb_routes
    from app.services.business_context_builder_service import (
        BusinessContextBuilderSessionSnapshot,
    )

    service = MagicMock()
    service.get_session = AsyncMock(
        return_value=BusinessContextBuilderSessionSnapshot(
            session=builder_session,
            messages=[message],
            result=None,
        )
    )
    monkeypatch.setattr(bcb_routes, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/business-context-builder/sessions/{session_id}",
            params={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["session"]["status"] == SESSION_STATUS_ACTIVE
    assert body["data"]["session"]["current_step"] == "business_description"
    assert len(body["data"]["messages"]) == 1
    assert body["data"]["result"] is None


@pytest.mark.anyio
async def test_closed_session_message_route_returns_error_envelope(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session_id = uuid.uuid4()

    from app.api.routes import business_context_builder as bcb_routes

    service = MagicMock()
    service.save_user_message = AsyncMock(
        side_effect=BusinessContextBuilderSessionClosedError(
            "cannot modify session with status completed"
        )
    )
    monkeypatch.setattr(bcb_routes, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/business-context-builder/sessions/{session_id}/messages",
            json={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
                "content": "late message",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 400
    body = response.json()
    assert body == {
        "success": False,
        "error": {
            "code": "CONTEXT_BUILDER_SESSION_CLOSED",
            "message": "Business Context Builder session is completed or cancelled",
        },
    }
    db_session.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_complete_completed_session_returns_invalid_transition(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session_id = uuid.uuid4()

    from app.api.routes import business_context_builder as bcb_routes

    service = MagicMock()
    service.complete_session = AsyncMock(
        side_effect=BusinessContextBuilderInvalidStatusTransitionError(
            "cannot complete session with status completed"
        )
    )
    monkeypatch.setattr(bcb_routes, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/business-context-builder/sessions/{session_id}/complete",
            json={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "CONTEXT_BUILDER_INVALID_STATUS_TRANSITION"


@pytest.mark.anyio
async def test_complete_session_route_returns_generated_draft_result(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime(2026, 6, 8, 12, 0, 0)
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        status=SESSION_STATUS_COMPLETED,
        current_step="completed",
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    result = BusinessContextBuilderResult(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        session_id=session_id,
        structured_context={
            "company_overview": "AI generated overview",
            "missing_information": [],
        },
        generated_prompt="AI generated draft prompt.",
        created_at=now,
        updated_at=now,
    )

    from app.api.routes import business_context_builder as bcb_routes

    service = MagicMock()
    service.complete_session = AsyncMock(return_value=(builder_session, result))
    monkeypatch.setattr(bcb_routes, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/business-context-builder/sessions/{session_id}/complete",
            json={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["session"]["status"] == SESSION_STATUS_COMPLETED
    assert body["data"]["result"]["generated_prompt"] == "AI generated draft prompt."
    assert (
        body["data"]["result"]["structured_context"]["company_overview"]
        == "AI generated overview"
    )
    db_session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_get_completed_session_returns_stored_result(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime(2026, 6, 8, 12, 0, 0)
    builder_session = BusinessContextBuilderSession(
        id=session_id,
        tenant_id=tenant_id,
        business_id=business_id,
        status=SESSION_STATUS_COMPLETED,
        current_step="completed",
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    result = BusinessContextBuilderResult(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        session_id=session_id,
        structured_context={"company_overview": "Stored result"},
        generated_prompt="Stored draft prompt.",
        created_at=now,
        updated_at=now,
    )

    from app.api.routes import business_context_builder as bcb_routes
    from app.services.business_context_builder_service import (
        BusinessContextBuilderSessionSnapshot,
    )

    service = MagicMock()
    service.get_session = AsyncMock(
        return_value=BusinessContextBuilderSessionSnapshot(
            session=builder_session,
            messages=[],
            result=result,
        )
    )
    monkeypatch.setattr(bcb_routes, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/business-context-builder/sessions/{session_id}",
            params={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["result"]["generated_prompt"] == "Stored draft prompt."
    assert body["data"]["result"]["structured_context"]["company_overview"] == "Stored result"


@pytest.mark.anyio
async def test_not_found_session_returns_error_envelope(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.api.routes import business_context_builder as bcb_routes

    service = MagicMock()
    service.get_session = AsyncMock(side_effect=BusinessContextBuilderSessionNotFoundError())
    monkeypatch.setattr(bcb_routes, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/business-context-builder/sessions/{uuid.uuid4()}",
            params={
                "tenant_id": str(uuid.uuid4()),
                "business_id": str(uuid.uuid4()),
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "CONTEXT_BUILDER_SESSION_NOT_FOUND"


@pytest.mark.anyio
async def test_scope_mismatch_returns_error_envelope(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.api.routes import business_context_builder as bcb_routes

    service = MagicMock()
    service.get_session = AsyncMock(side_effect=BusinessContextBuilderScopeMismatchError())
    monkeypatch.setattr(bcb_routes, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/business-context-builder/sessions/{uuid.uuid4()}",
            params={
                "tenant_id": str(uuid.uuid4()),
                "business_id": str(uuid.uuid4()),
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "CONTEXT_BUILDER_SCOPE_MISMATCH"


@pytest.mark.anyio
async def test_contexts_route_passes_limit_offset_and_returns_pagination_metadata(
    db_session: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    now = datetime(2026, 6, 8, 12, 0, 0)
    result = BusinessContextBuilderResult(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business_id,
        session_id=uuid.uuid4(),
        structured_context={"company": {}},
        generated_prompt="Draft placeholder prompt text.",
        created_at=now,
        updated_at=now,
    )

    from app.api.routes import business_context_builder as bcb_routes

    service = MagicMock()
    service.list_contexts = AsyncMock(return_value=[result])
    monkeypatch.setattr(bcb_routes, "business_context_builder_service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/business-context-builder/contexts",
            params={
                "tenant_id": str(tenant_id),
                "business_id": str(business_id),
                "limit": "10",
                "offset": "20",
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["limit"] == 10
    assert body["data"]["offset"] == 20
    assert len(body["data"]["items"]) == 1
    service.list_contexts.assert_awaited_once_with(
        db_session,
        tenant_id=tenant_id,
        business_id=business_id,
        limit=10,
        offset=20,
    )
