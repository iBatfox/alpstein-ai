"""E3.5d — real PostgreSQL concurrency validation for ingress rate limiting.

Requires live PostgreSQL with Alembic head applied. Skips when
``ALPSTEIN_AI_DATABASE_URL`` (or ``POSTGRES_TEST_URL``) is unavailable.

Run (from ``backend/``):

    ALPSTEIN_AI_DATABASE_URL='postgresql+asyncpg://user:pass@127.0.0.1:15433/alpstein_ai' \\
      .venv/bin/python -m pytest tests/test_e3_5_rate_limit_postgres_concurrency.py -v

Design:
- Two (or more) independent ``AsyncSession`` instances, each in ``session.begin()``
- ``asyncio.Barrier`` synchronizes concurrent entry into ``consume_ingress_request``
- ``SELECT ... FOR UPDATE`` inside ``RateLimitService._get_or_create_bucket`` must
  serialize bucket reads/increments so limits hold under race
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.models.business import Business
from app.models.rate_limit_bucket import SCOPE_BUSINESS, SCOPE_CONVERSATION, RateLimitBucket
from app.models.rate_limit_violation import RateLimitViolation
from app.models.tenant import Tenant
from app.services.rate_limit_policy import compute_window_start
from app.services.rate_limit_service import RateLimitExceededError, RateLimitService

BACKEND_DIR = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.postgres


def _postgres_url() -> str | None:
    return os.environ.get("ALPSTEIN_AI_DATABASE_URL") or os.environ.get("POSTGRES_TEST_URL")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "postgres: integration test requiring real PostgreSQL (ALPSTEIN_AI_DATABASE_URL)",
    )


@pytest.fixture(scope="session")
def postgres_url() -> str:
    url = _postgres_url()
    if not url:
        pytest.skip(
            "Set ALPSTEIN_AI_DATABASE_URL or POSTGRES_TEST_URL for postgres concurrency tests"
        )
    return url


@pytest.fixture(scope="session", autouse=True)
def ensure_alembic_head(postgres_url: str) -> None:
    env = os.environ.copy()
    env["ALPSTEIN_AI_DATABASE_URL"] = postgres_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            "alembic upgrade head failed before postgres concurrency tests:\n"
            f"{result.stderr or result.stdout}"
        )


@pytest.fixture
async def session_factory(postgres_url: str) -> AsyncIterator[Callable[[], AsyncSession]]:
    engine = create_async_engine(postgres_url, pool_pre_ping=True)
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    import app.db.session as db_session_module
    import app.services.rate_limit_service as rate_limit_service_module

    original_local = db_session_module.AsyncSessionLocal
    db_session_module.AsyncSessionLocal = factory
    rate_limit_service_module.AsyncSessionLocal = factory
    try:
        yield factory
    finally:
        db_session_module.AsyncSessionLocal = original_local
        rate_limit_service_module.AsyncSessionLocal = original_local
        await engine.dispose()


@pytest.fixture
async def rate_limit_fixture(
    session_factory: Callable[[], AsyncSession],
) -> AsyncIterator[tuple[uuid.UUID, uuid.UUID]]:
    tenant_id = uuid.uuid4()
    business_id = uuid.uuid4()
    slug = f"e35d-{tenant_id.hex[:12]}"

    async with session_factory() as session:
        async with session.begin():
            session.add(
                Tenant(
                    id=tenant_id,
                    name="E3.5d Concurrency Tenant",
                    slug=slug,
                    status="active",
                )
            )
            session.add(
                Business(
                    id=business_id,
                    tenant_id=tenant_id,
                    external_id=f"e35d-{business_id.hex[:12]}",
                    name="E3.5d Concurrency Business",
                    status="active",
                )
            )

    yield tenant_id, business_id

    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(RateLimitViolation).where(RateLimitViolation.tenant_id == tenant_id)
            )
            await session.execute(
                delete(RateLimitBucket).where(RateLimitBucket.tenant_id == tenant_id)
            )
            await session.execute(delete(Business).where(Business.id == business_id))
            await session.execute(delete(Tenant).where(Tenant.id == tenant_id))


def _high_limit_settings(**overrides) -> Settings:
    base = dict(
        rate_limit_enabled=True,
        rate_limit_window_seconds=60,
        rate_limit_tenant_limit=100_000,
        rate_limit_business_limit=100_000,
        rate_limit_adapter_telegram_limit=100_000,
        rate_limit_adapter_website_chat_limit=100_000,
        rate_limit_conversation_limit=100_000,
    )
    base.update(overrides)
    return Settings(**base)


async def _cleanup_scope_data(
    session_factory: Callable[[], AsyncSession],
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
) -> None:
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(RateLimitViolation).where(
                    RateLimitViolation.tenant_id == tenant_id,
                    RateLimitViolation.business_id == business_id,
                )
            )
            await session.execute(
                delete(RateLimitBucket).where(
                    RateLimitBucket.tenant_id == tenant_id,
                    RateLimitBucket.business_id == business_id,
                )
            )


async def _run_concurrent_consumes(
    session_factory: Callable[[], AsyncSession],
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    calls: list[tuple[str, uuid.UUID]],
) -> list[str | RateLimitExceededError]:
    barrier = asyncio.Barrier(len(calls))
    results: list[str | RateLimitExceededError | None] = [None] * len(calls)

    async def worker(index: int, channel: str, conversation_id: uuid.UUID) -> None:
        service = RateLimitService(settings)
        async with session_factory() as session:
            async with session.begin():
                await barrier.wait()
                try:
                    await service.consume_ingress_request(
                        session,
                        tenant_id=tenant_id,
                        business_id=business_id,
                        channel=channel,
                        conversation_id=conversation_id,
                        correlation_id=f"e35d-{index}",
                    )
                    results[index] = "accepted"
                except RateLimitExceededError as exc:
                    results[index] = exc

    await asyncio.gather(
        *[
            worker(index, channel, conversation_id)
            for index, (channel, conversation_id) in enumerate(calls)
        ]
    )
    return [item for item in results if item is not None]


async def _bucket_count(
    session_factory: Callable[[], AsyncSession],
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
    scope_type: str,
    scope_key: str,
    window_start: datetime,
) -> int | None:
    async with session_factory() as session:
        stmt = select(RateLimitBucket.request_count).where(
            RateLimitBucket.tenant_id == tenant_id,
            RateLimitBucket.business_id == business_id,
            RateLimitBucket.scope_type == scope_type,
            RateLimitBucket.scope_key == scope_key,
            RateLimitBucket.window_start == window_start,
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return row


async def _violation_count(
    session_factory: Callable[[], AsyncSession],
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
) -> int:
    async with session_factory() as session:
        stmt = (
            select(func.count())
            .select_from(RateLimitViolation)
            .where(
                RateLimitViolation.tenant_id == tenant_id,
                RateLimitViolation.business_id == business_id,
            )
        )
        result = await session.execute(stmt)
        return int(result.scalar_one())


@pytest.mark.anyio
async def test_scenario_1_concurrent_limit_one_one_accepted_one_rejected(
    session_factory: Callable[[], AsyncSession],
    rate_limit_fixture: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Limit=1, two concurrent requests on same conversation → one accept, one 429 path."""
    tenant_id, business_id = rate_limit_fixture
    await _cleanup_scope_data(session_factory, tenant_id=tenant_id, business_id=business_id)

    settings = _high_limit_settings(rate_limit_conversation_limit=1)
    conversation_id = uuid.uuid4()
    window_start = compute_window_start(
        now=datetime.utcnow(),
        window_seconds=settings.rate_limit_window_seconds,
    )

    results = await _run_concurrent_consumes(
        session_factory,
        settings,
        tenant_id=tenant_id,
        business_id=business_id,
        calls=[
            ("telegram", conversation_id),
            ("telegram", conversation_id),
        ],
    )

    accepted = [item for item in results if item == "accepted"]
    rejected = [item for item in results if isinstance(item, RateLimitExceededError)]
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0].details.scope_type == SCOPE_CONVERSATION

    conv_count = await _bucket_count(
        session_factory,
        tenant_id=tenant_id,
        business_id=business_id,
        scope_type=SCOPE_CONVERSATION,
        scope_key=str(conversation_id),
        window_start=window_start,
    )
    assert conv_count == 1
    assert (
        await _violation_count(
            session_factory, tenant_id=tenant_id, business_id=business_id
        )
        == 1
    )


