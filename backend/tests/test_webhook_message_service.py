import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
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
from app.services.orange_park_bitrix_service import (
    OrangeParkBitrixError,
    OrangeParkBitrixLeadResult,
)
from app.services.conversation_service import NEW_CONVERSATION_STATUS, ConversationService
from app.schemas.ai_reply import AiReplyResult
from app.schemas.ai_reply_orchestration import AiReplyOrchestrationOutcome
from app.services.ai_reply_orchestration_coordinator import REASON_AI_CHAIN_EXECUTED
from app.services.flow_service import LegacyWebhookFlow
from app.services.orange_park_dialog_service import (
    ORANGE_PARK_CONTACT_RECEIVED_REPLY_UK,
    ORANGE_PARK_START_WELCOME_UK,
)
from app.services.webhook_message_service import (
    WebhookMessageService,
    _response_metadata_from_message,
)
from tests.test_webhook_message_ai_wiring import _flow_service_mock
from tests.webhook_test_helpers import (
    delivery_visibility_service_mock,
    inbound_processing_lock_service_mock,
    message_trace_service_mock,
)


class _TracingServiceStub:
    def __init__(self) -> None:
        self.recorder = MagicMock(langfuse_trace_id="lf-message-turn")
        self.calls: list[dict] = []

    @asynccontextmanager
    async def trace_message_turn(self, **kwargs):
        self.calls.append(kwargs)
        yield self.recorder


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


def _success_ai_coordinator(reply_text: str = "AI wired reply") -> MagicMock:
    return MagicMock(
        execute_for_incoming_message=AsyncMock(
            return_value=AiReplyOrchestrationOutcome(
                is_duplicate=False,
                ai_executed=True,
                reason=REASON_AI_CHAIN_EXECUTED,
                ai_reply=AiReplyResult(
                    text=reply_text,
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


def _orange_park_contact_request() -> NormalizedWebhookMessageRequest:
    return NormalizedWebhookMessageRequest.model_validate(
        {
            "business_id": "orange-park",
            "channel": "telegram",
            "customer": {
                "external_customer_id": "telegram:111",
                "phone": "+380671112233",
                "name": "Олена Шевченко",
                "first_name": "Олена",
                "last_name": "Шевченко",
                "telegram_id": "111",
                "telegram_username": "olena",
                "contact_shared": True,
            },
            "message": {
                "text": "[telegram_contact_shared]",
                "external_message_id": f"tg:111:{uuid.uuid4()}",
                "external_conversation_id": "tg:111",
                "timestamp": "2026-05-21T10:00:00Z",
                "raw_payload": {
                    "provider": "telegram",
                    "telegram_id": "111",
                    "telegram_username": "olena",
                    "contact": {
                        "phone_number": "+380671112233",
                        "first_name": "Олена",
                        "last_name": "Шевченко",
                        "user_id": "111",
                    },
                },
            },
        }
    )



@pytest.mark.anyio
async def test_orange_park_area_reply_skips_ai_and_lead_creation():
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
        message_text="25",
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
        return_value=ConversationHistory.empty()
    )
    message_service.load_latest_orange_park_dialog_state = AsyncMock(
        return_value={
            "dialog_engine_version": "orange_park_v3",
            "intent": "apartment_sales",
            "stage": "apartment_area",
            "property_type": "apartment",
            "apartment_type": "1-room",
            "area_interest": None,
            "purpose": None,
            "purchase_path": None,
            "contact_requested": False,
            "contact_received": False,
        }
    )
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outgoing)
    lead_service = _lead_service_mock(business, customer, conversation)
    ai_reply_coordinator = _success_ai_coordinator()
    tracing_service = _TracingServiceStub()
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
        langfuse_tracing_service=tracing_service,
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _orange_park_request("25"),
    )

    assert result.lead_created is False
    assert "Зафіксував бажану площу близько 25 м²" in result.reply_to_customer
    assert incoming.metadata_["orange_park_dialog"]["state"]["area_interest"] == "25"
    lead_service.create_lead.assert_not_awaited()
    ai_reply_coordinator.execute_for_incoming_message.assert_not_awaited()
    assert tracing_service.calls[0]["customer_message_preview"] == "25"
    assert (
        tracing_service.calls[0]["observability"].business_external_id
        == "orange-park"
    )
    tracing_service.recorder.record_response.assert_called_once()
    assert (
        tracing_service.recorder.record_response.call_args.kwargs["metadata"][
            "business_uuid"
        ]
        == str(business.id)
    )
    trace_metadata = tracing_service.recorder.record_response.call_args.kwargs[
        "metadata"
    ]
    assert trace_metadata["runtime_path"] == "deterministic_dialog_engine"
    assert trace_metadata["dialog_intent"] == "apartment_sales"
    assert trace_metadata["dialog_stage"] == "apartment_purpose"


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
    tracing_service = _TracingServiceStub()
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
        langfuse_tracing_service=tracing_service,
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
    assert (
        tracing_service.calls[0]["observability"].business_external_id
        == "demo_barbershop_001"
    )
    tracing_service.recorder.record_response.assert_called_once()
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
    assert incoming.metadata_["orange_park_dialog"] == {
        "state": {
            "dialog_engine_version": "orange_park_v3",
            "intent": "unknown",
            "stage": "idle",
            "property_type": None,
            "apartment_type": None,
            "commercial_type": None,
            "area_interest": None,
            "budget_interest": None,
            "purpose": None,
            "purchase_path": None,
            "contact_requested": False,
            "contact_received": False,
        },
        "request_contact": False,
        "excluded_previous_history": True,
    }
    archive_call = session.execute.await_args_list[0]
    assert "update messages" in str(archive_call.args[0])
    assert "excluded_from_prompt_history" in archive_call.args[1]["metadata"]
    assert archive_call.args[1]["current_message_id"] == incoming.id
    message_service.load_recent_conversation_history.assert_not_awaited()
    lead_service.create_lead.assert_not_awaited()
    ai_reply_coordinator.execute_for_incoming_message.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("message_text", "expected_reply"),
    (
        (
            "Свяжи меня с менеджером",
            "Для зв'язку з менеджером натисніть кнопку "
            "«📱 Поділитися номером».",
        ),
        (
            "Які є варіанти до 100000 грн?",
            "Для зв'язку з менеджером натисніть кнопку "
            "«📱 Поділитися номером».",
        ),
    ),
)
async def test_orange_park_telegram_handoff_uses_contact_button_without_lead(
    message_text: str,
    expected_reply: str,
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
        message_text=message_text,
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
                    message_text=message_text,
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
        _orange_park_request(message_text),
    )

    assert result.lead_created is False
    assert result.reply_to_customer == expected_reply
    assert "Thank" not in result.reply_to_customer
    assert "Phone" not in result.reply_to_customer
    assert "Телефон:" not in result.reply_to_customer
    assert incoming.metadata_["orange_park_contact_collection"]["missing_fields"] == [
        "telegram_contact",
    ]
    assert incoming.metadata_["orange_park_contact_collection"][
        "telegram_contact_request"
    ] is True
    lead_service.create_lead.assert_not_awaited()
    ai_reply_coordinator.execute_for_incoming_message.assert_not_awaited()


