"""Spam protection enforcement and audit (E3.6b / E3.6c)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.db.session import AsyncSessionLocal
from app.models.replay_event import REPLAY_EVENT_REPLAY_IGNORED, ReplayEvent
from app.models.spam_containment import (
    ACTION_TEMPORARY_BLOCK,
    ACTION_THROTTLE,
    SpamContainment,
)
from app.models.spam_decision import (
    DECISION_IGNORE,
    DECISION_MARK_SUSPICIOUS,
    DECISION_TEMPORARY_BLOCK,
    DECISION_THROTTLE,
    OUTCOME_ALREADY_CONTAINED,
    OUTCOME_APPLIED,
    OUTCOME_PASSED,
    SpamDecision,
)
from app.models.spam_indicator_bucket import SCOPE_ADAPTER, SCOPE_CONVERSATION, SpamIndicatorBucket
from app.services.rate_limit_policy import compute_window_start, retry_after_seconds
from app.services.spam_payload_fingerprint import compute_payload_hash, payload_hash_prefix
from app.services.spam_policy import (
    BLOCKING_DECISIONS,
    MONITORED_SPAM_CHANNELS,
    RULE_ADAPTER_FANOUT,
    RULE_CONVERSATION_BURST,
    RULE_PAYLOAD_REPEAT,
    RULE_REPLAY_STORM,
    RULE_RETRY_ABUSE,
    SCOPE_SPECIFICITY_ORDER,
    SpamRuleDefinition,
    containment_action_for_decision,
    effective_decision,
    spam_policy_config,
)

FORBIDDEN_SPAM_METADATA_KEYS = frozenset(
    {
        "raw_payload",
        "provider_payload",
        "api_key",
        "secret",
        "bot_token",
        "password",
        "message_text",
        "prompt",
        "system_prompt",
    }
)


@dataclass(frozen=True)
class SpamEnforcementDetails:
    rule_id: str
    decision: str
    scope_type: str
    scope_key: str
    adapter: str | None
    observed_count: int
    threshold: int
    window_seconds: int
    retry_after_seconds: int

    def to_error_metadata(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "decision": self.decision,
            "scope_type": self.scope_type,
            "scope_key": self.scope_key,
            "adapter": self.adapter,
            "retry_after_seconds": self.retry_after_seconds,
            "window_seconds": self.window_seconds,
            "observed_count": self.observed_count,
            "threshold": self.threshold,
        }


class SpamThrottledError(Exception):
    def __init__(self, details: SpamEnforcementDetails) -> None:
        self.details = details
        super().__init__("Ingress throttled by spam protection")


class SpamContainedError(Exception):
    def __init__(self, details: SpamEnforcementDetails) -> None:
        self.details = details
        super().__init__("Ingress contained by spam protection")


@dataclass(frozen=True)
class _RuleEvaluation:
    rule: SpamRuleDefinition
    observed_count: int
    scope_key: str
    channel: str | None
    conversation_id: uuid.UUID | None
    metadata: dict[str, Any]


class SpamProtectionService:
    def __init__(self, app_settings: Settings | None = None) -> None:
        self._settings = app_settings or settings

    async def evaluate_ingress_request(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
        conversation_id: uuid.UUID,
        message_text: str,
        correlation_id: str | None = None,
    ) -> None:
        if not self._settings.spam_protection_enabled:
            return
        if channel not in MONITORED_SPAM_CHANNELS:
            return

        now = datetime.utcnow()
        policy = spam_policy_config(self._settings)
        payload_hash = compute_payload_hash(message_text)

        active = await self._find_active_containment(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            channel=channel,
            conversation_id=conversation_id,
            now=now,
        )
        if active is not None and not policy.production_safe_mode:
            details = self._details_from_containment(active, now=now)
            await self._record_decision_isolated(
                tenant_id=tenant_id,
                business_id=business_id,
                rule_id=active.rule_id,
                scope_type=active.scope_type,
                scope_key=active.scope_key,
                channel=active.channel,
                conversation_id=active.conversation_id,
                decision=DECISION_THROTTLE
                if active.action == ACTION_THROTTLE
                else DECISION_TEMPORARY_BLOCK,
                outcome=OUTCOME_ALREADY_CONTAINED,
                observed_count=None,
                threshold=None,
                window_seconds=None,
                containment_id=active.id,
                correlation_id=correlation_id,
                metadata=active.metadata_,
            )
            self._raise_for_containment(active.action, details)

        triggered: list[_RuleEvaluation] = []
        for rule in policy.rules:
            if not rule.enabled or rule.threshold <= 0:
                continue
            configured = effective_decision(
                rule.configured_action,
                production_safe_mode=policy.production_safe_mode,
            )
            if configured == DECISION_IGNORE:
                continue

            evaluation = await self._evaluate_rule(
                session,
                rule=rule,
                tenant_id=tenant_id,
                business_id=business_id,
                channel=channel,
                conversation_id=conversation_id,
                payload_hash=payload_hash,
                now=now,
            )
            if evaluation is None:
                continue
            if evaluation.observed_count >= rule.threshold:
                triggered.append(evaluation)

        if not triggered:
            return

        triggered.sort(
            key=lambda item: SCOPE_SPECIFICITY_ORDER.index(item.rule.scope_type)
            if item.rule.scope_type in SCOPE_SPECIFICITY_ORDER
            else 99
        )
        hit = triggered[0]
        decision = effective_decision(
            hit.rule.configured_action,
            production_safe_mode=policy.production_safe_mode,
        )

        safe_metadata = sanitize_spam_metadata(
            {
                **hit.metadata,
                "payload_hash_prefix": payload_hash_prefix(payload_hash),
                "observed_count": hit.observed_count,
                "threshold": hit.rule.threshold,
                "window_seconds": hit.rule.window_seconds,
            }
        )

        if decision == DECISION_MARK_SUSPICIOUS:
            await self._record_decision_isolated(
                tenant_id=tenant_id,
                business_id=business_id,
                rule_id=hit.rule.rule_id,
                scope_type=hit.rule.scope_type,
                scope_key=hit.scope_key,
                channel=hit.channel,
                conversation_id=hit.conversation_id,
                decision=decision,
                outcome=OUTCOME_APPLIED,
                observed_count=hit.observed_count,
                threshold=hit.rule.threshold,
                window_seconds=hit.rule.window_seconds,
                containment_id=None,
                correlation_id=correlation_id,
                metadata=safe_metadata,
            )
            return

        containment_action = containment_action_for_decision(decision)
        if containment_action is None:
            return

        expires_at = now + timedelta(
            seconds=(
                policy.throttle_ttl_seconds
                if containment_action == ACTION_THROTTLE
                else policy.block_ttl_seconds
            )
        )
        containment = await self._apply_containment(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            rule_id=hit.rule.rule_id,
            scope_type=hit.rule.scope_type,
            scope_key=hit.scope_key,
            channel=hit.channel,
            conversation_id=hit.conversation_id,
            action=containment_action,
            expires_at=expires_at,
            correlation_id=correlation_id,
            metadata=safe_metadata,
        )
        details = SpamEnforcementDetails(
            rule_id=hit.rule.rule_id,
            decision=decision,
            scope_type=hit.rule.scope_type,
            scope_key=hit.scope_key,
            adapter=hit.channel,
            observed_count=hit.observed_count,
            threshold=hit.rule.threshold,
            window_seconds=hit.rule.window_seconds,
            retry_after_seconds=max(
                1,
                int((containment.expires_at - now).total_seconds()),
            ),
        )
        await self._record_decision_isolated(
            tenant_id=tenant_id,
            business_id=business_id,
            rule_id=hit.rule.rule_id,
            scope_type=hit.rule.scope_type,
            scope_key=hit.scope_key,
            channel=hit.channel,
            conversation_id=hit.conversation_id,
            decision=decision,
            outcome=OUTCOME_APPLIED,
            observed_count=hit.observed_count,
            threshold=hit.rule.threshold,
            window_seconds=hit.rule.window_seconds,
            containment_id=containment.id,
            correlation_id=correlation_id,
            metadata=safe_metadata,
        )
        self._raise_for_containment(containment_action, details)

    async def _evaluate_rule(
        self,
        session: AsyncSession,
        *,
        rule: SpamRuleDefinition,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
        conversation_id: uuid.UUID,
        payload_hash: str,
        now: datetime,
    ) -> _RuleEvaluation | None:
        window_start = compute_window_start(now=now, window_seconds=rule.window_seconds)

        if rule.rule_id == RULE_PAYLOAD_REPEAT:
            scope_key = f"{conversation_id}:{payload_hash}"
            count = await self._increment_bucket(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                rule_id=rule.rule_id,
                scope_type=SCOPE_CONVERSATION,
                scope_key=scope_key,
                channel=channel,
                window_start=window_start,
                window_seconds=rule.window_seconds,
                now=now,
            )
            return _RuleEvaluation(
                rule=rule,
                observed_count=count,
                scope_key=scope_key,
                channel=channel,
                conversation_id=conversation_id,
                metadata={"payload_hash_prefix": payload_hash_prefix(payload_hash)},
            )

        if rule.rule_id == RULE_CONVERSATION_BURST:
            scope_key = str(conversation_id)
            count = await self._increment_bucket(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                rule_id=rule.rule_id,
                scope_type=SCOPE_CONVERSATION,
                scope_key=scope_key,
                channel=channel,
                window_start=window_start,
                window_seconds=rule.window_seconds,
                now=now,
            )
            return _RuleEvaluation(
                rule=rule,
                observed_count=count,
                scope_key=scope_key,
                channel=channel,
                conversation_id=conversation_id,
                metadata={},
            )

        if rule.rule_id == RULE_ADAPTER_FANOUT:
            scope_key = f"{business_id}:{channel}:{conversation_id}"
            await self._increment_bucket(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                rule_id=rule.rule_id,
                scope_type=SCOPE_ADAPTER,
                scope_key=scope_key,
                channel=channel,
                window_start=window_start,
                window_seconds=rule.window_seconds,
                now=now,
                cap_at_one=True,
            )
            count = await self._count_adapter_fanout_buckets(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                channel=channel,
                window_start=window_start,
            )
            return _RuleEvaluation(
                rule=rule,
                observed_count=count,
                scope_key=f"{business_id}:{channel}",
                channel=channel,
                conversation_id=None,
                metadata={},
            )

        if rule.rule_id == RULE_RETRY_ABUSE:
            count = await self._count_replay_events(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                conversation_id=conversation_id,
                since=now - timedelta(seconds=rule.window_seconds),
            )
            return _RuleEvaluation(
                rule=rule,
                observed_count=count,
                scope_key=str(conversation_id),
                channel=channel,
                conversation_id=conversation_id,
                metadata={},
            )

        if rule.rule_id == RULE_REPLAY_STORM:
            count = await self._count_replay_ignored_for_channel(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                channel=channel,
                since=now - timedelta(seconds=rule.window_seconds),
            )
            return _RuleEvaluation(
                rule=rule,
                observed_count=count,
                scope_key=f"{business_id}:{channel}",
                channel=channel,
                conversation_id=None,
                metadata={},
            )

        return None

    async def _increment_bucket(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        rule_id: str,
        scope_type: str,
        scope_key: str,
        channel: str | None,
        window_start: datetime,
        window_seconds: int,
        now: datetime,
        cap_at_one: bool = False,
    ) -> int:
        stmt = (
            select(SpamIndicatorBucket)
            .where(
                SpamIndicatorBucket.tenant_id == tenant_id,
                SpamIndicatorBucket.business_id == business_id,
                SpamIndicatorBucket.rule_id == rule_id,
                SpamIndicatorBucket.scope_type == scope_type,
                SpamIndicatorBucket.scope_key == scope_key,
                SpamIndicatorBucket.window_start == window_start,
            )
            .with_for_update()
        )
        result = await session.execute(stmt)
        bucket = result.scalar_one_or_none()
        if bucket is None:
            bucket = SpamIndicatorBucket(
                tenant_id=tenant_id,
                business_id=business_id,
                rule_id=rule_id,
                scope_type=scope_type,
                scope_key=scope_key,
                channel=channel,
                window_start=window_start,
                window_seconds=window_seconds,
                signal_count=1,
                created_at=now,
                updated_at=now,
            )
            session.add(bucket)
            await session.flush()
            return 1

        if cap_at_one:
            return bucket.signal_count
        bucket.signal_count += 1
        bucket.updated_at = now
        await session.flush()
        return bucket.signal_count

    async def _count_adapter_fanout_buckets(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
        window_start: datetime,
    ) -> int:
        prefix = f"{business_id}:{channel}:"
        stmt = (
            select(func.count())
            .select_from(SpamIndicatorBucket)
            .where(
                SpamIndicatorBucket.tenant_id == tenant_id,
                SpamIndicatorBucket.business_id == business_id,
                SpamIndicatorBucket.rule_id == RULE_ADAPTER_FANOUT,
                SpamIndicatorBucket.scope_type == SCOPE_ADAPTER,
                SpamIndicatorBucket.window_start == window_start,
                SpamIndicatorBucket.scope_key.like(f"{prefix}%"),
            )
        )
        result = await session.execute(stmt)
        return int(result.scalar_one())

    async def _count_replay_events(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        since: datetime,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(ReplayEvent)
            .where(
                ReplayEvent.tenant_id == tenant_id,
                ReplayEvent.business_id == business_id,
                ReplayEvent.conversation_id == conversation_id,
                ReplayEvent.created_at >= since,
            )
        )
        result = await session.execute(stmt)
        return int(result.scalar_one())

    async def _count_replay_ignored_for_channel(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
        since: datetime,
    ) -> int:
        from app.models.message_trace import MessageTrace

        stmt = (
            select(func.count())
            .select_from(ReplayEvent)
            .join(MessageTrace, ReplayEvent.trace_id == MessageTrace.id)
            .where(
                ReplayEvent.tenant_id == tenant_id,
                ReplayEvent.business_id == business_id,
                ReplayEvent.event_type == REPLAY_EVENT_REPLAY_IGNORED,
                ReplayEvent.created_at >= since,
                MessageTrace.channel == channel,
            )
        )
        result = await session.execute(stmt)
        return int(result.scalar_one())

    async def _find_active_containment(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
        conversation_id: uuid.UUID,
        now: datetime,
    ) -> SpamContainment | None:
        scopes = [
            (SCOPE_CONVERSATION, str(conversation_id)),
            (SCOPE_ADAPTER, f"{business_id}:{channel}"),
            ("business", str(business_id)),
        ]
        scope_filters = [
            and_(
                SpamContainment.scope_type == scope_type,
                SpamContainment.scope_key == scope_key,
            )
            for scope_type, scope_key in scopes
        ]
        stmt = (
            select(SpamContainment)
            .where(
                SpamContainment.tenant_id == tenant_id,
                SpamContainment.business_id == business_id,
                SpamContainment.released_at.is_(None),
                SpamContainment.expires_at > now,
                or_(*scope_filters),
            )
            .order_by(SpamContainment.created_at.desc())
        )
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        if not rows:
            return None
        rows.sort(
            key=lambda row: SCOPE_SPECIFICITY_ORDER.index(row.scope_type)
            if row.scope_type in SCOPE_SPECIFICITY_ORDER
            else 99
        )
        return rows[0]

    async def _apply_containment(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        rule_id: str,
        scope_type: str,
        scope_key: str,
        channel: str | None,
        conversation_id: uuid.UUID | None,
        action: str,
        expires_at: datetime,
        correlation_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> SpamContainment:
        existing = await session.execute(
            select(SpamContainment)
            .where(
                SpamContainment.tenant_id == tenant_id,
                SpamContainment.business_id == business_id,
                SpamContainment.scope_type == scope_type,
                SpamContainment.scope_key == scope_key,
                SpamContainment.rule_id == rule_id,
                SpamContainment.released_at.is_(None),
            )
            .with_for_update()
        )
        row = existing.scalar_one_or_none()
        if row is not None:
            row.expires_at = max(row.expires_at, expires_at)
            row.action = action
            row.metadata_ = metadata
            row.correlation_id = correlation_id
            await session.flush()
            return row

        containment = SpamContainment(
            tenant_id=tenant_id,
            business_id=business_id,
            rule_id=rule_id,
            scope_type=scope_type,
            scope_key=scope_key,
            channel=channel,
            conversation_id=conversation_id,
            action=action,
            expires_at=expires_at,
            correlation_id=correlation_id,
            metadata_=metadata,
            created_at=datetime.utcnow(),
        )
        session.add(containment)
        await session.flush()
        return containment

    async def _record_decision_isolated(
        self,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        rule_id: str,
        scope_type: str,
        scope_key: str,
        channel: str | None,
        conversation_id: uuid.UUID | None,
        decision: str,
        outcome: str,
        observed_count: int | None,
        threshold: int | None,
        window_seconds: int | None,
        containment_id: uuid.UUID | None,
        correlation_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> SpamDecision:
        row = SpamDecision(
            tenant_id=tenant_id,
            business_id=business_id,
            rule_id=rule_id,
            scope_type=scope_type,
            scope_key=scope_key,
            channel=channel,
            conversation_id=conversation_id,
            decision=decision,
            outcome=outcome,
            observed_count=observed_count,
            threshold=threshold,
            window_seconds=window_seconds,
            containment_id=containment_id,
            correlation_id=correlation_id,
            metadata_=metadata,
            created_at=datetime.utcnow(),
        )
        async with AsyncSessionLocal() as isolated:
            isolated.add(row)
            await isolated.commit()
        return row

    async def list_decisions(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str | None = None,
        rule_id: str | None = None,
        conversation_id: uuid.UUID | None = None,
        decision: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SpamDecision]:
        stmt = (
            select(SpamDecision)
            .where(
                SpamDecision.tenant_id == tenant_id,
                SpamDecision.business_id == business_id,
            )
            .order_by(SpamDecision.created_at.desc())
            .limit(min(limit, 100))
            .offset(offset)
        )
        if channel is not None:
            stmt = stmt.where(SpamDecision.channel == channel)
        if rule_id is not None:
            stmt = stmt.where(SpamDecision.rule_id == rule_id)
        if conversation_id is not None:
            stmt = stmt.where(SpamDecision.conversation_id == conversation_id)
        if decision is not None:
            stmt = stmt.where(SpamDecision.decision == decision)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def list_containments(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str | None = None,
        scope_type: str | None = None,
        active_only: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SpamContainment]:
        now = datetime.utcnow()
        stmt = (
            select(SpamContainment)
            .where(
                SpamContainment.tenant_id == tenant_id,
                SpamContainment.business_id == business_id,
            )
            .order_by(SpamContainment.created_at.desc())
            .limit(min(limit, 100))
            .offset(offset)
        )
        if channel is not None:
            stmt = stmt.where(SpamContainment.channel == channel)
        if scope_type is not None:
            stmt = stmt.where(SpamContainment.scope_type == scope_type)
        if active_only:
            stmt = stmt.where(
                SpamContainment.released_at.is_(None),
                SpamContainment.expires_at > now,
            )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_decisions_for_channel(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
        since: datetime,
        suspicious_only: bool = True,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(SpamDecision)
            .where(
                SpamDecision.tenant_id == tenant_id,
                SpamDecision.business_id == business_id,
                SpamDecision.channel == channel,
                SpamDecision.created_at >= since,
            )
        )
        if suspicious_only:
            stmt = stmt.where(SpamDecision.decision != "allow")
        result = await session.execute(stmt)
        return int(result.scalar_one())

    async def count_active_containments_for_channel(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        channel: str,
        now: datetime | None = None,
    ) -> int:
        current = now or datetime.utcnow()
        stmt = (
            select(func.count())
            .select_from(SpamContainment)
            .where(
                SpamContainment.tenant_id == tenant_id,
                SpamContainment.business_id == business_id,
                SpamContainment.channel == channel,
                SpamContainment.released_at.is_(None),
                SpamContainment.expires_at > current,
            )
        )
        result = await session.execute(stmt)
        return int(result.scalar_one())

    def _details_from_containment(
        self,
        containment: SpamContainment,
        *,
        now: datetime,
    ) -> SpamEnforcementDetails:
        metadata = containment.metadata_ or {}
        return SpamEnforcementDetails(
            rule_id=containment.rule_id,
            decision=DECISION_THROTTLE
            if containment.action == ACTION_THROTTLE
            else DECISION_TEMPORARY_BLOCK,
            scope_type=containment.scope_type,
            scope_key=containment.scope_key,
            adapter=containment.channel,
            observed_count=int(metadata.get("observed_count", 0)),
            threshold=int(metadata.get("threshold", 0)),
            window_seconds=int(metadata.get("window_seconds", 0)),
            retry_after_seconds=max(
                1,
                int((containment.expires_at - now).total_seconds()),
            ),
        )

    @staticmethod
    def _raise_for_containment(action: str, details: SpamEnforcementDetails) -> None:
        if action == ACTION_THROTTLE:
            raise SpamThrottledError(details)
        raise SpamContainedError(details)


def sanitize_spam_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    cleaned = {
        key: value
        for key, value in metadata.items()
        if key not in FORBIDDEN_SPAM_METADATA_KEYS
    }
    return cleaned or None
