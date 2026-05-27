import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.schemas.conversation_context import (
    ConversationHistory,
    ConversationHistoryMessage,
)
from app.services.tenant_context_validator import validate_tenant_context

CONVERSATION_HISTORY_MIN_LIMIT = 10
CONVERSATION_HISTORY_MAX_LIMIT = 20
CONVERSATION_HISTORY_DEFAULT_LIMIT = CONVERSATION_HISTORY_MAX_LIMIT


@dataclass(frozen=True)
class IncomingMessageSaveResult:
    message: Message
    is_duplicate: bool


class MessageService:
    async def find_by_external_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        external_message_id: str | None,
    ) -> Message | None:
        if external_message_id is None:
            return None

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
    ) -> IncomingMessageSaveResult:
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
        )

        if external_message_id is not None and external_message_id != "":
            existing = await self.find_by_external_id(
                session,
                tenant_id,
                business.id,
                external_message_id,
            )
            if existing is not None:
                return IncomingMessageSaveResult(message=existing, is_duplicate=True)

        resolved_channel = channel if channel is not None else conversation.channel
        stored_external_id = external_message_id if external_message_id != "" else None

        message = Message(
            tenant_id=tenant_id,
            business_id=business.id,
            conversation_id=conversation.id,
            sender_type="customer",
            direction="incoming",
            channel=resolved_channel,
            message_text=message_text,
            message_type="text",
            external_message_id=stored_external_id,
            raw_payload=raw_payload,
        )
        session.add(message)
        await session.flush()

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
    ) -> Message:
        validate_tenant_context(
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            customer=customer,
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