@pytest.mark.anyio
async def test_orange_park_telegram_manual_phone_from_idle_does_not_request_contact():
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
    assert result.reply_to_customer.startswith("Підкажіть, будь ласка")
    assert "Thank" not in result.reply_to_customer
    assert "phone number" not in result.reply_to_customer
    assert "orange_park_contact_collection" not in incoming.metadata_
    lead_service.create_lead.assert_not_awaited()
    ai_reply_coordinator.execute_for_incoming_message.assert_not_awaited()


@pytest.mark.anyio
async def test_orange_park_yes_from_idle_does_not_set_contact_button_metadata():
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
        external_customer_id="telegram:111",
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
        message_text="Так",
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
        return_value=ConversationHistory.empty()
    )
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outgoing)
    lead_service = _lead_service_mock(business, customer, conversation)
    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=lead_service,
        ai_reply_coordinator=_success_ai_coordinator(),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(session, _orange_park_request("Так"))

    assert result.response_metadata is None
    assert "orange_park_contact_collection" not in incoming.metadata_
    assert incoming.metadata_["orange_park_dialog"]["state"]["stage"] == "idle"
    lead_service.create_lead.assert_not_awaited()


@pytest.mark.anyio
async def test_orange_park_v3_unknown_message_bypasses_ai():
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
        external_customer_id="telegram:111",
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
        message_text="Хочу уточнити деталі",
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
        return_value=ConversationHistory.empty()
    )
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outgoing)
    lead_service = _lead_service_mock(business, customer, conversation)
    ai_reply_coordinator = _success_ai_coordinator(
        "Для уточнення залиште номер телефону для зв'язку."
    )
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
        _orange_park_request("Хочу уточнити деталі"),
    )

    assert result.response_metadata is None
    assert "що саме вас цікавить:" in result.reply_to_customer
    assert "orange_park_contact_collection" not in incoming.metadata_
    ai_reply_coordinator.execute_for_incoming_message.assert_not_awaited()


