"""Instagram DM ingress — parse Meta webhooks and persist inbound messages."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.services.business_service import BusinessService
from app.services.conversation_service import ConversationService
from app.services.customer_service import CustomerService
from app.services.flow_service import FlowService
from app.services.instagram_account_resolver import (
    INSTAGRAM_CHANNEL,
    InstagramAccountResolverService,
    ResolvedInstagramAccount,
)
from app.services.message_service import MessageService
from app.services.meta_webhook_intake import (
    InstagramInboundMessage,
    extract_instagram_inbound_messages,
    safe_message_text_for_log,
)

logger = logging.getLogger(__name__)

PLATFORM_INSTAGRAM = "instagram"
DIRECTION_INBOUND = "inbound"
INSTAGRAM_CONVERSATION_ID_PREFIX = "ig:"
SKIP_REASON_MISSING_ACCOUNT_MAPPING = "missing_account_mapping"


@dataclass(frozen=True)
class NormalizedInstagramInboundMessage:
    platform: str
    external_user_id: str
    external_chat_id: str
    message_id: str
    message_text: str
    direction: str
    received_at: datetime
    raw_event_type: str
    source_account_id: str


@dataclass(frozen=True)
class InstagramIngressParseResult:
    messages: tuple[NormalizedInstagramInboundMessage, ...]


@dataclass(frozen=True)
class InstagramIngressPersistOutcome:
    normalized: NormalizedInstagramInboundMessage
    persisted: bool
    is_duplicate: bool
    skipped: bool
    skip_reason: str | None = None
    internal_message_id: uuid.UUID | None = None


@dataclass(frozen=True)
class InstagramIngressProcessResult:
    outcomes: tuple[InstagramIngressPersistOutcome, ...]

    @property
    def accepted_count(self) -> int:
        return sum(
            1
            for outcome in self.outcomes
            if outcome.persisted and not outcome.is_duplicate and not outcome.skipped
        )

    @property
    def duplicate_message_ids(self) -> tuple[str, ...]:
        return tuple(
            outcome.normalized.message_id
            for outcome in self.outcomes
            if outcome.is_duplicate
        )

    @property
    def skipped_count(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.skipped)


class InstagramIngressService:
    """Parse Instagram webhook payloads into normalized inbound messages."""

    def __init__(self, *, app_settings: Settings | None = None) -> None:
        self._settings = app_settings or settings

    def parse_meta_webhook(self, body: dict[str, Any]) -> InstagramIngressParseResult:
        if body.get("object") != PLATFORM_INSTAGRAM:
            return InstagramIngressParseResult(())

        source_account_id = self._settings.instagram_user_id.strip()
        messages = tuple(
            _normalize_inbound_message(parsed, source_account_id)
            for parsed in extract_instagram_inbound_messages(body)
        )
        return InstagramIngressParseResult(messages)


class InstagramIngressPersistenceService:
    """Persist normalized Instagram inbound messages via canonical message services."""

    def __init__(
        self,
        *,
        ingress_service: InstagramIngressService | None = None,
        account_resolver: InstagramAccountResolverService | None = None,
        business_service: BusinessService | None = None,
        flow_service: FlowService | None = None,
        customer_service: CustomerService | None = None,
        conversation_service: ConversationService | None = None,
        message_service: MessageService | None = None,
    ) -> None:
        self._ingress_service = ingress_service or InstagramIngressService()
        self._account_resolver = account_resolver or InstagramAccountResolverService()
        self._business_service = business_service or BusinessService()
        self._flow_service = flow_service or FlowService()
        self._customer_service = customer_service or CustomerService()
        self._conversation_service = conversation_service or ConversationService()
        self._message_service = message_service or MessageService()

    async def process_webhook(
        self,
        session: AsyncSession,
        body: dict[str, Any],
    ) -> InstagramIngressProcessResult:
        parsed = self._ingress_service.parse_meta_webhook(body)
        outcomes: list[InstagramIngressPersistOutcome] = []
        for message in parsed.messages:
            outcomes.append(await self._persist_message(session, message))
        return InstagramIngressProcessResult(tuple(outcomes))

    async def _persist_message(
        self,
        session: AsyncSession,
        message: NormalizedInstagramInboundMessage,
    ) -> InstagramIngressPersistOutcome:
        account = await self._account_resolver.resolve_by_source_account_id(
            session,
            message.source_account_id,
        )
        if account is None:
            logger.warning(
                "instagram ingress skipped: account mapping not found",
                extra={
                    "platform": message.platform,
                    "source_account_id": message.source_account_id,
                    "external_user_id": message.external_user_id,
                    "message_id": message.message_id,
                    "skip_reason": SKIP_REASON_MISSING_ACCOUNT_MAPPING,
                },
            )
            return InstagramIngressPersistOutcome(
                normalized=message,
                persisted=False,
                is_duplicate=False,
                skipped=True,
                skip_reason=SKIP_REASON_MISSING_ACCOUNT_MAPPING,
            )

        business = await self._business_service.get_by_external_id(
            session,
            account.business_external_id,
        )
        if business.id != account.business_id or business.tenant_id != account.tenant_id:
            logger.warning(
                "instagram ingress skipped: resolved business mismatch",
                extra={
                    "source_account_id": message.source_account_id,
                    "message_id": message.message_id,
                    "skip_reason": SKIP_REASON_MISSING_ACCOUNT_MAPPING,
                },
            )
            return InstagramIngressPersistOutcome(
                normalized=message,
                persisted=False,
                is_duplicate=False,
                skipped=True,
                skip_reason=SKIP_REASON_MISSING_ACCOUNT_MAPPING,
            )

        flow = await self._flow_service.resolve_for_webhook(
            session,
            tenant_id=business.tenant_id,
            business_id=business.id,
            flow_key=None,
        )
        customer = await self._customer_service.get_or_create_customer(
            session,
            tenant_id=business.tenant_id,
            business_id=business.id,
            source_channel=INSTAGRAM_CHANNEL,
            external_customer_id=message.external_user_id,
        )
        external_conversation_id = _external_conversation_id(message.external_chat_id)
        conversation = await self._conversation_service.get_or_create_open_conversation(
            session,
            tenant_id=business.tenant_id,
            business_id=business.id,
            flow_id=flow.id,
            customer_id=customer.id,
            channel=INSTAGRAM_CHANNEL,
            external_conversation_id=external_conversation_id,
        )
        save_result = await self._message_service.save_incoming_customer_message(
            session,
            tenant_id=business.tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            message_text=message.message_text,
            channel=INSTAGRAM_CHANNEL,
            external_message_id=message.message_id,
            raw_payload=_ingress_raw_payload(message),
            flow_id=flow.id,
            message_timestamp=message.received_at,
        )
        conversation.last_message_at = message.received_at
        await session.flush()

        return InstagramIngressPersistOutcome(
            normalized=message,
            persisted=True,
            is_duplicate=save_result.is_duplicate,
            skipped=False,
            internal_message_id=save_result.message.id,
        )


def ingress_log_extra(message: NormalizedInstagramInboundMessage) -> dict[str, Any]:
    """Safe structured log fields for accepted Instagram ingress messages."""
    extra: dict[str, Any] = {
        "platform": message.platform,
        "external_user_id": message.external_user_id,
        "external_chat_id": message.external_chat_id,
        "message_id": message.message_id,
        "message_text": safe_message_text_for_log(message.message_text),
        "direction": message.direction,
        "raw_event_type": message.raw_event_type,
        "source_account_id": message.source_account_id,
        "received_at": message.received_at.isoformat(),
    }
    if len(message.message_text) > 200:
        extra["message_text_length"] = len(message.message_text)
    return extra


def _normalize_inbound_message(
    parsed: InstagramInboundMessage,
    source_account_id: str,
) -> NormalizedInstagramInboundMessage:
    return NormalizedInstagramInboundMessage(
        platform=PLATFORM_INSTAGRAM,
        external_user_id=parsed.sender_id,
        external_chat_id=parsed.sender_id,
        message_id=parsed.message_id,
        message_text=parsed.message_text,
        direction=DIRECTION_INBOUND,
        received_at=_resolve_received_at(parsed.event_timestamp),
        raw_event_type=parsed.raw_event_type or "instagram.inbound",
        source_account_id=source_account_id,
    )


def _resolve_received_at(event_timestamp: str | None) -> datetime:
    """Return naive UTC for TIMESTAMP WITHOUT TIME ZONE columns."""
    if event_timestamp and event_timestamp.isdigit():
        return datetime.fromtimestamp(int(event_timestamp), tz=UTC).replace(tzinfo=None)
    return datetime.now(tz=UTC).replace(tzinfo=None)


def _external_conversation_id(external_chat_id: str) -> str:
    if external_chat_id.startswith(INSTAGRAM_CONVERSATION_ID_PREFIX):
        return external_chat_id
    return f"{INSTAGRAM_CONVERSATION_ID_PREFIX}{external_chat_id}"


def _ingress_raw_payload(message: NormalizedInstagramInboundMessage) -> dict[str, Any]:
    return {
        "platform": message.platform,
        "raw_event_type": message.raw_event_type,
        "source_account_id": message.source_account_id,
        "external_user_id": message.external_user_id,
        "direction": message.direction,
    }


_default_ingress_service: InstagramIngressService | None = None
_default_persistence_service: InstagramIngressPersistenceService | None = None


def get_instagram_ingress_service() -> InstagramIngressService:
    global _default_ingress_service
    if _default_ingress_service is None:
        _default_ingress_service = InstagramIngressService()
    return _default_ingress_service


def get_instagram_ingress_persistence_service() -> InstagramIngressPersistenceService:
    global _default_persistence_service
    if _default_persistence_service is None:
        _default_persistence_service = InstagramIngressPersistenceService(
            ingress_service=get_instagram_ingress_service(),
        )
    return _default_persistence_service


def reset_instagram_ingress_services_for_tests() -> InstagramIngressPersistenceService:
    """Replace process-wide ingress services (tests only)."""
    global _default_ingress_service, _default_persistence_service
    _default_ingress_service = InstagramIngressService()
    _default_persistence_service = InstagramIngressPersistenceService(
        ingress_service=_default_ingress_service,
    )
    return _default_persistence_service
