import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import desc, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.schemas.conversation_context import (
    ConversationHistory,
    ConversationHistoryMessage,
)
from app.services.message_idempotency import (
    build_inbound_idempotency_key,
    normalize_external_message_id,
)
from app.services.tenant_context_validator import validate_tenant_context

CONVERSATION_HISTORY_MIN_LIMIT = 10
CONVERSATION_HISTORY_MAX_LIMIT = 20
CONVERSATION_HISTORY_DEFAULT_LIMIT = CONVERSATION_HISTORY_MAX_LIMIT

INCOMING_CUSTOMER_SENDER = "customer"
INCOMING_DIRECTION = "incoming"


@dataclass(frozen=True)
class IncomingMessageSaveResult:
    message: Message
    is_duplicate: bool


class MessageService:
    async def find_inbound_customer_message(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        external_message_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Message | None:
        normalized_external_id = normalize_external_message_id(external_message_id)
        if normalized_external_id is None and not idempotency_key:
            return None

        conditions = [
            Message.tenant_id == tenant_id,
            Message.business_id == business_id,
            Message.conversation_id == conversation_id,
            Message.sender_type == INCOMING_CUSTOMER_SENDER,
            Message.direction == INCOMING_DIRECTION,
        ]
        dedup_match = []
        if normalized_external_id is not None:
            dedup_match.append(Message.external_message_id == normalized_external_id)
        if idempotency_key:
            dedup_match.append(Message.idempotency_key == idempotency_key)
        if not dedup_match:
            return None

        result = await session.execute(
            select(Message).where(*conditions, or_(*dedup_match)).limit(1)
        )
        return result.scalar_one_or_none()

    async def find_by_external_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        external_message_id: str | None,
        *,
        conversation_id: uuid.UUID | None = None,
    ) -> Message | None:
        """Backward-compatible lookup; prefers conversation-scoped inbound dedup when set."""
        if external_message_id is None:
            return None

        if conversation_id is not None:
            return await self.find_inbound_customer_message(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                conversation_id=conversation_id,
                external_message_id=external_message_id,
            )

        result = await session.execute(
            select(Message)
            .where(
                Message.tenant_id == tenant_id,
                Message.business_id == business_id,
                Message.external_message_id == external_message_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save_incoming_customer_message(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business: object,
        conversation: object,
        message_text: str,
        channel: str | None = None,
        customer: object | None = None,
        external_message_id: str | None = None,
        raw_payload: dict[str, Any] | None = None,
        flow_id: uuid.UUID | None = None,
        message_timestamp: datetime | None = None,
        idempotency_key: str | None = None,
    ) -> IncomingMessageSaveResult:
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            flow_id=flow_id,
        )

        resolved_flow_id = flow_id or getattr(conversation, "flow_id", None)
        if resolved_flow_id is None:
            raise ValueError("flow_id is required for inbound message deduplication")

        resolved_channel = channel if channel is not None else conversation.channel
        stored_external_id = normalize_external_message_id(external_message_id)
        resolved_idempotency_key = idempotency_key or build_inbound_idempotency_key(
            business_id=business.id,
            flow_id=resolved_flow_id,
            conversation_id=conversation.id,
            channel=resolved_channel,
            external_message_id=stored_external_id,
            message_text=message_text,
            message_timestamp=message_timestamp,
        )

        existing = await self.find_inbound_customer_message(
            session,
            tenant_id=tenant_id,
            business_id=business.id,
            conversation_id=conversation.id,
            external_message_id=stored_external_id,
            idempotency_key=resolved_idempotency_key,
        )
        if existing is not None:
            return IncomingMessageSaveResult(message=existing, is_duplicate=True)

        message = Message(
            tenant_id=tenant_id,
            business_id=business.id,
            conversation_id=conversation.id,
            sender_type=INCOMING_CUSTOMER_SENDER,
            direction=INCOMING_DIRECTION,
            channel=resolved_channel,
            message_text=message_text,
            message_type="text",
            external_message_id=stored_external_id,
            idempotency_key=resolved_idempotency_key,
            raw_payload=raw_payload,
        )
        session.add(message)

        try:
            async with session.begin_nested():
                await session.flush()
        except IntegrityError:
            existing = await self.find_inbound_customer_message(
                session,
                tenant_id=tenant_id,
                business_id=business.id,
                conversation_id=conversation.id,
                external_message_id=stored_external_id,
                idempotency_key=resolved_idempotency_key,
            )
            if existing is None:
                raise
            return IncomingMessageSaveResult(message=existing, is_duplicate=True)

        return IncomingMessageSaveResult(message=message, is_duplicate=False)

    async def save_outgoing_ai_message(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business: object,
        conversation: object,
        message_text: str,
        channel: str | None = None,
        ai_metadata: dict[str, Any] | None = None,
        customer: object | None = None,
        flow_id: uuid.UUID | None = None,
    ) -> Message:
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
            flow_id=flow_id,
        )

        resolved_channel = channel if channel is not None else conversation.channel
        message = Message(
            tenant_id=tenant_id,
            business_id=business.id,
            conversation_id=conversation.id,
            sender_type="ai",
            direction="outgoing",
            channel=resolved_channel,
            message_text=message_text,
            message_type="text",
            external_message_id=None,
            idempotency_key=None,
            raw_payload=None,
            ai_metadata=ai_metadata,
        )
        session.add(message)
        await session.flush()
        return message

    async def find_last_outgoing_ai_message(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Message | None:
        result = await session.execute(
            select(Message)
            .where(
                Message.tenant_id == tenant_id,
                Message.business_id == business_id,
                Message.conversation_id == conversation_id,
                Message.sender_type == "ai",
                Message.direction == "outgoing",
            )
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def find_outgoing_ai_for_inbound(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        inbound_message_id: uuid.UUID,
    ) -> Message | None:
        """Return the AI outbound message linked to a specific inbound message, if any."""
        from app.models.message_trace import MessageTrace

        trace_result = await session.execute(
            select(MessageTrace.outbound_message_id)
            .where(
                MessageTrace.tenant_id == tenant_id,
                MessageTrace.business_id == business_id,
                MessageTrace.inbound_message_id == inbound_message_id,
                MessageTrace.outbound_message_id.is_not(None),
            )
            .limit(1)
        )
        outbound_id = trace_result.scalar_one_or_none()
        if outbound_id is None:
            return None

        message_result = await session.execute(
            select(Message).where(
                Message.tenant_id == tenant_id,
                Message.business_id == business_id,
                Message.id == outbound_id,
                Message.sender_type == "ai",
                Message.direction == "outgoing",
            )
        )
        return message_result.scalar_one_or_none()

    async def load_recent_conversation_history(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        limit: int = CONVERSATION_HISTORY_DEFAULT_LIMIT,
    ) -> ConversationHistory:
        bounded_limit = _normalize_history_limit(limit)

        result = await session.execute(
            select(Message)
            .where(
                Message.tenant_id == tenant_id,
                Message.business_id == business_id,
                Message.conversation_id == conversation_id,
            )
            .order_by(desc(Message.created_at))
            .limit(bounded_limit)
        )
        rows = list(result.scalars().all())
        if not rows:
            return ConversationHistory.empty()

        rows.reverse()
        return ConversationHistory(
            messages=tuple(_map_history_message(row) for row in rows)
        )


def _normalize_history_limit(limit: int) -> int:
    if limit < CONVERSATION_HISTORY_MIN_LIMIT or limit > CONVERSATION_HISTORY_MAX_LIMIT:
        raise ValueError(
            "limit must be between "
            f"{CONVERSATION_HISTORY_MIN_LIMIT} and {CONVERSATION_HISTORY_MAX_LIMIT}"
        )
    return limit


def _map_history_message(message: Message) -> ConversationHistoryMessage:
    return ConversationHistoryMessage(
        sender_type=message.sender_type,
        message_text=message.message_text,
        created_at=message.created_at,
    )
