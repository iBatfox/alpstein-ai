import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.business import Business
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.lead import LEAD_PRIORITY_NORMAL, LEAD_STATUS_NEW, Lead
from app.models.message import Message
from app.schemas.webhook import NormalizedWebhookMessageRequest
from app.schemas.conversation_context import (
    ConversationHistory,
    ConversationHistoryMessage,
)
from app.services.message_service import IncomingMessageSaveResult
from app.services.conversation_service import NEW_CONVERSATION_STATUS, ConversationService
from app.schemas.ai_reply import AiReplyResult
from app.schemas.ai_reply_orchestration import AiReplyOrchestrationOutcome
from app.services.ai_reply_orchestration_coordinator import REASON_AI_CHAIN_EXECUTED
from app.services.flow_service import LegacyWebhookFlow
from app.services.webhook_message_service import (
    WebhookMessageService,
    _orange_park_contact_collection_reply_and_metadata,
)
from tests.test_webhook_message_ai_wiring import _flow_service_mock
from tests.webhook_test_helpers import (
    delivery_visibility_service_mock,
    inbound_processing_lock_service_mock,
    message_trace_service_mock,
)

ORANGE_PARK_START_WELCOME_UK = (
    "Добрий день! 👋\n\n"
    "Я AI-асистент ЖК Orange Park.\n\n"
    "Можу допомогти з інформацією про комплекс, квартири, комерційні приміщення "
    "та умови придбання, а також передати ваш запит менеджеру.\n\n"
    "Що вас цікавить?\n"
    "🏡 Квартира\n"
    "🏢 Комерційне приміщення\n"
    "💳 Умови покупки / розтермінування"
)


def _none_result() -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    return result


def _execute_mappings(rows):
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows
    return result


def _lead_service_mock(
    business: Business,
    customer: Customer,
    conversation: Conversation,
) -> MagicMock:
    async def _create_lead(session, **kwargs) -> Lead:
        return Lead(
            id=uuid.uuid4(),
            tenant_id=kwargs["tenant_id"],
            business_id=kwargs["business_id"],
            customer_id=kwargs["customer_id"],
            conversation_id=kwargs["conversation_id"],
            status=LEAD_STATUS_NEW,
            priority=LEAD_PRIORITY_NORMAL,
            source_channel=kwargs.get("source_channel", "whatsapp"),
        )

    lead_service = MagicMock()
    lead_service.find_active_lead = AsyncMock(return_value=None)
    lead_service.create_lead = AsyncMock(side_effect=_create_lead)
    lead_service.update_lead = AsyncMock(side_effect=lambda session, *, lead, **kw: lead)
    return lead_service


def _success_ai_coordinator() -> MagicMock:
    return MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=False,
                ai_executed=True,
                reason=REASON_AI_CHAIN_EXECUTED,
                ai_reply=AiReplyResult(
                    text="AI wired reply",
                    is_success=True,
                    prompt_run_id=uuid.uuid4(),
                    model="gpt-4o-mini",
                    provider="openai",
                    error=None,
                ),
            )
        )
    )


def _request(**overrides) -> NormalizedWebhookMessageRequest:
    payload = {
        "business_id": "demo_barbershop_001",
        "channel": "whatsapp",
        "customer": {"phone": "+41790000000"},
        "message": {
            "text": "Hello",
            "external_message_id": "wamid.example",
            "timestamp": "2026-05-21T10:00:00Z",
        },
    }
    payload.update(overrides)
    return NormalizedWebhookMessageRequest.model_validate(payload)


def _orange_park_request(message_text: str) -> NormalizedWebhookMessageRequest:
    return NormalizedWebhookMessageRequest.model_validate(
        {
            "business_id": "orange-park",
            "channel": "telegram",
            "customer": {
                "external_customer_id": "tg-orange-park-customer",
                "phone": message_text if message_text.startswith("+") else None,
            },
            "message": {
                "text": message_text,
                "external_message_id": f"tg:orange-park:{uuid.uuid4()}",
                "external_conversation_id": "tg:orange-park-contact-form-test",
                "timestamp": "2026-05-21T10:00:00Z",
            },
        }
    )


def test_orange_park_contact_form_defaults_to_ukrainian_for_ambiguous_handoff():
    reply, metadata = _orange_park_contact_collection_reply_and_metadata(
        "Давай",
        history=ConversationHistory.empty(),
    )

    assert reply == (
        "Будь ласка, залиште дані у такому форматі:\n\n"
        "Ім'я:\n"
        "Прізвище:\n"
        "Телефон:"
    )
    assert "Пожалуйста" not in reply
    assert "Please" not in reply
    assert metadata["orange_park_contact_collection"]["missing_fields"] == [
        "first_name",
        "last_name",
        "phone",
    ]


