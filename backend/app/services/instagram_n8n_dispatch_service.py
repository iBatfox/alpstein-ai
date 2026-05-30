"""Dispatch persisted Instagram ingress events to n8n unified customer ingress."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from app.core.config import Settings, settings
from app.services.instagram_ingress import NormalizedInstagramInboundMessage

logger = logging.getLogger(__name__)

DISPATCH_LOG_STARTED = "instagram_n8n_dispatch_started"
DISPATCH_LOG_SUCCEEDED = "instagram_n8n_dispatch_succeeded"
DISPATCH_LOG_FAILED = "instagram_n8n_dispatch_failed"
DISPATCH_LOG_SKIPPED_DISABLED = "instagram_n8n_dispatch_skipped_disabled"


@dataclass(frozen=True)
class InstagramN8nDispatchContext:
    tenant_id: uuid.UUID
    business_external_id: str
    internal_message_id: uuid.UUID
    normalized: NormalizedInstagramInboundMessage
    correlation_id: uuid.UUID | None = None


class InstagramN8nDispatchService:
    def __init__(
        self,
        *,
        app_settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = app_settings or settings
        self._http_client = http_client

    def is_enabled(self) -> bool:
        return self._settings.instagram_n8n_ingress_enabled

    async def dispatch_persisted_message(
        self,
        context: InstagramN8nDispatchContext,
    ) -> bool:
        if not self.is_enabled():
            logger.info(
                DISPATCH_LOG_SKIPPED_DISABLED,
                extra=_dispatch_log_extra(context, webhook_url=None),
            )
            return False

        webhook_url = self._settings.instagram_n8n_ingress_webhook_url.strip()
        payload = build_instagram_n8n_event_payload(context)
        log_extra = _dispatch_log_extra(context, webhook_url=webhook_url)

        logger.info(DISPATCH_LOG_STARTED, extra=log_extra)

        try:
            if self._http_client is not None:
                response = await self._http_client.post(webhook_url, json=payload)
            else:
                async with httpx.AsyncClient(timeout=self._settings.instagram_n8n_dispatch_timeout_seconds) as client:
                    response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
        except Exception as exc:
            logger.warning(
                DISPATCH_LOG_FAILED,
                extra={
                    **log_extra,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)[:200],
                },
            )
            return False

        logger.info(
            DISPATCH_LOG_SUCCEEDED,
            extra={
                **log_extra,
                "http_status": response.status_code,
            },
        )
        return True


def build_instagram_n8n_event_payload(context: InstagramN8nDispatchContext) -> dict[str, Any]:
    message = context.normalized
    correlation_id = context.correlation_id or uuid.uuid4()
    conversation_id = _external_conversation_id(message.external_chat_id)
    timestamp = _format_timestamp(message.received_at)

    instagram_context = {
        "instagram_user_id": message.external_user_id,
        "instagram_username": None,
        "instagram_display_name": None,
        "instagram_account_id": message.source_account_id,
        "conversation_id": conversation_id,
    }

    return {
        "correlation_id": str(correlation_id),
        "tenant_id": str(context.tenant_id),
        "business_id": context.business_external_id,
        "internal_message_id": str(context.internal_message_id),
        "channel": "instagram",
        "customer": {
            "phone": None,
            "name": None,
            "email": None,
            "external_customer_id": message.external_user_id,
        },
        "message": {
            "text": message.message_text,
            "external_message_id": message.message_id,
            "external_conversation_id": conversation_id,
            "timestamp": timestamp,
            "raw_payload": {
                "platform": message.platform,
                "raw_event_type": message.raw_event_type,
                "source_account_id": message.source_account_id,
                "external_user_id": message.external_user_id,
                "direction": message.direction,
            },
        },
        "instagram_context": instagram_context,
    }


def _dispatch_log_extra(
    context: InstagramN8nDispatchContext,
    *,
    webhook_url: str | None,
) -> dict[str, Any]:
    extra: dict[str, Any] = {
        "tenant_id": str(context.tenant_id),
        "business_id": context.business_external_id,
        "internal_message_id": str(context.internal_message_id),
        "external_message_id": context.normalized.message_id,
        "external_user_id": context.normalized.external_user_id,
        "correlation_id": str(context.correlation_id) if context.correlation_id else None,
    }
    if webhook_url:
        extra["webhook_url"] = webhook_url
    return extra


def _external_conversation_id(external_chat_id: str) -> str:
    prefix = "ig:"
    if external_chat_id.startswith(prefix):
        return external_chat_id
    return f"{prefix}{external_chat_id}"


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.replace(tzinfo=None)
    return value.isoformat(timespec="seconds")


_default_dispatch_service: InstagramN8nDispatchService | None = None


def get_instagram_n8n_dispatch_service() -> InstagramN8nDispatchService:
    global _default_dispatch_service
    if _default_dispatch_service is None:
        _default_dispatch_service = InstagramN8nDispatchService()
    return _default_dispatch_service


def reset_instagram_n8n_dispatch_service_for_tests() -> InstagramN8nDispatchService:
    global _default_dispatch_service
    _default_dispatch_service = InstagramN8nDispatchService()
    return _default_dispatch_service
