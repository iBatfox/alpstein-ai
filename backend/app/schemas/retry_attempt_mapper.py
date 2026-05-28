from app.models.retry_attempt import RetryAttempt
from app.schemas.retry_attempt import RetryAttemptResponse


def retry_attempt_to_response(attempt: RetryAttempt) -> RetryAttemptResponse:
    return RetryAttemptResponse(
        id=str(attempt.id),
        tenant_id=str(attempt.tenant_id),
        business_id=str(attempt.business_id),
        scope_type=attempt.scope_type,
        scope_id=str(attempt.scope_id),
        trace_id=str(attempt.trace_id) if attempt.trace_id else None,
        conversation_id=str(attempt.conversation_id) if attempt.conversation_id else None,
        attempt_number=attempt.attempt_number,
        status=attempt.status,
        error_type=attempt.error_type,
        error_message=attempt.error_message,
        correlation_id=attempt.correlation_id,
        metadata=attempt.metadata_,
        created_at=attempt.created_at,
    )
