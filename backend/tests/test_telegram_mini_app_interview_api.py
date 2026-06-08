import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlencode

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.business_context_builder import (
    MINI_APP_ALLOWED_USER_STATUS_ACTIVE,
    BusinessContextBuilderBusinessIntegration,
    BusinessContextBuilderMiniAppAllowedUser,
)
from app.services.telegram_mini_app_interview_service import (
    TelegramMiniAppInterviewService,
)

BOT_TOKEN = "123456:test-token"


def signed_init_data(*, telegram_user_id: int = 777001) -> str:
    pairs = {
        "auth_date": str(int(time.time())),
        "query_id": "interview-query-1",
        "user": json.dumps(
            {
                "id": telegram_user_id,
                "first_name": "Bridge",
                "username": "bridge_user",
            },
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    pairs["hash"] = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(pairs)


def init_headers(telegram_user_id: int = 777001) -> dict[str, str]:
    return {"X-Telegram-Init-Data": signed_init_data(telegram_user_id=telegram_user_id)}


@pytest.fixture(autouse=True)
def configure_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path):
    from app.api.routes import telegram_mini_app_business_context_builder as bridge

    monkeypatch.setattr(bridge.settings, "telegram_bot_token", BOT_TOKEN)
    monkeypatch.setattr(bridge.settings, "telegram_initdata_max_age_seconds", 86400)
    monkeypatch.setattr(
        bridge,
        "telegram_interview_service",
        TelegramMiniAppInterviewService(storage_root=tmp_path / "interview"),
    )

    access_service = MagicMock()

    async def _verify_allowed_user(_session, *, telegram_user_id: int):
        if telegram_user_id == 777999:
            return BusinessContextBuilderMiniAppAllowedUser(
                id=uuid.uuid4(),
                telegram_user_id=telegram_user_id,
                display_name="Missing Business",
                company_name="Missing Business",
                alpstein_business_id=None,
                status=MINI_APP_ALLOWED_USER_STATUS_ACTIVE,
                notes=None,
                created_at=datetime(2026, 6, 8, 12, 0, 0),
                updated_at=datetime(2026, 6, 8, 12, 0, 0),
            )
        return BusinessContextBuilderMiniAppAllowedUser(
            id=uuid.uuid4(),
            telegram_user_id=telegram_user_id,
            display_name="Bridge User",
            company_name="Alpstein Demo GmbH",
            alpstein_business_id="alpstein-ai",
            status=MINI_APP_ALLOWED_USER_STATUS_ACTIVE,
            notes=None,
            created_at=datetime(2026, 6, 8, 12, 0, 0),
            updated_at=datetime(2026, 6, 8, 12, 0, 0),
        )

    access_service.verify_allowed_user = AsyncMock(side_effect=_verify_allowed_user)
    access_service.list_integrations = AsyncMock(
        return_value=[
            BusinessContextBuilderBusinessIntegration(
                id=uuid.uuid4(),
                alpstein_business_id="alpstein-ai",
                channel_type="telegram",
                display_name="Telegram",
                status="connected",
                external_channel_id=None,
                provider="telegram",
                workflow_name="alpstein-customer-ingress",
                workflow_id="workflow-1",
                backend_route="alpstein-telegram/webhook",
                notes=None,
                created_at=datetime(2026, 6, 8, 12, 0, 0),
                updated_at=datetime(2026, 6, 8, 12, 0, 0),
            )
        ]
    )
    monkeypatch.setattr(bridge, "telegram_access_service", access_service)

    session = MagicMock()

    async def _override():
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override
    yield tmp_path
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_verified_user_can_create_interview_session():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/interview/session",
            headers=init_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["alpstein_business_id"] == "alpstein-ai"
    assert body["data"]["question"] == "What is the company name?"
    assert body["data"]["progress_total"] == 15


@pytest.mark.anyio
async def test_interview_answers_are_stored_by_business(configure_bridge):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/interview/answer",
            json={"content": "Alpstein AI"},
            headers=init_headers(),
        )

    assert response.status_code == 200
    session_path = configure_bridge / "interview" / "alpstein-ai" / "session.json"
    session = json.loads(session_path.read_text())
    assert session["alpstein_business_id"] == "alpstein-ai"
    assert session["answers"][0]["answer"] == "Alpstein AI"


@pytest.mark.anyio
async def test_generate_documents_saves_under_business_directory(configure_bridge):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/interview/answer",
            json={"content": "Alpstein AI"},
            headers=init_headers(),
        )
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/interview/generate-documents",
            headers=init_headers(),
        )

    assert response.status_code == 200
    business_dir = configure_bridge / "interview" / "alpstein-ai"
    assert (business_dir / "session.json").exists()
    documents = sorted(path.name for path in business_dir.glob("*.md"))
    assert any(name.endswith("business-analysis.md") for name in documents)
    assert any(name.endswith("technical-spec.md") for name in documents)
    assert str(business_dir).startswith(str(configure_bridge / "interview"))


@pytest.mark.anyio
async def test_user_cannot_access_another_business_document(configure_bridge):
    other_dir = configure_bridge / "interview" / "other-business"
    other_dir.mkdir(parents=True)
    (other_dir / "2026-06-08-business-analysis.md").write_text("secret")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/telegram-mini-app/business-context-builder/interview/documents/2026-06-08-business-analysis",
            headers=init_headers(),
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_missing_alpstein_business_id_is_safe():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/telegram-mini-app/business-context-builder/interview/session",
            headers=init_headers(telegram_user_id=777999),
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ALPSTEIN_BUSINESS_ID_REQUIRED"


@pytest.mark.anyio
async def test_document_path_traversal_is_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/telegram-mini-app/business-context-builder/interview/documents/..%2Fsecret",
            headers=init_headers(),
        )

    assert response.status_code == 404