@pytest.mark.anyio
async def test_orange_park_telegram_contact_payload_acknowledges_without_manual_phone_or_bitrix_lead():
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
        phone="+380671112233",
        external_customer_id="telegram:111",
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
        message_text="[telegram_contact_shared]",
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
    message_service.load_recent_conversation_history = AsyncMock()
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
        _orange_park_contact_request(),
    )

    assert result.reply_to_customer == (
        "Дякуємо. Запит передано менеджеру. Очікуйте дзвінок."
    )
    assert result.lead_created is False
    assert result.response_metadata == {
        "orange_park_contact_collection": {
            "contact_received": True,
            "crm_ready": True,
            "crm_creation_deferred": True,
        }
    }

    contact = incoming.metadata_["orange_park_contact_collection"]
    assert contact["phone"] == "+380671112233"
    assert contact["first_name"] == "Олена"
    assert contact["last_name"] == "Шевченко"
    assert contact["telegram_id"] == "111"
    assert contact["telegram_username"] == "olena"
    assert contact["business_id"] == "orange-park"
    assert contact["channel"] == "telegram"
    assert contact["missing_fields"] == []
    lead_service.create_lead.assert_not_awaited()
    ai_reply_coordinator.execute_for_incoming_message.assert_not_awaited()
    message_service.load_recent_conversation_history.assert_not_awaited()


@pytest.mark.anyio
async def test_orange_park_telegram_contact_with_first_name_only_does_not_ask_last_name():
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
        phone="+380671112233",
        external_customer_id="telegram:111",
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
        message_text="[telegram_contact_shared]",
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
    message_service.load_recent_conversation_history = AsyncMock()
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outgoing)
    lead_service = _lead_service_mock(business, customer, conversation)
    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=_flow_service_mock(business),
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=lead_service,
        ai_reply_coordinator=_success_ai_coordinator(),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
    )
    session = MagicMock()
    session.flush = AsyncMock()
    request = _orange_park_contact_request().model_copy(deep=True)
    request.customer.last_name = None

    result = await service.process_incoming_message(session, request)

    assert result.reply_to_customer == ORANGE_PARK_CONTACT_RECEIVED_REPLY_UK
    assert "телефон" not in result.reply_to_customer.casefold()
    assert "прізвище" not in result.reply_to_customer.casefold()
    assert incoming.metadata_["orange_park_contact_collection"]["missing_fields"] == [
        "last_name",
    ]
    lead_service.create_lead.assert_not_awaited()
    message_service.load_recent_conversation_history.assert_not_awaited()


@pytest.mark.anyio
async def test_orange_park_telegram_contact_is_ready_for_lead_when_bitrix_enabled():
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
        phone="+380671112233",
        external_customer_id="telegram:111",
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
    flow_service = _flow_service_mock(business)
    flow_service.resolve_for_webhook.return_value.metadata_ = {
        "crm": {"bitrix": {"enabled": True}},
    }
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="telegram",
        message_text="[telegram_contact_shared]",
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
    message_service.load_recent_conversation_history = AsyncMock()
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outgoing)
    lead_service = _lead_service_mock(business, customer, conversation)
    bitrix_service = MagicMock()
    bitrix_service.is_configured.return_value = True
    bitrix_service.create_or_update_lead = AsyncMock(
        return_value=OrangeParkBitrixLeadResult(
            lead_id="501",
            action="create",
            timestamp=datetime(2026, 6, 13, 10, 0, tzinfo=UTC),
        )
    )
    tracing_service = _TracingServiceStub()
    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=flow_service,
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=lead_service,
        orange_park_bitrix_service=bitrix_service,
        ai_reply_coordinator=_success_ai_coordinator(),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
        langfuse_tracing_service=tracing_service,
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _orange_park_contact_request(),
    )

    assert result.lead_created is True
    assert result.lead_updated is False
    assert result.notify_owner is False
    assert result.lead is not None
    assert result.reply_to_customer == (
        "Дякуємо. Запит передано менеджеру. Очікуйте дзвінок."
    )
    lead_service.create_lead.assert_awaited_once()
    bitrix_service.create_or_update_lead.assert_awaited_once()
    assert incoming.metadata_["orange_park_contact_collection"]["bitrix_lead_id"] == "501"
    assert incoming.metadata_["orange_park_contact_collection"]["action"] == "create"
    assert result.response_metadata == {
        "orange_park_contact_collection": {
            "contact_received": True,
            "crm_ready": True,
            "crm_creation_deferred": False,
            "bitrix_lead_id": "501",
            "action": "create",
            "timestamp": "2026-06-13T10:00:00+00:00",
        }
    }
    assert (
        tracing_service.recorder.record_response.call_args.kwargs["metadata"][
            "crm_sync_status"
        ]
        == "create"
    )

    bitrix_service.create_or_update_lead.side_effect = OrangeParkBitrixError(
        "Bitrix24 network request failed"
    )
    failed_result = await service.process_incoming_message(
        session,
        _orange_park_contact_request(),
    )

    assert failed_result.reply_to_customer == ORANGE_PARK_CONTACT_RECEIVED_REPLY_UK
    assert failed_result.response_metadata == {
        "orange_park_contact_collection": {
            "contact_received": True,
            "crm_ready": True,
            "crm_creation_deferred": True,
        }
    }
    assert (
        tracing_service.recorder.record_response.call_args.kwargs["metadata"][
            "crm_sync_status"
        ]
        == "failed_deferred"
    )


