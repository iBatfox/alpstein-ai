import logging
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
from app.exceptions import BusinessNotFoundError, FlowNotFoundError, TenantContextError
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
        lead=result.lead,
        notification=result.notification,
    )