def test_orange_park_phone_followup_defaults_to_ukrainian_without_language_context():
    reply, metadata = _orange_park_contact_collection_reply_and_metadata(
        "+41798232786",
        history=ConversationHistory.empty(),
    )

    assert reply == "Дякую, номер отримав. Напишіть, будь ласка, ім'я та прізвище."
    assert "Спасибо" not in reply
    assert "Thanks" not in reply
    assert metadata["orange_park_contact_collection"]["missing_fields"] == [
        "first_name",
        "last_name",
    ]


@pytest.fixture
def business() -> Business:
    return Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id="demo_barbershop_001",
        name="Demo",
    )


@pytest.fixture
def customer(business: Business) -> Customer:
    return Customer(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        phone="+41790000000",
        source_channel="whatsapp",
    )


@pytest.fixture
def conversation(business: Business, customer: Customer) -> Conversation:
    return Conversation(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=uuid.uuid4(),
        customer_id=customer.id,
        channel="whatsapp",
        status="waiting_for_customer",
    )


@pytest.mark.anyio
async def test_process_incoming_message_orchestrates_services(
    business: Business,
    customer: Customer,
    conversation: Conversation,
):
    message = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="whatsapp",
        message_text="Hello",
    )
    business_service = MagicMock()
    business_service.get_by_external_id = AsyncMock(return_value=business)
    customer_service = MagicMock()
    customer_service.get_or_create_customer = AsyncMock(return_value=customer)
    conversation_service = MagicMock()
    conversation_service.get_or_create_open_conversation = AsyncMock(
        return_value=conversation
    )
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=message, is_duplicate=False)
    )
    message_service.save_outgoing_ai_message = AsyncMock()
    ai_reply_coordinator = _success_ai_coordinator()
    session = MagicMock()
    session.flush = AsyncMock()

    flow_service = _flow_service_mock(business)
    service = WebhookMessageService(
        business_service=business_service,
        customer_service=customer_service,
        conversation_service=conversation_service,
        message_service=message_service,
        lead_service=_lead_service_mock(business, customer, conversation),
        ai_reply_coordinator=ai_reply_coordinator,
        flow_service=flow_service,
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
    )
    request = _request()

    result = await service.process_incoming_message(session, request)

    flow_service.resolve_for_webhook.assert_awaited_once()
    assert result.flow.flow_key == "default"
    business_service.get_by_external_id.assert_awaited_once_with(
        session,
        "demo_barbershop_001",
    )
    customer_service.get_or_create_customer.assert_awaited_once()
    conversation_service.get_or_create_open_conversation.assert_awaited_once()
    conv_kwargs = (
        conversation_service.get_or_create_open_conversation.await_args.kwargs
    )
    assert conv_kwargs["flow_id"] == flow_service.resolve_for_webhook.return_value.id
    assert conv_kwargs.get("external_conversation_id") is None
    message_service.save_incoming_customer_message.assert_awaited_once()
    assert result.is_duplicate is False
    assert result.lead_created is True
    assert result.notify_owner is True
    assert result.reply_to_customer == "AI wired reply"
    ai_reply_coordinator.execute_for_incoming_message.assert_awaited_once()
    assert conversation.last_message_at == datetime(2026, 5, 21, 10, 0, 0)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("raw_payload", "previous_customer_message"),
    [
        ({"language_code": "uk"}, "old stale message"),
        ({"language_code": "ru"}, "old stale message"),
        ({}, "old stale message"),
        ({"language_code": "ru"}, "Свяжи меня с менеджером"),
    ],
)
async def test_orange_park_telegram_start_always_ukrainian_and_skips_ai(
    raw_payload,
    previous_customer_message: str,
):
    business = Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id="orange-park",
        name="Orange Park",
    )
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        external_customer_id="tg-orange-park-customer",
        source_channel="telegram",
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=uuid.uuid4(),
        customer_id=customer.id,
        channel="telegram",
        status="open",
    )
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="telegram",
        message_text="/start",
    )
    outgoing = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel="telegram",
        message_text="",
    )
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=False)
    )
    message_service.load_recent_conversation_history = AsyncMock(
        return_value=ConversationHistory(
            messages=(
                ConversationHistoryMessage(
                    sender_type="customer",
                    message_text=previous_customer_message,
                    created_at=datetime(2026, 5, 21, 9, 59, 0),
                ),
            )
        )
    )
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outgoing)
    lead_service = _lead_service_mock(business, customer, conversation)
    ai_reply_coordinator = _success_ai_coordinator()
    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=lead_service,
        ai_reply_coordinator=ai_reply_coordinator,
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
    )
    session = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock())

    result = await service.process_incoming_message(
        session,
        NormalizedWebhookMessageRequest.model_validate(
            {
                "business_id": "orange-park",
                "channel": "telegram",
                "customer": {"external_customer_id": "tg-orange-park-customer"},
                "message": {
                    "text": "/start",
                    "external_message_id": f"tg:orange-park:{uuid.uuid4()}",
                    "external_conversation_id": "tg:orange-park-start-test",
                    "timestamp": "2026-05-21T10:00:00Z",
                    "raw_payload": raw_payload,
                },
            }
        ),
    )

    assert result.lead_created is False
    assert result.reply_to_customer == ORANGE_PARK_START_WELCOME_UK
    assert "I'm here" not in result.reply_to_customer
    assert "What are you interested" not in result.reply_to_customer
    assert incoming.metadata_["orange_park_start_reset"] == {
        "stage": "orange_park_telegram_start_reset",
        "excluded_previous_history": True,
        "language": "uk",
    }
    archive_call = session.execute.await_args_list[0]
    assert "update messages" in str(archive_call.args[0])
    assert "excluded_from_prompt_history" in archive_call.args[1]["metadata"]
    assert archive_call.args[1]["current_message_id"] == incoming.id
    message_service.load_recent_conversation_history.assert_not_awaited()
    lead_service.create_lead.assert_not_awaited()
    ai_reply_coordinator.execute_for_incoming_message.assert_not_awaited()


