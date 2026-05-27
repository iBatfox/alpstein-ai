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
        customer_id: uuid.UUID,
        channel: str,
    ) -> Conversation:
        conversation = await self._find_reusable_conversation(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            customer_id=customer_id,
            channel=channel,
        )
        if conversation is not None:
            return conversation

        conversation = Conversation(
            tenant_id=tenant_id,
            business_id=business_id,
            customer_id=customer_id,
            channel=channel,
            status=NEW_CONVERSATION_STATUS,
        )
        session.add(conversation)
        await session.flush()
        return conversation

    async def _find_reusable_conversation(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        customer_id: uuid.UUID,
        channel: str,
    ) -> Conversation | None:
        result = await session.execute(
            select(Conversation)
            .where(
                Conversation.tenant_id == tenant_id,
                Conversation.business_id == business_id,
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
