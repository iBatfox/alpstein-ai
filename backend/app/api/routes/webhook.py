from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.webhook_auth import require_webhook_token
from app.db.session import get_db_session
from app.exceptions import BusinessNotFoundError, TenantContextError
from app.schemas.webhook import NormalizedWebhookMessageRequest
from app.schemas.webhook_response import serialize_webhook_message_success
from app.services.webhook_message_service import WebhookMessageService

router = APIRouter()
webhook_message_service = WebhookMessageService()


@router.post("/webhook/message", dependencies=[Depends(require_webhook_token)])
async def post_webhook_message(
    body: NormalizedWebhookMessageRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        result = await webhook_message_service.process_incoming_message(session, body)
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

    return serialize_webhook_message_success(
        reply_to_customer=result.reply_to_customer,
        lead_created=result.lead_created,
        lead_updated=result.lead_updated,
        notify_owner=result.notify_owner,
        conversation_id=str(result.conversation.id),
        conversation_status=result.conversation.status,
        message_id=str(result.message.id),
        is_duplicate=result.is_duplicate,
        lead=result.lead,
        notification=result.notification,
    )
