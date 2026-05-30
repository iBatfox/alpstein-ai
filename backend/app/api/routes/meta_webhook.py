import json
import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.services.instagram_ingress import (
    get_instagram_ingress_persistence_service,
    ingress_log_extra,
)
from app.services.instagram_n8n_dispatch_service import (
    InstagramN8nDispatchContext,
    get_instagram_n8n_dispatch_service,
)
from app.services.meta_webhook_intake import (
    instagram_ingress_ignored_log_extra,
    instagram_payload_shape_diagnostic,
    meta_webhook_log_context,
    should_log_instagram_payload_shape,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _validation_error(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message,
            },
        },
    )


@router.get("/meta")
async def verify_meta_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    """Meta webhook verification handshake (WhatsApp Cloud API)."""
    expected_token = settings.meta_verify_token.strip()
    if not expected_token:
        logger.warning("meta webhook verification rejected: META_VERIFY_TOKEN not configured")
        return Response(status_code=403)

    if hub_mode != "subscribe":
        logger.info(
            "meta webhook verification rejected",
            extra={"hub_mode": hub_mode},
        )
        return Response(status_code=403)

    if not hub_verify_token or hub_verify_token != expected_token:
        logger.info("meta webhook verification rejected: verify token mismatch")
        return Response(status_code=403)

    if hub_challenge is None or hub_challenge == "":
        logger.info("meta webhook verification rejected: missing hub.challenge")
        return Response(status_code=403)

    logger.info("meta webhook verification succeeded")
    return PlainTextResponse(content=hub_challenge, status_code=200)


@router.post("/meta")
async def receive_meta_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Accept raw Meta webhook events; Instagram ingress persists inbound DMs only."""
    raw_body = await request.body()
    if not raw_body or not raw_body.strip():
        return _validation_error("Request body is required")

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        return _validation_error("Request body must be valid JSON")

    if not isinstance(body, dict):
        return _validation_error("Request body must be a JSON object")

    if body.get("object") == "instagram":
        persistence = get_instagram_ingress_persistence_service()
        try:
            result = await persistence.process_webhook(session, body)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("instagram ingress persistence failed")
            return JSONResponse(status_code=200, content={"status": "received"})

        for outcome in result.outcomes:
            if outcome.skipped:
                continue
            if outcome.is_duplicate:
                logger.info(
                    "instagram ingress duplicate ignored",
                    extra={"message_ids": [outcome.normalized.message_id]},
                )
                continue
            logger.info(
                "instagram ingress accepted",
                extra={
                    **ingress_log_extra(outcome.normalized),
                    "internal_message_id": str(outcome.internal_message_id),
                },
            )
            if (
                outcome.internal_message_id is not None
                and outcome.tenant_id is not None
                and outcome.business_external_id
            ):
                await get_instagram_n8n_dispatch_service().dispatch_persisted_message(
                    InstagramN8nDispatchContext(
                        tenant_id=outcome.tenant_id,
                        business_external_id=outcome.business_external_id,
                        internal_message_id=outcome.internal_message_id,
                        normalized=outcome.normalized,
                    ),
                )

        if not result.outcomes:
            logger.info(
                "instagram ingress ignored",
                extra=instagram_ingress_ignored_log_extra(
                    body,
                    source_account_id=settings.instagram_user_id.strip(),
                ),
            )

        if should_log_instagram_payload_shape(
            body,
            accepted_count=result.accepted_count,
            duplicate_count=len(result.duplicate_message_ids),
        ):
            shape = instagram_payload_shape_diagnostic(body)
            logger.info(
                "instagram payload shape %s",
                json.dumps(shape, separators=(",", ":")),
            )
    else:
        log_context = meta_webhook_log_context(body)
        logger.info("meta webhook event received", extra=log_context)

    return JSONResponse(status_code=200, content={"status": "received"})
