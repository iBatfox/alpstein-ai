import logging
import uuid
from contextvars import Token

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.webhook_auth import require_webhook_token
from app.core.observability_context import (
    reset_observability_context,
    set_observability_context,
)
from app.db.session import get_db_session
from app.exceptions import (
    AdapterIngressContainedError,
    BusinessNotFoundError,
    FlowNotFoundError,
    TenantContextError,
)
from app.services.rate_limit_service import RateLimitExceededError
from app.services.spam_protection_service import SpamContainedError, SpamThrottledError
from app.schemas.observability import (
    InvalidCorrelationIdError,
    X_CORRELATION_ID_HEADER,
    X_N8N_EXECUTION_ID_HEADER,
    observability_context_from_webhook,
    resolve_correlation_id,
)
from app.schemas.webhook import NormalizedWebhookMessageRequest
from app.schemas.webhook_response import serialize_webhook_message_success
from app.services.webhook_message_service import WebhookMessageService

logger = logging.getLogger(__name__)

router = APIRouter()
webhook_message_service = WebhookMessageService()


@router.post("/webhook/message", dependencies=[Depends(require_webhook_token)])
async def post_webhook_message(
    body: NormalizedWebhookMessageRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    x_correlation_id: str | None = Header(default=None, alias=X_CORRELATION_ID_HEADER),
    x_n8n_execution_id: str | None = Header(
        default=None,
        alias=X_N8N_EXECUTION_ID_HEADER,
    ),
) -> dict:
    try:
        correlation_id = resolve_correlation_id(
            header_value=x_correlation_id,
            body_value=body.correlation_id,
        )
    except InvalidCorrelationIdError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(exc),
                },
            },
        )

    observability = observability_context_from_webhook(
        body,
        correlation_id=correlation_id,
        n8n_execution_id=x_n8n_execution_id,
    )
    context_token: Token | None = set_observability_context(observability)
    logger.info(
        "webhook message received",
        extra={
            "correlation_id": str(correlation_id),
            "business_external_id": body.business_id,
            "channel": body.channel.value,
        },
    )

    try:
        result = await webhook_message_service.process_incoming_message(
            session,
            body,
            observability=observability,
        )
        await session.commit()
    except BusinessNotFoundError:
        await session.rollback()
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": "BUSINESS_NOT_FOUND",
                    "message": "Business not found",
                },
            },
        )
    except FlowNotFoundError as exc:
        await session.rollback()
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": "FLOW_NOT_FOUND",
                    "message": str(exc),
                },
            },
        )
    except TenantContextError:
        await session.rollback()
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Tenant context is inconsistent",
                },
            },
        )
    except AdapterIngressContainedError as exc:
        await session.rollback()
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "ADAPTER_INGRESS_CONTAINED",
                    "message": "Ingress temporarily not accepted for this adapter",
                },
            },
        )
    except RateLimitExceededError as exc:
        await session.rollback()
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Ingress rate limit exceeded",
                    "metadata": exc.details.to_error_metadata(),
                },
            },
        )
    except SpamThrottledError as exc:
        await session.rollback()
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": {
                    "code": "SPAM_THROTTLED",
                    "message": "Ingress temporarily throttled due to spam protection",
                    "metadata": exc.details.to_error_metadata(),
                },
            },
        )
    except SpamContainedError as exc:
        await session.rollback()
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "error": {
                    "code": "SPAM_CONTAINED",
                    "message": "Ingress temporarily not accepted due to spam protection",
                    "metadata": exc.details.to_error_metadata(),
                },
            },
        )
    finally:
        if context_token is not None:
            reset_observability_context(context_token)

    return serialize_webhook_message_success(
        reply_to_customer=result.reply_to_customer,
        lead_created=result.lead_created,
        lead_updated=result.lead_updated,
        notify_owner=result.notify_owner,
        conversation_id=str(result.conversation.id),
        conversation_status=result.conversation.status,
        message_id=str(result.message.id),
        is_duplicate=result.is_duplicate,
        flow_id=str(result.flow.id),
        flow_key=result.flow.flow_key,
        trace_id=(
            str(result.message_trace_id)
            if isinstance(getattr(result, "message_trace_id", None), uuid.UUID)
            else None
        ),
        correlation_id=(
            str(result.correlation_id)
            if isinstance(getattr(result, "correlation_id", None), uuid.UUID)
            else None
        ),
        processing_status=(
            result.processing_status
            if isinstance(getattr(result, "processing_status", None), str)
            else None
        ),
        delivery_id=(
            str(result.delivery_id)
            if isinstance(getattr(result, "delivery_id", None), uuid.UUID)
            else None
        ),
        delivery_status=(
            result.delivery_status
            if isinstance(getattr(result, "delivery_status", None), str)
            else None
        ),
        outbound_message_id=(
            str(result.outbound_message_id)
            if isinstance(getattr(result, "outbound_message_id", None), uuid.UUID)
            else None
        ),
        instagram_outbound_allowed=getattr(result, "instagram_outbound_allowed", None),
        lead=result.lead,
        notification=result.notification,
    )
