"""Adapter-level operational health derived from observability tables (E3.3a / E3.4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.models.dead_letter_event import DL_SCOPE_INBOUND, DeadLetterEvent
from app.models.delivery_event import (
    DELIVERY_STATUS_DEAD_LETTER,
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_FAILED,
    DELIVERY_STATUS_PENDING,
    DeliveryEvent,
)
from app.models.message_trace import TRACE_STATUS_FAILED, MessageTrace
from app.models.retry_attempt import RETRY_SCOPE_DELIVERY, RETRY_SCOPE_INBOUND, RetryAttempt
from app.services.adapter_health_policy import (
    MONITORED_ADAPTERS,
    adapter_health_thresholds,
    is_monitored_adapter,
)
from app.services.ingress_isolation_policy import (
    AdapterIsolationView,
    IngressHealthMetrics,
    IsolationSummary,
    build_isolation_summary,
    combine_adapter_status,
    compute_spread_risk,
    evaluate_containment_status,
    evaluate_delivery_status,
    evaluate_ingress_status,
    ingress_health_thresholds,
    should_reject_ingress,
)


@dataclass
class PeerAdapterSnapshot:
    adapter: str
    status: str
    ingress_status: str
    delivery_status: str
    containment_status: str


@dataclass
class AdapterHealthSnapshot:
    adapter: str
    status: str
    status_reasons: list[str]
    ingress_status: str
    delivery_status: str
    ingress_status_reasons: list[str]
    delivery_status_reasons: list[str]
    containment_status: str
    recent_messages: int
    ingress_failed_count: int
    ingress_retry_count: int
    ingress_dead_letter_count: int
    delivery_success_count: int
    delivery_failure_count: int
    delivery_pending_count: int
    retry_count: int
    dead_letter_count: int
    delivery_failure_rate: float | None
    last_activity_at: datetime | None
    evaluated_at: datetime
    breakdown: dict[str, Any] | None = None
    peer_adapter: PeerAdapterSnapshot | None = None


@dataclass
class _ChannelAccumulator:
    recent_messages: int = 0
    ingress_failed_count: int = 0
    ingress_retry_count: int = 0
    ingress_dead_letter_count: int = 0
    delivery_success_count: int = 0
    delivery_failure_count: int = 0
    delivery_pending_count: int = 0
    delivery_retry_count: int = 0
    delivery_dead_letter_count: int = 0
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
    ) -> tuple[int, list[AdapterHealthSnapshot], IsolationSummary]:
        hours = self._window_hours(window_hours)
        snapshots, summary = await self._build_snapshots(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            window_hours=hours,
            include_breakdown=False,
        )
        return hours, snapshots, summary

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
        snapshots, _ = await self._build_snapshots(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            window_hours=hours,
            include_breakdown=True,
            adapters=MONITORED_ADAPTERS,
        )
        by_adapter = {item.adapter: item for item in snapshots}
        target = by_adapter.get(adapter)
        if target is None:
            return None
        peer_key = _peer_adapter(adapter)
        peer = by_adapter.get(peer_key)
        if peer is not None:
            target.peer_adapter = PeerAdapterSnapshot(
                adapter=peer.adapter,
                status=peer.status,
                ingress_status=peer.ingress_status,
                delivery_status=peer.delivery_status,
                containment_status=peer.containment_status,
            )
        return target

    async def should_reject_ingress_for_channel(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
    ) -> bool:
        if not self._settings.ingress_containment_enabled:
            return False
        if not is_monitored_adapter(channel):
            return False
        snapshot = await self.get_adapter(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            adapter=channel,
        )
        if snapshot is None:
            return False
        return should_reject_ingress(
            channel=channel,
            ingress_containment_enabled=self._settings.ingress_containment_enabled,
            ingress_dead_letter_count=snapshot.ingress_dead_letter_count,
            containment_status=snapshot.containment_status,
        )

    async def _build_snapshots(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        window_hours: int,
        include_breakdown: bool,
        adapters: tuple[str, ...] | None = None,
    ) -> tuple[list[AdapterHealthSnapshot], IsolationSummary]:
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

        delivery_thresholds = adapter_health_thresholds(self._settings)
        ingress_thresholds = ingress_health_thresholds(self._settings)

        partial_views: list[AdapterIsolationView] = []
        snapshots_by_adapter: dict[str, AdapterHealthSnapshot] = {}

        for adapter in adapter_keys:
            acc = accumulators[adapter]
            ingress_metrics = IngressHealthMetrics(
                adapter=adapter,
                ingress_recent_messages=acc.recent_messages,
                ingress_failed_count=acc.ingress_failed_count,
                ingress_retry_count=acc.inbound_retry_count,
                ingress_dead_letter_count=acc.inbound_dead_letter_count,
            )
            ingress_status, ingress_reasons = evaluate_ingress_status(
                ingress_metrics,
                ingress_thresholds,
            )
            delivery_status, delivery_reasons, failure_rate = evaluate_delivery_status(
                recent_messages=acc.recent_messages,
                delivery_success_count=acc.delivery_success_count,
                delivery_failure_count=acc.delivery_failure_count,
                delivery_pending_count=acc.delivery_pending_count,
                delivery_retry_count=acc.delivery_retry_count,
                delivery_dead_letter_count=acc.delivery_dead_letter_count,
                thresholds=delivery_thresholds,
            )
            combined_status = combine_adapter_status(ingress_status, delivery_status)
            combined_reasons = sorted(set(ingress_reasons + delivery_reasons))
            breakdown = None
            if include_breakdown:
                breakdown = {"delivery_by_status": dict(sorted(acc.delivery_by_status.items()))}

            view = AdapterIsolationView(
                adapter=adapter,
                ingress_status=ingress_status,
                delivery_status=delivery_status,
                status=combined_status,
                ingress_status_reasons=list(ingress_reasons),
                delivery_status_reasons=list(delivery_reasons),
                containment_status="normal",
                ingress_failed_count=acc.ingress_failed_count,
                ingress_dead_letter_count=acc.inbound_dead_letter_count,
            )
            partial_views.append(view)
            snapshots_by_adapter[adapter] = AdapterHealthSnapshot(
                adapter=adapter,
                status=combined_status,
                status_reasons=combined_reasons,
                ingress_status=ingress_status,
                delivery_status=delivery_status,
                ingress_status_reasons=list(ingress_reasons),
                delivery_status_reasons=list(delivery_reasons),
                containment_status="normal",
                recent_messages=acc.recent_messages,
                ingress_failed_count=acc.ingress_failed_count,
                ingress_retry_count=acc.inbound_retry_count,
                ingress_dead_letter_count=acc.inbound_dead_letter_count,
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

        spread_risk = compute_spread_risk(partial_views)
        status_by_adapter = {view.adapter: view.status for view in partial_views}

        final_views: list[AdapterIsolationView] = []
        for view in partial_views:
            peer_key = _peer_adapter(view.adapter)
            peer_status = status_by_adapter.get(peer_key) if peer_key else None
            containment = evaluate_containment_status(
                adapter=view.adapter,
                adapter_status=view.status,
                peer_status=peer_status,
                spread_risk=spread_risk,
            )
            final_views.append(
                AdapterIsolationView(
                    adapter=view.adapter,
                    ingress_status=view.ingress_status,
                    delivery_status=view.delivery_status,
                    status=view.status,
                    ingress_status_reasons=view.ingress_status_reasons,
                    delivery_status_reasons=view.delivery_status_reasons,
                    containment_status=containment,
                    ingress_failed_count=view.ingress_failed_count,
                    ingress_dead_letter_count=view.ingress_dead_letter_count,
                )
            )
            snapshots_by_adapter[view.adapter].containment_status = containment

        summary = build_isolation_summary(final_views)
        ordered = [snapshots_by_adapter[key] for key in adapter_keys if key in snapshots_by_adapter]
        return ordered, summary

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

        failed_stmt = (
            select(
                MessageTrace.channel,
                func.count().label("count"),
            )
            .where(
                MessageTrace.tenant_id == tenant_id,
                MessageTrace.business_id == business_id,
                MessageTrace.channel.in_(tuple(accumulators.keys())),
                MessageTrace.created_at >= window_start,
                MessageTrace.status == TRACE_STATUS_FAILED,
            )
            .group_by(MessageTrace.channel)
        )
        failed_result = await session.execute(failed_stmt)
        for channel, count in failed_result.all():
            accumulators[channel].ingress_failed_count = int(count)

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
            acc = accumulators[channel]
            acc.delivery_retry_count += int(count)
            acc.retry_count += int(count)

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
            acc = accumulators[channel]
            acc.inbound_retry_count += int(count)
            acc.retry_count += int(count)

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
            acc = accumulators[channel]
            acc.delivery_dead_letter_count += int(count)
            acc.dead_letter_count += int(count)

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
                DeadLetterEvent.scope_type == DL_SCOPE_INBOUND,
                MessageTrace.channel.in_(tuple(accumulators.keys())),
                window_filter,
            )
            .group_by(MessageTrace.channel)
        )
        inbound_result = await session.execute(inbound_stmt)
        for channel, count in inbound_result.all():
            acc = accumulators[channel]
            acc.inbound_dead_letter_count += int(count)
            acc.dead_letter_count += int(count)


def _peer_adapter(adapter: str) -> str | None:
    if adapter == "telegram":
        return "website_chat"
    if adapter == "website_chat":
        return "telegram"
    return None
