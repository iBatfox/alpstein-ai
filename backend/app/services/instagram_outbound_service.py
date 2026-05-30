"""Instagram outbound DM send for n8n channel delivery (T-IG-OUTBOUND-REPLY)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import Settings, settings
from app.schemas.instagram_outbound import (
    InstagramSendMessageData,
    InstagramSendMessageRequest,
)
from app.services.instagram_client import (
    InstagramClientError,
    InstagramGraphClient,
    InstagramSendResult,
)

logger = logging.getLogger(__name__)

LOG_STARTED = "instagram_outbound_send_started"
LOG_SUCCEEDED = "instagram_outbound_send_succeeded"
LOG_FAILED = "instagram_outbound_send_failed"
LOG_SKIPPED_DISABLED = "instagram_outbound_send_skipped_disabled"


class InstagramOutboundDisabledError(Exception):
    code = "INSTAGRAM_OUTBOUND_DISABLED"

    def __init__(self) -> None:
        super().__init__("Instagram outbound send is disabled")


@dataclass(frozen=True)
class InstagramOutboundSendResult:
    provider_message_id: str
    status: str = "sent"


class InstagramOutboundService:
    def __init__(
        self,
        *,
        app_settings: Settings | None = None,
        graph_client: InstagramGraphClient | None = None,
    ) -> None:
        self._settings = app_settings or settings
        self._graph_client = graph_client or InstagramGraphClient(
            app_settings=self._settings,
        )

    def is_enabled(self) -> bool:
        return self._settings.instagram_outbound_enabled

    def send_customer_reply(
        self,
        request: InstagramSendMessageRequest,
    ) -> InstagramOutboundSendResult:
        log_extra = _log_extra(request)

        if not self.is_enabled():
            logger.info(LOG_SKIPPED_DISABLED, extra=log_extra)
            raise InstagramOutboundDisabledError()

        logger.info(LOG_STARTED, extra=log_extra)

        try:
            send_result = self._graph_client.send_message(
                request.recipient_id,
                request.message_text,
                messaging_type="RESPONSE",
            )
        except InstagramClientError as exc:
            logger.warning(
                LOG_FAILED,
                extra={
                    **log_extra,
                    "error_code": exc.code,
                    "error_message": str(exc)[:200],
                },
            )
            raise

        logger.info(
            LOG_SUCCEEDED,
            extra={
                **log_extra,
                "provider_message_id": send_result.message_id,
            },
        )
        return _map_send_result(send_result)


def _map_send_result(result: InstagramSendResult) -> InstagramOutboundSendResult:
    return InstagramOutboundSendResult(
        provider_message_id=result.message_id,
        status="sent",
    )


def to_response_data(result: InstagramOutboundSendResult) -> InstagramSendMessageData:
    return InstagramSendMessageData(
        provider_message_id=result.provider_message_id,
        status=result.status,
    )


def _log_extra(request: InstagramSendMessageRequest) -> dict[str, str | None]:
    text = request.message_text.strip()
    preview = text[:80] + ("..." if len(text) > 80 else "")
    return {
        "business_id": request.business_id,
        "recipient_id": request.recipient_id,
        "correlation_id": request.correlation_id,
        "external_inbound_message_id": request.external_inbound_message_id,
        "message_text_length": str(len(text)),
        "message_text_preview": preview,
    }
