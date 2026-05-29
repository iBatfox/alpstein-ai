"""Map rate limit violations to API responses."""

from __future__ import annotations

from app.models.rate_limit_violation import RateLimitViolation
from app.schemas.rate_limit import RateLimitViolationResponse


def rate_limit_violation_to_response(row: RateLimitViolation) -> RateLimitViolationResponse:
    return RateLimitViolationResponse(
        id=row.id,
        scope_type=row.scope_type,
        scope_key=row.scope_key,
        channel=row.channel,
        conversation_id=row.conversation_id,
        limit_value=row.limit_value,
        window_seconds=row.window_seconds,
        window_start=row.window_start,
        observed_count=row.observed_count,
        correlation_id=row.correlation_id,
        metadata=row.metadata_,
        created_at=row.created_at,
    )
