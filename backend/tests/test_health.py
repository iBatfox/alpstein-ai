import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.session import get_db_session


@pytest.mark.anyio
async def test_health_endpoint_returns_expected_envelope():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {
            "status": "ok",
            "service": "alpstein-ai-backend",
            "environment": "production",
        },
    }


@pytest.mark.anyio
async def test_health_ready_endpoint_returns_ready_when_db_reachable():
    class DummyResult:
        def scalar_one_or_none(self):
            return 1

    class DummySession:
        async def execute(self, _query):
            return DummyResult()

    previous_overrides = dict(app.dependency_overrides)

    async def override_get_db_session():
        yield DummySession()

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")

        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "data": {
                "status": "ready",
                "service": "alpstein-ai-backend",
                "environment": "production",
                "db": "reachable",
            },
        }
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.mark.anyio
async def test_health_ready_endpoint_returns_error_when_db_unreachable():
    class DummySession:
        async def execute(self, _query):
            raise Exception("db down")

    previous_overrides = dict(app.dependency_overrides)

    async def override_get_db_session():
        yield DummySession()

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")

        assert response.status_code != 200
        assert response.json() == {
            "success": False,
            "error": {
                "code": "DATABASE_ERROR",
                "message": "PostgreSQL is not reachable",
            },
        }
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