@pytest.mark.anyio
async def test_scenario_2_concurrent_limit_two_both_accepted(
    session_factory: Callable[[], AsyncSession],
    rate_limit_fixture: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Limit=2, two concurrent requests → both accepted, count=2, no violations."""
    tenant_id, business_id = rate_limit_fixture
    await _cleanup_scope_data(session_factory, tenant_id=tenant_id, business_id=business_id)

    settings = _high_limit_settings(rate_limit_conversation_limit=2)
    conversation_id = uuid.uuid4()
    window_start = compute_window_start(
        now=datetime.utcnow(),
        window_seconds=settings.rate_limit_window_seconds,
    )

    results = await _run_concurrent_consumes(
        session_factory,
        settings,
        tenant_id=tenant_id,
        business_id=business_id,
        calls=[
            ("telegram", conversation_id),
            ("telegram", conversation_id),
        ],
    )

    assert results == ["accepted", "accepted"]
    conv_count = await _bucket_count(
        session_factory,
        tenant_id=tenant_id,
        business_id=business_id,
        scope_type=SCOPE_CONVERSATION,
        scope_key=str(conversation_id),
        window_start=window_start,
    )
    assert conv_count == 2
    assert (
        await _violation_count(
            session_factory, tenant_id=tenant_id, business_id=business_id
        )
        == 0
    )


@pytest.mark.anyio
async def test_scenario_3_different_conversations_use_independent_buckets(
    session_factory: Callable[[], AsyncSession],
    rate_limit_fixture: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Limit=1 per conversation; two different conversations both accepted."""
    tenant_id, business_id = rate_limit_fixture
    await _cleanup_scope_data(session_factory, tenant_id=tenant_id, business_id=business_id)

    settings = _high_limit_settings(rate_limit_conversation_limit=1)
    conversation_a = uuid.uuid4()
    conversation_b = uuid.uuid4()
    window_start = compute_window_start(
        now=datetime.utcnow(),
        window_seconds=settings.rate_limit_window_seconds,
    )

    results = await _run_concurrent_consumes(
        session_factory,
        settings,
        tenant_id=tenant_id,
        business_id=business_id,
        calls=[
            ("telegram", conversation_a),
            ("telegram", conversation_b),
        ],
    )

    assert results == ["accepted", "accepted"]
    assert (
        await _bucket_count(
            session_factory,
            tenant_id=tenant_id,
            business_id=business_id,
            scope_type=SCOPE_CONVERSATION,
            scope_key=str(conversation_a),
            window_start=window_start,
        )
        == 1
    )
    assert (
        await _bucket_count(
            session_factory,
            tenant_id=tenant_id,
            business_id=business_id,
            scope_type=SCOPE_CONVERSATION,
            scope_key=str(conversation_b),
            window_start=window_start,
        )
        == 1
    )
    assert (
        await _violation_count(
            session_factory, tenant_id=tenant_id, business_id=business_id
        )
        == 0
    )


@pytest.mark.anyio
async def test_scenario_4_business_scope_shared_across_channels(
    session_factory: Callable[[], AsyncSession],
    rate_limit_fixture: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Business limit=1; telegram + website_chat share one business bucket."""
    tenant_id, business_id = rate_limit_fixture
    await _cleanup_scope_data(session_factory, tenant_id=tenant_id, business_id=business_id)

    settings = _high_limit_settings(rate_limit_business_limit=1)
    telegram_conversation = uuid.uuid4()
    website_conversation = uuid.uuid4()
    window_start = compute_window_start(
        now=datetime.utcnow(),
        window_seconds=settings.rate_limit_window_seconds,
    )

    results = await _run_concurrent_consumes(
        session_factory,
        settings,
        tenant_id=tenant_id,
        business_id=business_id,
        calls=[
            ("telegram", telegram_conversation),
            ("website_chat", website_conversation),
        ],
    )

    accepted = [item for item in results if item == "accepted"]
    rejected = [item for item in results if isinstance(item, RateLimitExceededError)]
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0].details.scope_type == SCOPE_BUSINESS

    business_count = await _bucket_count(
        session_factory,
        tenant_id=tenant_id,
        business_id=business_id,
        scope_type=SCOPE_BUSINESS,
        scope_key=str(business_id),
        window_start=window_start,
    )
    assert business_count == 1
    assert (
        await _violation_count(
            session_factory, tenant_id=tenant_id, business_id=business_id
        )
        == 1
    )
