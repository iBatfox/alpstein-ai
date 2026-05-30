"""Tests for Instagram ingress persistence and account mapping."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.models.business import Business
from app.models.customer import Customer
from app.models.message import Message
from app.services.instagram_account_resolver import ResolvedInstagramAccount
from app.services.instagram_ingress import (
    InstagramIngressPersistenceService,
    InstagramIngressProcessResult,
    InstagramIngressPersistOutcome,
    InstagramIngressService,
    NormalizedInstagramInboundMessage,
    SKIP_REASON_MISSING_ACCOUNT_MAPPING,
)
from app.services.message_service import IncomingMessageSaveResult
from tests.test_instagram_ingress import REAL_CHANGE_VALUE_PAYLOAD
from tests.test_webhook_message_ai_wiring import _default_flow


def _normalized_message(**overrides) -> NormalizedInstagramInboundMessage:
    base = {
        "platform": "instagram",
        "external_user_id": "SENDER_ID",
        "external_chat_id": "SENDER_ID",
        "message_id": "MID_REAL_001",
        "message_text": "hello real dm",
        "direction": "inbound",
        "received_at": datetime.fromtimestamp(123, tz=UTC),
        "raw_event_type": "changes.value.message",
        "source_account_id": "IG_SOURCE_ACCOUNT",
    }
    base.update(overrides)
    return NormalizedInstagramInboundMessage(**base)


def _business(*, external_id: str = "demo_alpstein_001") -> Business:
    return Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        external_id=external_id,
        name="Demo",
    )


def _persistence_service(
    *,
    business: Business,
    save_results: list[IncomingMessageSaveResult],
    account: ResolvedInstagramAccount | None,
) -> InstagramIngressPersistenceService:
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        external_customer_id="SENDER_ID",
        source_channel="instagram",
    )
    flow = _default_flow(business)
    conversation = MagicMock(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        flow_id=flow.id,
        customer_id=customer.id,
        channel="instagram",
        status="open",
    )

    message_service = MagicMock()
    message_service.save_incoming_customer_message = AsyncMock(side_effect=save_results)

    return InstagramIngressPersistenceService(
        ingress_service=InstagramIngressService(
            app_settings=Settings(instagram_user_id="IG_SOURCE_ACCOUNT"),
        ),
        account_resolver=MagicMock(
            resolve_by_source_account_id=AsyncMock(return_value=account),
        ),
        business_service=MagicMock(
            get_by_external_id=AsyncMock(return_value=business),
        ),
        flow_service=MagicMock(
            resolve_for_webhook=AsyncMock(return_value=flow),
        ),
        customer_service=MagicMock(
            get_or_create_customer=AsyncMock(return_value=customer),
        ),
        conversation_service=MagicMock(
            get_or_create_open_conversation=AsyncMock(return_value=conversation),
        ),
        message_service=message_service,
    )


@pytest.mark.anyio
async def test_instagram_message_persists_when_account_mapping_exists() -> None:
    business = _business()
    account = ResolvedInstagramAccount(
        tenant_id=business.tenant_id,
        business_id=business.id,
        business_external_id=business.external_id,
        source_account_id="IG_SOURCE_ACCOUNT",
    )
    stored = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=uuid.uuid4(),
        sender_type="customer",
        direction="incoming",
        channel="instagram",
        message_text="hello real dm",
        external_message_id="MID_REAL_001",
        idempotency_key="ext:MID_REAL_001",
    )
    service = _persistence_service(
        business=business,
        account=account,
        save_results=[IncomingMessageSaveResult(message=stored, is_duplicate=False)],
    )
    session = MagicMock()
    session.flush = AsyncMock()

    result = await service.process_webhook(session, REAL_CHANGE_VALUE_PAYLOAD)

    assert len(result.outcomes) == 1
    outcome = result.outcomes[0]
    assert outcome.persisted is True
    assert outcome.is_duplicate is False
    assert outcome.skipped is False
    assert outcome.internal_message_id == stored.id
    service._message_service.save_incoming_customer_message.assert_awaited_once()
    kwargs = service._message_service.save_incoming_customer_message.await_args.kwargs
    assert kwargs["external_message_id"] == "MID_REAL_001"
    assert kwargs["channel"] == "instagram"
    assert kwargs["message_text"] == "hello real dm"


@pytest.mark.anyio
async def test_missing_account_mapping_is_handled_safely() -> None:
    business = _business()
    service = _persistence_service(
        business=business,
        account=None,
        save_results=[],
    )
    session = MagicMock()

    result = await service.process_webhook(session, REAL_CHANGE_VALUE_PAYLOAD)

    assert result.outcomes[0].skipped is True
    assert result.outcomes[0].skip_reason == SKIP_REASON_MISSING_ACCOUNT_MAPPING
    service._message_service.save_incoming_customer_message.assert_not_awaited()


@pytest.mark.anyio
async def test_duplicate_message_id_does_not_create_second_db_record() -> None:
    business = _business()
    account = ResolvedInstagramAccount(
        tenant_id=business.tenant_id,
        business_id=business.id,
        business_external_id=business.external_id,
        source_account_id="IG_SOURCE_ACCOUNT",
    )
    stored = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=uuid.uuid4(),
        sender_type="customer",
        direction="incoming",
        channel="instagram",
        message_text="hello real dm",
        external_message_id="MID_REAL_001",
        idempotency_key="ext:MID_REAL_001",
    )
    service = _persistence_service(
        business=business,
        account=account,
        save_results=[
            IncomingMessageSaveResult(message=stored, is_duplicate=False),
            IncomingMessageSaveResult(message=stored, is_duplicate=True),
        ],
    )
    session = MagicMock()
    session.flush = AsyncMock()

    first = await service.process_webhook(session, REAL_CHANGE_VALUE_PAYLOAD)
    second = await service.process_webhook(session, REAL_CHANGE_VALUE_PAYLOAD)

    assert first.outcomes[0].is_duplicate is False
    assert second.outcomes[0].is_duplicate is True
    assert service._message_service.save_incoming_customer_message.await_count == 2


@pytest.mark.anyio
async def test_duplicate_ignored_after_new_persistence_service_instance() -> None:
    business = _business()
    account = ResolvedInstagramAccount(
        tenant_id=business.tenant_id,
        business_id=business.id,
        business_external_id=business.external_id,
        source_account_id="IG_SOURCE_ACCOUNT",
    )
    stored = Message(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        business_id=business.id,
        conversation_id=uuid.uuid4(),
        sender_type="customer",
        direction="incoming",
        channel="instagram",
        message_text="hello real dm",
        external_message_id="MID_REAL_001",
        idempotency_key="ext:MID_REAL_001",
    )
    shared_message_service = MagicMock()
    shared_message_service.save_incoming_customer_message = AsyncMock(
        side_effect=[
            IncomingMessageSaveResult(message=stored, is_duplicate=False),
            IncomingMessageSaveResult(message=stored, is_duplicate=True),
        ]
    )

    def _build_service() -> InstagramIngressPersistenceService:
        service = _persistence_service(
            business=business,
            account=account,
            save_results=[],
        )
        service._message_service = shared_message_service
        return service

    session = MagicMock()
    session.flush = AsyncMock()

    first_service = _build_service()
    second_service = _build_service()

    first = await first_service.process_webhook(session, REAL_CHANGE_VALUE_PAYLOAD)
    second = await second_service.process_webhook(session, REAL_CHANGE_VALUE_PAYLOAD)

    assert first.outcomes[0].is_duplicate is False
    assert second.outcomes[0].is_duplicate is True


def test_process_result_duplicate_message_ids_property() -> None:
    message = _normalized_message()
    result = InstagramIngressProcessResult(
        (
            InstagramIngressPersistOutcome(
                normalized=message,
                persisted=True,
                is_duplicate=True,
                skipped=False,
                internal_message_id=uuid.uuid4(),
            ),
        )
    )
    assert result.duplicate_message_ids == ("MID_REAL_001",)
