"""Instagram duplicate re-ingress must run AI once per inbound message (not reuse stale replies)."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.business import Business
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.webhook import NormalizedWebhookMessageRequest
from app.schemas.ai_reply import AiReplyResult
from app.schemas.ai_reply_orchestration import AiReplyOrchestrationOutcome
from app.services.ai_reply_orchestration_coordinator import (
    REASON_AI_CHAIN_EXECUTED,
    REASON_DUPLICATE_INCOMING_MESSAGE,
)
from app.services.webhook_message_service import (
    DUPLICATE_SAFE_ACKNOWLEDGMENT,
    WebhookMessageService,
)
from tests.test_webhook_message_ai_wiring import _base_service_mocks


@pytest.fixture
def business() -> Business:
    return Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id="alpstein_ai_demo_001",
        name="Demo",
    )


@pytest.fixture
def conversation(business: Business) -> Conversation:
    return Conversation(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        customer_id=uuid.uuid4(),
        channel="instagram",
        status="open",
    )


def _instagram_request(**overrides) -> NormalizedWebhookMessageRequest:
    payload = {
        "business_id": "alpstein_ai_demo_001",
        "channel": "instagram",
        "customer": {"external_customer_id": "17841400000000001"},
        "message": {
            "text": "Сколько стоит бот для Instagram?",
            "external_message_id": "mid.ig.reingress.001",
        },
        "operator_business_context": "Alpstein AI demo business.",
    }
    payload.update(overrides)
    return NormalizedWebhookMessageRequest.model_validate(payload)


@pytest.mark.anyio
async def test_instagram_reingress_runs_ai_when_prior_turn_had_outgoing_reply(
    business: Business,
    conversation: Conversation,
) -> None:
    """Prior conversation AI reply must not block AI for a new duplicate inbound row."""
    tenant_id = business.tenant_id
    customer_id = uuid.uuid4()
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="instagram",
        message_text="Сколько стоит бот для Instagram?",
        external_message_id="mid.ig.reingress.001",
        created_at=datetime.utcnow(),
    )
    prior_ai_reply = Message(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel="instagram",
        message_text=DUPLICATE_SAFE_ACKNOWLEDGMENT,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )

    mocks = _base_service_mocks(
        business=business,
        customer=MagicMock(id=customer_id),
        conversation=conversation,
        incoming_message=incoming,
        is_duplicate=True,
    )
    mocks["message_service"].find_outgoing_ai_for_inbound = AsyncMock(return_value=None)
    mocks["message_service"].find_last_outgoing_ai_message = AsyncMock(
        return_value=prior_ai_reply,
    )
    mocks["ai_reply_coordinator"] = MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=False,
                ai_executed=True,
                reason=REASON_AI_CHAIN_EXECUTED,
                ai_reply=AiReplyResult(
                    text="Pricing depends on scope; we can estimate after a short call.",
                    is_success=True,
                    prompt_run_id=uuid.uuid4(),
                    model="gpt-4o-mini",
                    provider="openai",
                    error=None,
                ),
            )
        )
    )
    mocks["message_service"].save_outgoing_ai_message = AsyncMock(
        return_value=Message(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business.id,
            conversation_id=conversation.id,
            sender_type="ai",
            direction="outgoing",
            channel="instagram",
            message_text="Pricing depends on scope; we can estimate after a short call.",
        )
    )

    service = WebhookMessageService(**mocks)
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(session, _instagram_request())

    coordinator_kwargs = (
        mocks["ai_reply_coordinator"].execute_for_incoming_message.await_args.kwargs
    )
    assert coordinator_kwargs["is_duplicate"] is False
    assert coordinator_kwargs["channel"] == "instagram"
    assert "Сколько стоит бот" in coordinator_kwargs["customer_message_text"]
    assert result.reply_to_customer.startswith("Pricing depends")
    assert result.reply_to_customer != DUPLICATE_SAFE_ACKNOWLEDGMENT
    mocks["message_service"].save_outgoing_ai_message.assert_awaited_once()


@pytest.mark.anyio
async def test_instagram_reingress_skips_ai_when_inbound_already_has_outbound(
    business: Business,
    conversation: Conversation,
) -> None:
    tenant_id = business.tenant_id
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="instagram",
        message_text="Сколько стоит бот для Instagram?",
        external_message_id="mid.ig.reingress.002",
    )
    existing_outbound = Message(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel="instagram",
        message_text="Contextual reply already stored for this inbound.",
    )

    mocks = _base_service_mocks(
        business=business,
        customer=MagicMock(id=uuid.uuid4()),
        conversation=conversation,
        incoming_message=incoming,
        is_duplicate=True,
    )
    mocks["message_service"].find_outgoing_ai_for_inbound = AsyncMock(
        return_value=existing_outbound,
    )
    mocks["ai_reply_coordinator"] = MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=True,
                ai_executed=False,
                reason=REASON_DUPLICATE_INCOMING_MESSAGE,
                ai_reply=None,
            )
        )
    )

    service = WebhookMessageService(**mocks)
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(session, _instagram_request())

    coordinator_kwargs = (
        mocks["ai_reply_coordinator"].execute_for_incoming_message.await_args.kwargs
    )
    assert coordinator_kwargs["is_duplicate"] is True
    assert result.reply_to_customer == "Contextual reply already stored for this inbound."
    mocks["message_service"].save_outgoing_ai_message.assert_not_awaited()


@pytest.mark.anyio
async def test_telegram_duplicate_still_skips_ai_chain(
    business: Business,
    conversation: Conversation,
) -> None:
    from app.schemas.webhook import NormalizedWebhookMessageRequest

    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="telegram",
        message_text="Hello",
        external_message_id="tg-dup-001",
    )

    mocks = _base_service_mocks(
        business=business,
        customer=MagicMock(id=uuid.uuid4()),
        conversation=conversation,
        incoming_message=incoming,
        is_duplicate=True,
    )
    mocks["ai_reply_coordinator"] = MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=True,
                ai_executed=False,
                reason=REASON_DUPLICATE_INCOMING_MESSAGE,
                ai_reply=None,
            )
        )
    )
    mocks["message_service"].find_outgoing_ai_for_inbound = AsyncMock(return_value=None)
    mocks["message_service"].find_last_outgoing_ai_message = AsyncMock(return_value=None)

    service = WebhookMessageService(**mocks)
    session = MagicMock()
    session.flush = AsyncMock()

    request = NormalizedWebhookMessageRequest.model_validate(
        {
            "business_id": "alpstein_ai_demo_001",
            "channel": "telegram",
            "customer": {"phone": "+41790000001"},
            "message": {"text": "Hello", "external_message_id": "tg-dup-001"},
        }
    )
    await service.process_incoming_message(session, request)

    coordinator_kwargs = (
        mocks["ai_reply_coordinator"].execute_for_incoming_message.await_args.kwargs
    )
    assert coordinator_kwargs["is_duplicate"] is True
    assert coordinator_kwargs["channel"] == "telegram"


@pytest.mark.anyio
async def test_instagram_reingress_succeeds_when_no_message_trace_exists(
    business: Business,
    conversation: Conversation,
) -> None:
    """Meta-first persist + n8n re-ingress may have no trace; must not crash mark_completed."""
    tenant_id = business.tenant_id
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="instagram",
        message_text="Сколько стоит бот для Instagram?",
        external_message_id="mid.ig.reingress.no-trace",
    )
    outbound = Message(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel="instagram",
        message_text="Instagram bot pricing starts from a scoped discovery call.",
    )

    mocks = _base_service_mocks(
        business=business,
        customer=MagicMock(id=uuid.uuid4()),
        conversation=conversation,
        incoming_message=incoming,
        is_duplicate=True,
    )
    mocks["message_service"].find_outgoing_ai_for_inbound = AsyncMock(return_value=None)
    mocks["message_service"].find_last_outgoing_ai_message = AsyncMock(return_value=None)
    mocks["message_trace_service"].record_inbound_turn = AsyncMock(return_value=None)
    from app.services.message_trace_service import MessageTraceService

    real_trace_service = MessageTraceService()

    async def _safe_mark_completed(session, trace, **kwargs):
        return await real_trace_service.mark_completed(session, trace, **kwargs)

    mocks["message_trace_service"].mark_completed = AsyncMock(
        side_effect=_safe_mark_completed
    )
    mocks["ai_reply_coordinator"] = MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=False,
                ai_executed=True,
                reason=REASON_AI_CHAIN_EXECUTED,
                ai_reply=AiReplyResult(
                    text="Instagram bot pricing starts from a scoped discovery call.",
                    is_success=True,
                    prompt_run_id=uuid.uuid4(),
                    model="gpt-4o-mini",
                    provider="openai",
                    error=None,
                ),
            )
        )
    )
    mocks["message_service"].save_outgoing_ai_message = AsyncMock(return_value=outbound)

    service = WebhookMessageService(**mocks)
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(session, _instagram_request())

    assert result.reply_to_customer == (
        "Instagram bot pricing starts from a scoped discovery call."
    )
    assert result.is_duplicate is True
    mocks["message_trace_service"].mark_completed.assert_awaited_once()
    assert mocks["message_trace_service"].mark_completed.await_args.args[1] is None
