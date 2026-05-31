"""T-f2.3 — ERPNext Communication read-model contract checks."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommunicationDoc:
    reference_doctype: str
    reference_name: str
    communication_medium: str
    sent_or_received: str
    content: str
    alpstein_external_message_id: str
    alpstein_channel: str
    alpstein_business_id: str
    alpstein_direction: str
    alpstein_sender_type: str
    alpstein_conversation_id: str


def build_docs(
    *,
    channel: str,
    business_id: str,
    lead_name: str,
    conversation_id: str,
    inbound_external_message_id: str,
    inbound_text: str,
    reply_text: str,
    outbound_message_id: str | None,
) -> list[CommunicationDoc]:
    medium = {
        "telegram": "Telegram",
        "instagram": "Instagram",
        "whatsapp": "WhatsApp",
        "website_chat": "Website Chat",
    }.get(channel, channel)
    docs = [
        CommunicationDoc(
            reference_doctype="Lead",
            reference_name=lead_name,
            communication_medium=medium,
            sent_or_received="Received",
            content=inbound_text,
            alpstein_external_message_id=inbound_external_message_id,
            alpstein_channel=channel,
            alpstein_business_id=business_id,
            alpstein_direction="incoming",
            alpstein_sender_type="customer",
            alpstein_conversation_id=conversation_id,
        )
    ]
    external_outbound_id = outbound_message_id or f"alpstein:ai:{inbound_external_message_id}"
    docs.append(
        CommunicationDoc(
            reference_doctype="Lead",
            reference_name=lead_name,
            communication_medium=medium,
            sent_or_received="Sent",
            content=reply_text,
            alpstein_external_message_id=external_outbound_id,
            alpstein_channel=channel,
            alpstein_business_id=business_id,
            alpstein_direction="outgoing",
            alpstein_sender_type="ai",
            alpstein_conversation_id=conversation_id,
        )
    )
    return docs


def create_missing(
    docs: list[CommunicationDoc],
    existing_keys: set[tuple[str, str]],
) -> list[CommunicationDoc]:
    return [
        doc
        for doc in docs
        if (doc.alpstein_external_message_id, doc.alpstein_business_id)
        not in existing_keys
    ]


def _assert_all_link_to_lead(docs: list[CommunicationDoc], lead_name: str) -> None:
    assert docs
    assert all(doc.reference_doctype == "Lead" for doc in docs)
    assert all(doc.reference_name == lead_name for doc in docs)


def test_instagram_inbound_creates_one_communication() -> None:
    docs = build_docs(
        channel="instagram",
        business_id="alpstein_ai_demo_001",
        lead_name="CRM-LEAD-2026-00042",
        conversation_id="conv-ig",
        inbound_external_message_id="ig:m_1",
        inbound_text="Привет",
        reply_text="Здравствуйте",
        outbound_message_id="out-ig-1",
    )

    inbound = [doc for doc in docs if doc.alpstein_sender_type == "customer"]

    assert len(inbound) == 1
    assert inbound[0].communication_medium == "Instagram"
    assert inbound[0].sent_or_received == "Received"


def test_instagram_ai_reply_creates_one_communication() -> None:
    docs = build_docs(
        channel="instagram",
        business_id="alpstein_ai_demo_001",
        lead_name="CRM-LEAD-2026-00042",
        conversation_id="conv-ig",
        inbound_external_message_id="ig:m_1",
        inbound_text="Привет",
        reply_text="Здравствуйте",
        outbound_message_id="out-ig-1",
    )

    outbound = [doc for doc in docs if doc.alpstein_sender_type == "ai"]

    assert len(outbound) == 1
    assert outbound[0].communication_medium == "Instagram"
    assert outbound[0].sent_or_received == "Sent"


def test_telegram_inbound_creates_one_communication() -> None:
    docs = build_docs(
        channel="telegram",
        business_id="alpstein_ai_demo_001",
        lead_name="CRM-LEAD-2026-00043",
        conversation_id="conv-tg",
        inbound_external_message_id="tg:123:5",
        inbound_text="Hello",
        reply_text="Hi",
        outbound_message_id="out-tg-1",
    )

    inbound = [doc for doc in docs if doc.alpstein_sender_type == "customer"]

    assert len(inbound) == 1
    assert inbound[0].communication_medium == "Telegram"
    assert inbound[0].alpstein_direction == "incoming"


def test_telegram_ai_reply_creates_one_communication() -> None:
    docs = build_docs(
        channel="telegram",
        business_id="alpstein_ai_demo_001",
        lead_name="CRM-LEAD-2026-00043",
        conversation_id="conv-tg",
        inbound_external_message_id="tg:123:5",
        inbound_text="Hello",
        reply_text="Hi",
        outbound_message_id="out-tg-1",
    )

    outbound = [doc for doc in docs if doc.alpstein_sender_type == "ai"]

    assert len(outbound) == 1
    assert outbound[0].communication_medium == "Telegram"
    assert outbound[0].alpstein_direction == "outgoing"


def test_duplicate_webhook_does_not_create_duplicate_communication() -> None:
    docs = build_docs(
        channel="instagram",
        business_id="alpstein_ai_demo_001",
        lead_name="CRM-LEAD-2026-00042",
        conversation_id="conv-ig",
        inbound_external_message_id="ig:m_1",
        inbound_text="Привет",
        reply_text="Здравствуйте",
        outbound_message_id="out-ig-1",
    )
    existing = {
        ("ig:m_1", "alpstein_ai_demo_001"),
        ("out-ig-1", "alpstein_ai_demo_001"),
    }

    assert create_missing(docs, existing) == []


def test_all_communications_link_to_correct_lead() -> None:
    lead_name = "CRM-LEAD-2026-00042"
    docs = build_docs(
        channel="telegram",
        business_id="alpstein_ai_demo_001",
        lead_name=lead_name,
        conversation_id="conv-tg",
        inbound_external_message_id="tg:123:5",
        inbound_text="Hello",
        reply_text="Hi",
        outbound_message_id="out-tg-1",
    )

    _assert_all_link_to_lead(docs, lead_name)