@pytest.mark.anyio
async def test_orange_park_telegram_handoff_asks_russian_contact_form_without_lead():
    business = Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id="orange-park",
        name="Orange Park",
    )
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        external_customer_id="tg-orange-park-customer",
        source_channel="telegram",
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=uuid.uuid4(),
        customer_id=customer.id,
        channel="telegram",
        status="open",
    )
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="telegram",
        message_text="Свяжи меня с менеджером",
    )
    outgoing = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel="telegram",
        message_text="",
    )
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=False)
    )
    message_service.load_recent_conversation_history = AsyncMock(
        return_value=ConversationHistory(
            messages=(
                ConversationHistoryMessage(
                    sender_type="customer",
                    message_text="Свяжи меня с менеджером",
                    created_at=datetime(2026, 5, 21, 10, 0, 0),
                ),
            )
        )
    )
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outgoing)
    lead_service = _lead_service_mock(business, customer, conversation)
    ai_reply_coordinator = _success_ai_coordinator()
    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=lead_service,
        ai_reply_coordinator=ai_reply_coordinator,
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _orange_park_request("Свяжи меня с менеджером"),
    )

    assert result.lead_created is False
    assert result.reply_to_customer == (
        "Пожалуйста, оставьте данные в таком формате:\n\n"
        "Имя:\n"
        "Фамилия:\n"
        "Телефон:"
    )
    assert "Thank" not in result.reply_to_customer
    assert "Phone" not in result.reply_to_customer
    assert incoming.metadata_["orange_park_contact_collection"]["missing_fields"] == [
        "first_name",
        "last_name",
        "phone",
    ]
    lead_service.create_lead.assert_not_awaited()
    ai_reply_coordinator.execute_for_incoming_message.assert_not_awaited()


@pytest.mark.anyio
async def test_orange_park_telegram_phone_asks_missing_name_in_russian_without_lead():
    business = Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id="orange-park",
        name="Orange Park",
    )
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        phone="+41798232786",
        external_customer_id="tg-orange-park-customer",
        source_channel="telegram",
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=uuid.uuid4(),
        customer_id=customer.id,
        channel="telegram",
        status="open",
    )
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="telegram",
        message_text="+41798232786",
    )
    outgoing = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel="telegram",
        message_text="",
    )
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=False)
    )
    message_service.load_recent_conversation_history = AsyncMock(
        return_value=ConversationHistory(
            messages=(
                ConversationHistoryMessage(
                    sender_type="customer",
                    message_text="Свяжи меня с менеджером",
                    created_at=datetime(2026, 5, 21, 9, 59, 0),
                ),
                ConversationHistoryMessage(
                    sender_type="customer",
                    message_text="+41798232786",
                    created_at=datetime(2026, 5, 21, 10, 0, 0),
                ),
            )
        )
    )
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outgoing)
    lead_service = _lead_service_mock(business, customer, conversation)
    ai_reply_coordinator = _success_ai_coordinator()
    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=lead_service,
        ai_reply_coordinator=ai_reply_coordinator,
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _orange_park_request("+41798232786"),
    )

    assert result.lead_created is False
    assert result.reply_to_customer == (
        "Спасибо, номер получил. Напишите, пожалуйста, имя и фамилию."
    )
    assert "Thank" not in result.reply_to_customer
    assert "phone number" not in result.reply_to_customer
    assert incoming.metadata_["orange_park_contact_collection"]["phone"] == (
        "+41798232786"
    )
    assert incoming.metadata_["orange_park_contact_collection"]["missing_fields"] == [
        "first_name",
        "last_name",
    ]
    lead_service.create_lead.assert_not_awaited()
    ai_reply_coordinator.execute_for_incoming_message.assert_not_awaited()


