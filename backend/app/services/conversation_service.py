import uuid

from sqlalchemy import desc, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation

NEW_CONVERSATION_STATUS = "open"
REUSABLE_CONVERSATION_STATUSES = (
    "open",
    "waiting_for_customer",
    "waiting_for_owner",
)


class ConversationService:
    async def get_or_create_open_conversation(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_id: uuid.UUID,
        customer_id: uuid.UUID,
        channel: str,
        external_conversation_id: str | None = None,
    ) -> Conversation:
        normalized_external_id = _normalize_external_conversation_id(
            external_conversation_id
        )

        if normalized_external_id is not None:
            conversation = await self._find_reusable_by_external_conversation(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                flow_id=flow_id,
                channel=channel,
                external_conversation_id=normalized_external_id,
            )
            if conversation is not None:
                return conversation
        else:
            conversation = await self._find_reusable_by_customer(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                flow_id=flow_id,
                customer_id=customer_id,
                channel=channel,
            )
            if conversation is not None:
                return conversation

        conversation = Conversation(
            tenant_id=tenant_id,
            business_id=business_id,
            flow_id=flow_id,
            customer_id=customer_id,
            channel=channel,
            external_conversation_id=normalized_external_id,
            status=NEW_CONVERSATION_STATUS,
        )
        session.add(conversation)
        await session.flush()
        return conversation

    async def _find_reusable_by_external_conversation(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_id: uuid.UUID,
        channel: str,
        external_conversation_id: str,
    ) -> Conversation | None:
        result = await session.execute(
            select(Conversation)
            .where(
                Conversation.tenant_id == tenant_id,
                Conversation.business_id == business_id,
                Conversation.flow_id == flow_id,
                Conversation.channel == channel,
                Conversation.external_conversation_id == external_conversation_id,
                Conversation.status.in_(REUSABLE_CONVERSATION_STATUSES),
            )
            .order_by(
                nulls_last(desc(Conversation.last_message_at)),
                desc(Conversation.created_at),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _find_reusable_by_customer(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_id: uuid.UUID,
        customer_id: uuid.UUID,
        channel: str,
    ) -> Conversation | None:
        result = await session.execute(
            select(Conversation)
            .where(
                Conversation.tenant_id == tenant_id,
                Conversation.business_id == business_id,
                Conversation.flow_id == flow_id,
                Conversation.customer_id == customer_id,
                Conversation.channel == channel,
                Conversation.status.in_(REUSABLE_CONVERSATION_STATUSES),
            )
            .order_by(
                nulls_last(desc(Conversation.last_message_at)),
                desc(Conversation.created_at),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()


def _normalize_external_conversation_id(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None
