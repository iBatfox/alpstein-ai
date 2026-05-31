"""Instagram outbound DM send for n8n channel delivery (T-IG-OUTBOUND-REPLY)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

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
from app.services.instagram_outbound_dedup_service import InstagramOutboundDedupService

logger = logging.getLogger(__name__)

LOG_STARTED = "instagram_outbound_send_started"
LOG_SUCCEEDED = "instagram_outbound_send_succeeded"
LOG_FAILED = "instagram_outbound_send_failed"
LOG_SKIPPED_DISABLED = "instagram_outbound_send_skipped_disabled"
LOG_SKIPPED_DUPLICATE = "instagram_outbound_send_skipped_duplicate"

INSTAGRAM_OUTBOUND_DUPLICATE_SKIPPED = "INSTAGRAM_OUTBOUND_DUPLICATE_SKIPPED"
OUTBOUND_STATUS_SENT = "sent"
OUTBOUND_STATUS_SKIPPED = "skipped"


class InstagramOutboundDisabledError(Exception):
    code = "INSTAGRAM_OUTBOUND_DISABLED"

    def __init__(self) -> None:
        super().__init__("Instagram outbound send is disabled")


@dataclass(frozen=True)
class InstagramOutboundSendResult:
    provider_message_id: str | None
    status: str = OUTBOUND_STATUS_SENT
    skip_code: str | None = None


class InstagramOutboundService:
    def __init__(
        self,
        *,
        app_settings: Settings | None = None,
        graph_client: InstagramGraphClient | None = None,
        dedup_service: InstagramOutboundDedupService | None = None,
    ) -> None:
        self._settings = app_settings or settings
        self._graph_client = graph_client or InstagramGraphClient(
            app_settings=self._settings,
        )
        self._dedup_service = dedup_service or InstagramOutboundDedupService()

    def is_enabled(self) -> bool:
        return self._settings.instagram_outbound_enabled

    async def send_customer_reply(
        self,
        session: AsyncSession,
        request: InstagramSendMessageRequest,
    ) -> InstagramOutboundSendResult:
        log_extra = _log_extra(request)

        if not self.is_enabled():
            logger.info(LOG_SKIPPED_DISABLED, extra=log_extra)
            raise InstagramOutboundDisabledError()

        acquired = await self._dedup_service.try_acquire_send_slot(
            session,
            business_external_id=request.business_id,
            external_inbound_message_id=request.external_inbound_message_id,
        )
        if not acquired:
            logger.info(LOG_SKIPPED_DUPLICATE, extra=log_extra)
            return InstagramOutboundSendResult(
                provider_message_id=None,
                status=OUTBOUND_STATUS_SKIPPED,
                skip_code=INSTAGRAM_OUTBOUND_DUPLICATE_SKIPPED,
            )

        logger.info(LOG_STARTED, extra=log_extra)

        try:
            send_result = self._graph_client.send_message(
                request.recipient_id,
                request.message_text,
                messaging_type="RESPONSE",
            )
        except InstagramClientError as exc:
            await self._dedup_service.release_send_slot(
                session,
                business_external_id=request.business_id,
                external_inbound_message_id=request.external_inbound_message_id,
            )
            logger.warning(
                "%s error_code=%s error_message=%s",
                LOG_FAILED,
                exc.code,
                str(exc)[:300],
                extra={
                    **log_extra,
                    "error_code": exc.code,
                    "error_message": str(exc)[:300],
                },
            )
            raise

        mapped = _map_send_result(send_result)
        await self._dedup_service.record_provider_message_id(
            session,
            business_external_id=request.business_id,
            external_inbound_message_id=request.external_inbound_message_id,
            provider_message_id=mapped.provider_message_id or "",
        )
        await session.commit()

        logger.info(
            LOG_SUCCEEDED,
            extra={
                **log_extra,
                "provider_message_id": mapped.provider_message_id,
            },
        )
        return mapped


def _map_send_result(result: InstagramSendResult) -> InstagramOutboundSendResult:
    return InstagramOutboundSendResult(
        provider_message_id=result.message_id,
        status=OUTBOUND_STATUS_SENT,
    )


def to_response_data(result: InstagramOutboundSendResult) -> InstagramSendMessageData:
    return InstagramSendMessageData(
        provider_message_id=result.provider_message_id,
        status=result.status,
        skip_code=result.skip_code,
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
