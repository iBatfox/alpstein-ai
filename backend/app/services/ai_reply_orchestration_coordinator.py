"""Gate AI reply orchestration on incoming message idempotency (T11.13)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai_reply_orchestration import AiReplyOrchestrationOutcome
from app.schemas.observability import ObservabilityContext
from app.services.ai_reply_orchestration_service import AiReplyOrchestrationService

REASON_DUPLICATE_INCOMING_MESSAGE = "duplicate_incoming_message"
REASON_AI_CHAIN_EXECUTED = "ai_chain_executed"


class AiReplyOrchestrationCoordinator:
    def __init__(
        self,
        orchestration_service: AiReplyOrchestrationService | None = None,
    ) -> None:
        self.orchestration_service = (
            orchestration_service or AiReplyOrchestrationService()
        )

    async def execute_for_incoming_message(
        self,
        session: AsyncSession,
        *,
        is_duplicate: bool,
        tenant_id: uuid.UUID,
        business: object,
        conversation: object,
        message: object,
        customer_message_text: str,
        channel: str,
        template_key: str,
        operator_business_context: str | None = None,
        message_timestamp: datetime | None = None,
        raw_payload: dict[str, Any] | None = None,
        observability: ObservabilityContext | None = None,
    ) -> AiReplyOrchestrationOutcome:
        if is_duplicate:
            return AiReplyOrchestrationOutcome(
                is_duplicate=True,
                ai_executed=False,
                reason=REASON_DUPLICATE_INCOMING_MESSAGE,
                ai_reply=None,
            )

        ai_reply = await self.orchestration_service.generate_reply(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            message=message,
            customer_message_text=customer_message_text,
            channel=channel,
            template_key=template_key,
            operator_business_context=operator_business_context,
            message_timestamp=message_timestamp,
            raw_payload=raw_payload,
            observability=observability,
        )
        return AiReplyOrchestrationOutcome(
            is_duplicate=False,
            ai_executed=True,
            reason=REASON_AI_CHAIN_EXECUTED,
            ai_reply=ai_reply,
        )
