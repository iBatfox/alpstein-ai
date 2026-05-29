import json
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from app.core.config import settings
from app.services.meta_webhook_intake import meta_webhook_log_context

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
async def receive_meta_webhook(request: Request) -> JSONResponse:
    """Accept raw Meta webhook events; no processing or outbound replies yet."""
    raw_body = await request.body()
    if not raw_body or not raw_body.strip():
        return _validation_error("Request body is required")

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        return _validation_error("Request body must be valid JSON")

    if not isinstance(body, dict):
        return _validation_error("Request body must be a JSON object")

    log_context = meta_webhook_log_context(body)
    logger.info("meta webhook event received", extra=log_context)

    return JSONResponse(status_code=200, content={"status": "received"})