@pytest.mark.anyio
async def test_process_incoming_message_uses_legacy_branch_when_flow_table_absent(
    business: Business,
):
    legacy_flow = LegacyWebhookFlow(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
    )
    business_service = MagicMock()
    business_service.get_by_external_id = AsyncMock(return_value=business)
    flow_service = MagicMock()
    flow_service.resolve_for_webhook = AsyncMock(return_value=legacy_flow)
    service = WebhookMessageService(
        business_service=business_service,
        flow_service=flow_service,
    )
    legacy_result = object()
    service._process_incoming_message_legacy = AsyncMock(return_value=legacy_result)
    session = MagicMock()

    result = await service.process_incoming_message(session, _request())

    assert result is legacy_result
    flow_service.resolve_for_webhook.assert_awaited_once_with(
        session,
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_key=None,
    )
    service._process_incoming_message_legacy.assert_awaited_once()
    legacy_kwargs = service._process_incoming_message_legacy.await_args.kwargs
    assert legacy_kwargs["tenant_id"] == business.tenant_id
    assert legacy_kwargs["business"] is business
    assert legacy_kwargs["flow"] is legacy_flow


@pytest.mark.anyio
async def test_process_incoming_message_returns_duplicate_flag(
    business: Business,
    customer: Customer,
    conversation: Conversation,
):
    message = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="whatsapp",
        message_text="Hello",
    )
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=message, is_duplicate=True)
    )
    message_service.find_last_outgoing_ai_message = AsyncMock(return_value=None)
    message_service.find_outgoing_ai_for_inbound = AsyncMock(return_value=None)
    ai_reply_coordinator = MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=True,
                ai_executed=False,
                reason="duplicate_incoming_message",
                ai_reply=None,
            )
        )
    )
    lead_service = _lead_service_mock(business, customer, conversation)
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=lead_service,
        ai_reply_coordinator=ai_reply_coordinator,
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(session, _request())

    assert result.is_duplicate is True
    assert result.lead_created is False
    assert result.notify_owner is False
    lead_service.find_active_lead.assert_not_awaited()


@pytest.mark.anyio
async def test_process_incoming_message_creates_customer_via_customer_service(
    business: Business,
    customer: Customer,
    conversation: Conversation,
):
    customer_service = MagicMock()
    customer_service.get_or_create_customer = AsyncMock(return_value=customer)
    message = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="whatsapp",
        message_text="Hello",
    )
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        customer_service=customer_service,
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=MagicMock(
            save_incoming_customer_message=AsyncMock(
                return_value=IncomingMessageSaveResult(
                    message=message,
                    is_duplicate=False,
                )
            ),
            save_outgoing_ai_message=AsyncMock(),
        ),
        lead_service=_lead_service_mock(business, customer, conversation),
        ai_reply_coordinator=_success_ai_coordinator(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    await service.process_incoming_message(session, _request())

    customer_service.get_or_create_customer.assert_awaited_once_with(
        session,
        tenant_id=business.tenant_id,
        business_id=business.id,
        source_channel="whatsapp",
        phone="+41790000000",
        external_customer_id=None,
        name=None,
        email=None,
    )


@pytest.mark.anyio
async def test_process_incoming_message_creates_open_conversation_when_none_reusable(
    business: Business,
    customer: Customer,
):
    session = MagicMock()
    session.execute = AsyncMock(return_value=_none_result())
    session.flush = AsyncMock()
    message = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=uuid.uuid4(),
        sender_type="customer",
        direction="incoming",
        channel="whatsapp",
        message_text="Hello",
    )
    placeholder_conversation = Conversation(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        customer_id=customer.id,
        channel="whatsapp",
        status=NEW_CONVERSATION_STATUS,
    )
    service = WebhookMessageService(
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business)
        ),
        flow_service=_flow_service_mock(business),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer)
        ),
        conversation_service=ConversationService(),
        message_service=MagicMock(
            save_incoming_customer_message=AsyncMock(
                return_value=IncomingMessageSaveResult(
                    message=message,
                    is_duplicate=False,
                )
            ),
            save_outgoing_ai_message=AsyncMock(),
        ),
        lead_service=_lead_service_mock(
            business,
            customer,
            placeholder_conversation,
        ),
        ai_reply_coordinator=_success_ai_coordinator(),
    )

    result = await service.process_incoming_message(session, _request())

    assert result.conversation.status == NEW_CONVERSATION_STATUS
    session.add.assert_called()
