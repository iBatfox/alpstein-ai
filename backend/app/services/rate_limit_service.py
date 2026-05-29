"""Ingress rate limiting enforcement (E3.5b)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.db.session import AsyncSessionLocal
from app.models.rate_limit_bucket import RateLimitBucket
from app.models.rate_limit_violation import RateLimitViolation
from app.services.rate_limit_policy import (
    RateLimitScopeDefinition,
    build_rate_limit_scopes,
    compute_window_start,
    pick_violation_scope,
    rate_limit_policy_config,
    retry_after_seconds,
)

FORBIDDEN_VIOLATION_METADATA_KEYS = frozenset(
    {
        "raw_payload",
        "provider_payload",
        "api_key",
        "secret",
        "bot_token",
        "password",
        "message_text",
        "prompt",
    }
)


@dataclass(frozen=True)
class RateLimitExceededDetails:
    scope_type: str
    scope_key: str
    adapter: str | None
    limit: int
    window_seconds: int
    window_start: datetime
    observed_count: int
    retry_after_seconds: int

    def to_error_metadata(self) -> dict[str, Any]:
        return {
            "scope_type": self.scope_type,
            "scope_key": self.scope_key,
            "adapter": self.adapter,
            "retry_after_seconds": self.retry_after_seconds,
            "window_seconds": self.window_seconds,
            "limit": self.limit,
            "current_count": self.observed_count,
        }


class RateLimitExceededError(Exception):
    def __init__(self, details: RateLimitExceededDetails) -> None:
        self.details = details
        super().__init__("Ingress rate limit exceeded")


class RateLimitService:
    def __init__(self, app_settings: Settings | None = None) -> None:
        self._settings = app_settings or settings

    async def consume_ingress_request(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
        conversation_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> None:
        if not self._settings.rate_limit_enabled:
            return

        now = datetime.utcnow()
        policy = rate_limit_policy_config(self._settings)
        scopes = build_rate_limit_scopes(
            tenant_id=str(tenant_id),
            business_id=str(business_id),
            channel=channel,
            conversation_id=str(conversation_id),
            policy=policy,
        )
        window_start = compute_window_start(now=now, window_seconds=policy.window_seconds)

        buckets: list[tuple[RateLimitScopeDefinition, RateLimitBucket]] = []
        for scope in scopes:
            bucket = await self._get_or_create_bucket(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                scope=scope,
                window_start=window_start,
                now=now,
            )
            buckets.append((scope, bucket))

        exceeded: list[tuple[RateLimitScopeDefinition, int]] = []
        for scope, bucket in buckets:
            if bucket.request_count >= scope.limit:
                exceeded.append((scope, bucket.request_count))

        if exceeded:
            violation_scope, observed_count = pick_violation_scope(exceeded)
            details = RateLimitExceededDetails(
                scope_type=violation_scope.scope_type,
                scope_key=violation_scope.scope_key,
                adapter=violation_scope.channel,
                limit=violation_scope.limit,
                window_seconds=violation_scope.window_seconds,
                window_start=window_start,
                observed_count=observed_count,
                retry_after_seconds=retry_after_seconds(
                    now=now,
                    window_start=window_start,
                    window_seconds=violation_scope.window_seconds,
                ),
            )
            await self._record_violation(
                tenant_id=tenant_id,
                business_id=business_id,
                conversation_id=conversation_id,
                details=details,
                correlation_id=correlation_id,
            )
            raise RateLimitExceededError(details)

        for _, bucket in buckets:
            bucket.request_count += 1
        await session.flush()

    async def _get_or_create_bucket(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        scope: RateLimitScopeDefinition,
        window_start: datetime,
        now: datetime,
    ) -> RateLimitBucket:
        stmt = (
            select(RateLimitBucket)
            .where(
                RateLimitBucket.tenant_id == tenant_id,
                RateLimitBucket.business_id == business_id,
                RateLimitBucket.scope_type == scope.scope_type,
                RateLimitBucket.scope_key == scope.scope_key,
                RateLimitBucket.window_start == window_start,
            )
            .with_for_update()
        )
        result = await session.execute(stmt)
        bucket = result.scalar_one_or_none()
        if bucket is not None:
            return bucket

        bucket = RateLimitBucket(
            tenant_id=tenant_id,
            business_id=business_id,
            scope_type=scope.scope_type,
            scope_key=scope.scope_key,
            channel=scope.channel,
            window_start=window_start,
            window_seconds=scope.window_seconds,
            request_count=0,
            created_at=now,
            updated_at=now,
        )
        session.add(bucket)
        await session.flush()
        locked = await session.execute(stmt)
        existing = locked.scalar_one_or_none()
        return existing if existing is not None else bucket

    async def _record_violation(
        self,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        details: RateLimitExceededDetails,
        correlation_id: str | None,
    ) -> RateLimitViolation:
        row = RateLimitViolation(
            tenant_id=tenant_id,
            business_id=business_id,
            scope_type=details.scope_type,
            scope_key=details.scope_key,
            channel=details.adapter,
            conversation_id=conversation_id,
            limit_value=details.limit,
            window_seconds=details.window_seconds,
            window_start=details.window_start,
            observed_count=details.observed_count,
            correlation_id=correlation_id,
            metadata_=sanitize_violation_metadata(details.to_error_metadata()),
            created_at=datetime.utcnow(),
        )
        async with AsyncSessionLocal() as isolated_session:
            isolated_session.add(row)
            await isolated_session.commit()
        return row

    async def list_violations(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str | None = None,
        scope_type: str | None = None,
        conversation_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[RateLimitViolation]:
        stmt = (
            select(RateLimitViolation)
            .where(
                RateLimitViolation.tenant_id == tenant_id,
                RateLimitViolation.business_id == business_id,
            )
            .order_by(RateLimitViolation.created_at.desc())
            .limit(min(limit, 100))
            .offset(offset)
        )
        if channel is not None:
            stmt = stmt.where(RateLimitViolation.channel == channel)
        if scope_type is not None:
            stmt = stmt.where(RateLimitViolation.scope_type == scope_type)
        if conversation_id is not None:
            stmt = stmt.where(RateLimitViolation.conversation_id == conversation_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_violations_for_channel(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
        since: datetime,
    ) -> int:
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(RateLimitViolation)
            .where(
                RateLimitViolation.tenant_id == tenant_id,
                RateLimitViolation.business_id == business_id,
                RateLimitViolation.channel == channel,
                RateLimitViolation.created_at >= since,
            )
        )
        result = await session.execute(stmt)
        return int(result.scalar_one())


def sanitize_violation_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    cleaned = {
        key: value
        for key, value in metadata.items()
        if key not in FORBIDDEN_VIOLATION_METADATA_KEYS
    }
    return cleaned or None
