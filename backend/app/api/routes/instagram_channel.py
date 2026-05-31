"""Instagram channel outbound routes (n8n → backend → Meta Send API)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.webhook_auth import require_webhook_token
from app.db.session import get_db_session
from app.schemas.instagram_outbound import (
    InstagramSendMessageRequest,
    InstagramSendMessageResponse,
)
from app.services.instagram_client import InstagramClientError
from app.services.instagram_outbound_service import (
    OUTBOUND_STATUS_SKIPPED,
    InstagramOutboundDisabledError,
    InstagramOutboundService,
    to_response_data,
)

logger = logging.getLogger(__name__)

router = APIRouter()
instagram_outbound_service = InstagramOutboundService()


@router.post(
    "/channels/instagram/send-message",
    dependencies=[Depends(require_webhook_token)],
)
async def post_instagram_send_message(
    body: InstagramSendMessageRequest,
    session: AsyncSession = Depends(get_db_session),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-Id"),
    x_n8n_execution_id: str | None = Header(default=None, alias="X-N8n-Execution-Id"),
) -> dict:
    _ = x_correlation_id, x_n8n_execution_id

    try:
        result = await instagram_outbound_service.send_customer_reply(session, body)
    except InstagramOutboundDisabledError:
        return JSONResponse(
            status_code=403,
            content=InstagramSendMessageResponse(
                success=False,
                error={
                    "code": InstagramOutboundDisabledError.code,
                    "message": "Instagram outbound send is disabled",
                },
            ).model_dump(),
        )
    except InstagramClientError as exc:
        await session.rollback()
        return JSONResponse(
            status_code=502,
            content=InstagramSendMessageResponse(
                success=False,
                error={
                    "code": exc.code,
                    "message": str(exc),
                },
            ).model_dump(),
        )

    if result.status == OUTBOUND_STATUS_SKIPPED:
        return InstagramSendMessageResponse(
            success=True,
            data=to_response_data(result),
        ).model_dump(exclude_none=True)

    return InstagramSendMessageResponse(
        success=True,
        data=to_response_data(result),
    ).model_dump(exclude_none=True)


def validation_error_response(exc: ValidationError) -> JSONResponse:
    message = "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
        for error in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content=InstagramSendMessageResponse(
            success=False,
            error={
                "code": "VALIDATION_ERROR",
                "message": message,
            },
        ).model_dump(),
    )
