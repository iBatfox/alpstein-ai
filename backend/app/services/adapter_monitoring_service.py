"""Adapter-level operational health derived from observability tables (E3.3a)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.models.dead_letter_event import DeadLetterEvent
from app.models.delivery_event import (
    DELIVERY_STATUS_DEAD_LETTER,
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_FAILED,
    DELIVERY_STATUS_PENDING,
    DeliveryEvent,
)
from app.models.message_trace import MessageTrace
from app.models.retry_attempt import RETRY_SCOPE_DELIVERY, RETRY_SCOPE_INBOUND, RetryAttempt
from app.services.adapter_health_policy import (
    MONITORED_ADAPTERS,
    AdapterHealthMetrics,
    adapter_health_thresholds,
    evaluate_adapter_status,
    is_monitored_adapter,
)


@dataclass
class AdapterHealthSnapshot:
    adapter: str
    status: str
    status_reasons: list[str]
    recent_messages: int
    delivery_success_count: int
    delivery_failure_count: int
    delivery_pending_count: int
    retry_count: int
    dead_letter_count: int
    delivery_failure_rate: float | None
    last_activity_at: datetime | None
    evaluated_at: datetime
    breakdown: dict[str, Any] | None = None


@dataclass
class _ChannelAccumulator:
    recent_messages: int = 0
    delivery_success_count: int = 0
    delivery_failure_count: int = 0
    delivery_pending_count: int = 0
    retry_count: int = 0
    dead_letter_count: int = 0
    last_activity_at: datetime | None = None
    delivery_by_status: dict[str, int] = field(default_factory=dict)

    def bump_activity(self, value: datetime | None) -> None:
        if value is None:
            return
        if self.last_activity_at is None or value > self.last_activity_at:
            self.last_activity_at = value


class AdapterMonitoringService:
    def __init__(self, app_settings: Settings | None = None) -> None:
        self._settings = app_settings or settings

    def _window_hours(self, window_hours: int | None) -> int:
        if window_hours is None:
            return self._settings.adapter_monitor_window_hours
        return max(1, min(window_hours, 168))

    def _window_start(self, *, window_hours: int) -> datetime:
        return datetime.utcnow() - timedelta(hours=window_hours)

    async def list_adapters(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        window_hours: int | None = None,
    ) -> tuple[int, list[AdapterHealthSnapshot]]:
        hours = self._window_hours(window_hours)
        snapshots = await self._build_snapshots(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            window_hours=hours,
            include_breakdown=False,
        )
        return hours, snapshots

    async def get_adapter(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        adapter: str,
        window_hours: int | None = None,
    ) -> AdapterHealthSnapshot | None:
        if not is_monitored_adapter(adapter):
            return None
        hours = self._window_hours(window_hours)
        snapshots = await self._build_snapshots(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            window_hours=hours,
            include_breakdown=True,
            adapters=(adapter,),
        )
        return snapshots[0] if snapshots else None

    async def _build_snapshots(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        window_hours: int,
        include_breakdown: bool,
        adapters: tuple[str, ...] | None = None,
    ) -> list[AdapterHealthSnapshot]:
        adapter_keys = adapters or MONITORED_ADAPTERS
        window_start = self._window_start(window_hours=window_hours)
        evaluated_at = datetime.utcnow()
        accumulators = {key: _ChannelAccumulator() for key in adapter_keys}

        await self._load_trace_metrics(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            window_start=window_start,
            accumulators=accumulators,
        )
        await self._load_delivery_metrics(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            window_start=window_start,
            accumulators=accumulators,
        )
        await self._load_retry_metrics(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            window_start=window_start,
            accumulators=accumulators,
        )
        await self._load_dead_letter_metrics(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            window_start=window_start,
            accumulators=accumulators,
        )

        thresholds = adapter_health_thresholds(self._settings)
        snapshots: list[AdapterHealthSnapshot] = []
        for adapter in adapter_keys:
            acc = accumulators[adapter]
            metrics = AdapterHealthMetrics(
                adapter=adapter,
                recent_messages=acc.recent_messages,
                delivery_success_count=acc.delivery_success_count,
                delivery_failure_count=acc.delivery_failure_count,
                delivery_pending_count=acc.delivery_pending_count,
                retry_count=acc.retry_count,
                dead_letter_count=acc.dead_letter_count,
            )
            status, reasons, failure_rate = evaluate_adapter_status(metrics, thresholds)
            breakdown = None
            if include_breakdown:
                breakdown = {"delivery_by_status": dict(sorted(acc.delivery_by_status.items()))}
            snapshots.append(
                AdapterHealthSnapshot(
                    adapter=adapter,
                    status=status,
                    status_reasons=reasons,
                    recent_messages=acc.recent_messages,
                    delivery_success_count=acc.delivery_success_count,
                    delivery_failure_count=acc.delivery_failure_count,
                    delivery_pending_count=acc.delivery_pending_count,
                    retry_count=acc.retry_count,
                    dead_letter_count=acc.dead_letter_count,
                    delivery_failure_rate=failure_rate,
                    last_activity_at=acc.last_activity_at,
                    evaluated_at=evaluated_at,
                    breakdown=breakdown,
                )
            )
        return snapshots

    async def _load_trace_metrics(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        window_start: datetime,
        accumulators: dict[str, _ChannelAccumulator],
    ) -> None:
        stmt = (
            select(
                MessageTrace.channel,
                func.count().label("count"),
                func.max(MessageTrace.created_at).label("last_at"),
            )
            .where(
                MessageTrace.tenant_id == tenant_id,
                MessageTrace.business_id == business_id,
                MessageTrace.channel.in_(tuple(accumulators.keys())),
                MessageTrace.created_at >= window_start,
            )
            .group_by(MessageTrace.channel)
        )
        result = await session.execute(stmt)
        for channel, count, last_at in result.all():
            acc = accumulators[channel]
            acc.recent_messages = int(count)
            acc.bump_activity(last_at)

    async def _load_delivery_metrics(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        window_start: datetime,
        accumulators: dict[str, _ChannelAccumulator],
    ) -> None:
        stmt = (
            select(
                DeliveryEvent.channel,
                DeliveryEvent.status,
                func.count().label("count"),
                func.max(DeliveryEvent.updated_at).label("last_at"),
            )
            .where(
                DeliveryEvent.tenant_id == tenant_id,
                DeliveryEvent.business_id == business_id,
                DeliveryEvent.channel.in_(tuple(accumulators.keys())),
                DeliveryEvent.created_at >= window_start,
            )
            .group_by(DeliveryEvent.channel, DeliveryEvent.status)
        )
        result = await session.execute(stmt)
        for channel, status, count, last_at in result.all():
            acc = accumulators[channel]
            acc.bump_activity(last_at)
            acc.delivery_by_status[status] = int(count)
            if status == DELIVERY_STATUS_DELIVERED:
                acc.delivery_success_count += int(count)
            elif status in (DELIVERY_STATUS_FAILED, DELIVERY_STATUS_DEAD_LETTER):
                acc.delivery_failure_count += int(count)
            elif status == DELIVERY_STATUS_PENDING:
                acc.delivery_pending_count += int(count)

    async def _load_retry_metrics(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        window_start: datetime,
        accumulators: dict[str, _ChannelAccumulator],
    ) -> None:
        delivery_stmt = (
            select(
                DeliveryEvent.channel,
                func.count().label("count"),
            )
            .select_from(RetryAttempt)
            .join(
                DeliveryEvent,
                and_(
                    RetryAttempt.scope_type == RETRY_SCOPE_DELIVERY,
                    RetryAttempt.scope_id == DeliveryEvent.id,
                ),
            )
            .where(
                RetryAttempt.tenant_id == tenant_id,
                RetryAttempt.business_id == business_id,
                RetryAttempt.created_at >= window_start,
                DeliveryEvent.channel.in_(tuple(accumulators.keys())),
            )
            .group_by(DeliveryEvent.channel)
        )
        delivery_result = await session.execute(delivery_stmt)
        for channel, count in delivery_result.all():
            accumulators[channel].retry_count += int(count)

        inbound_stmt = (
            select(
                MessageTrace.channel,
                func.count().label("count"),
            )
            .select_from(RetryAttempt)
            .join(
                MessageTrace,
                RetryAttempt.trace_id == MessageTrace.id,
            )
            .where(
                RetryAttempt.tenant_id == tenant_id,
                RetryAttempt.business_id == business_id,
                RetryAttempt.scope_type == RETRY_SCOPE_INBOUND,
                RetryAttempt.created_at >= window_start,
                MessageTrace.channel.in_(tuple(accumulators.keys())),
            )
            .group_by(MessageTrace.channel)
        )
        inbound_result = await session.execute(inbound_stmt)
        for channel, count in inbound_result.all():
            accumulators[channel].retry_count += int(count)

    async def _load_dead_letter_metrics(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        window_start: datetime,
        accumulators: dict[str, _ChannelAccumulator],
    ) -> None:
        window_filter = or_(
            DeadLetterEvent.created_at >= window_start,
            DeadLetterEvent.last_seen_at >= window_start,
        )
        delivery_stmt = (
            select(
                DeliveryEvent.channel,
                func.count().label("count"),
            )
            .select_from(DeadLetterEvent)
            .join(
                DeliveryEvent,
                DeadLetterEvent.delivery_id == DeliveryEvent.id,
            )
            .where(
                DeadLetterEvent.tenant_id == tenant_id,
                DeadLetterEvent.business_id == business_id,
                DeliveryEvent.channel.in_(tuple(accumulators.keys())),
                window_filter,
            )
            .group_by(DeliveryEvent.channel)
        )
        delivery_result = await session.execute(delivery_stmt)
        for channel, count in delivery_result.all():
            accumulators[channel].dead_letter_count += int(count)

        inbound_stmt = (
            select(
                MessageTrace.channel,
                func.count().label("count"),
            )
            .select_from(DeadLetterEvent)
            .join(
                MessageTrace,
                DeadLetterEvent.trace_id == MessageTrace.id,
            )
            .where(
                DeadLetterEvent.tenant_id == tenant_id,
                DeadLetterEvent.business_id == business_id,
                DeadLetterEvent.delivery_id.is_(None),
                MessageTrace.channel.in_(tuple(accumulators.keys())),
                window_filter,
            )
            .group_by(MessageTrace.channel)
        )
        inbound_result = await session.execute(inbound_stmt)
        for channel, count in inbound_result.all():
            accumulators[channel].dead_letter_count += int(count)
