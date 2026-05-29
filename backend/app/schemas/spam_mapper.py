"""Map spam protection rows to API responses."""

from __future__ import annotations

from app.models.spam_containment import SpamContainment
from app.models.spam_decision import SpamDecision
from app.schemas.spam import SpamContainmentResponse, SpamDecisionResponse


def spam_decision_to_response(row: SpamDecision) -> SpamDecisionResponse:
    return SpamDecisionResponse(
        id=row.id,
        rule_id=row.rule_id,
        scope_type=row.scope_type,
        scope_key=row.scope_key,
        channel=row.channel,
        conversation_id=row.conversation_id,
        decision=row.decision,
        outcome=row.outcome,
        observed_count=row.observed_count,
        threshold=row.threshold,
        window_seconds=row.window_seconds,
        containment_id=row.containment_id,
        correlation_id=row.correlation_id,
        metadata=row.metadata_,
        created_at=row.created_at,
    )


def spam_containment_to_response(row: SpamContainment) -> SpamContainmentResponse:
    return SpamContainmentResponse(
        id=row.id,
        rule_id=row.rule_id,
        scope_type=row.scope_type,
        scope_key=row.scope_key,
        channel=row.channel,
        conversation_id=row.conversation_id,
        action=row.action,
        expires_at=row.expires_at,
        released_at=row.released_at,
        correlation_id=row.correlation_id,
        metadata=row.metadata_,
        created_at=row.created_at,
    )