@pytest.mark.anyio
async def test_orange_park_bitrix_flag_with_missing_webhook_keeps_sync_deferred():
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
        phone="+380671112233",
        external_customer_id="telegram:111",
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
    flow_service = _flow_service_mock(business)
    flow_service.resolve_for_webhook.return_value.metadata_ = {
        "crm": {"bitrix": {"enabled": True}},
    }
    incoming = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="customer",
        direction="incoming",
        channel="telegram",
        message_text="[telegram_contact_shared]",
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
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outgoing)
    lead_service = _lead_service_mock(business, customer, conversation)
    bitrix_service = MagicMock()
    bitrix_service.is_configured.return_value = False
    bitrix_service.create_or_update_lead = AsyncMock()
    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=flow_service,
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=lead_service,
        orange_park_bitrix_service=bitrix_service,
        ai_reply_coordinator=_success_ai_coordinator(),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _orange_park_contact_request(),
    )

    assert result.lead_created is False
    assert result.lead_updated is False
    assert result.notify_owner is False
    lead_service.create_lead.assert_not_awaited()
    bitrix_service.create_or_update_lead.assert_not_awaited()


@pytest.mark.anyio
async def test_orange_park_bitrix_does_not_run_for_ordinary_telegram_message():
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
        external_customer_id="telegram:111",
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
        message_text="Які є квартири?",
    )
    outgoing = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=conversation.id,
        sender_type="ai",
        direction="outgoing",
        channel="telegram",
        message_text="AI wired reply",
    )
    flow_service = _flow_service_mock(business)
    flow_service.resolve_for_webhook.return_value.metadata_ = {
        "crm": {"bitrix": {"enabled": True}},
    }
    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(
        return_value=IncomingMessageSaveResult(message=incoming, is_duplicate=False)
    )
    message_service.load_recent_conversation_history = AsyncMock(
        return_value=ConversationHistory.empty()
    )
    message_service.save_outgoing_ai_message = AsyncMock(return_value=outgoing)
    lead_service = _lead_service_mock(business, customer, conversation)
    bitrix_service = MagicMock()
    bitrix_service.is_configured.return_value = True
    bitrix_service.create_or_update_lead = AsyncMock()
    service = WebhookMessageService(
        business_service=MagicMock(get_by_external_id=AsyncMock(return_value=business)),
        flow_service=flow_service,
        customer_service=MagicMock(get_or_create_customer=AsyncMock(return_value=customer)),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation)
        ),
        message_service=message_service,
        lead_service=lead_service,
        orange_park_bitrix_service=bitrix_service,
        ai_reply_coordinator=_success_ai_coordinator(),
        message_trace_service=message_trace_service_mock(),
        delivery_visibility_service=delivery_visibility_service_mock(),
        inbound_processing_lock_service=inbound_processing_lock_service_mock(),
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_incoming_message(
        session,
        _orange_park_request("Які є квартири?"),
    )

    assert result.lead_created is False
    assert result.lead_updated is False
    lead_service.create_lead.assert_not_awaited()
    bitrix_service.create_or_update_lead.assert_not_awaited()


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
