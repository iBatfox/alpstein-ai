"""ConversationIntentService — CIP-A detection tests."""

import uuid
from datetime import datetime, timezone

import pytest

from app.schemas.conversation_context import ConversationHistory, ConversationHistoryMessage
from app.schemas.conversation_intent import ConversationIntent
from app.schemas.langfuse_intent_trace import (
    LANGFUSE_METADATA_CONVERSATION_INTENT,
    LANGFUSE_METADATA_INTENT_MATCHED_RULE,
)
from app.services.conversation_intent_service import ConversationIntentService


def _resolve(text: str, *, history: ConversationHistory | None = None):
    return ConversationIntentService().resolve(
        current_customer_message=text,
        history=history,
    )


def _customer_history(*texts: str) -> ConversationHistory:
    now = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    return ConversationHistory(
        messages=tuple(
            ConversationHistoryMessage(
                sender_type="customer",
                message_text=t,
                created_at=now,
            )
            for t in texts
        )
    )


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("I don't understand what you mean", ConversationIntent.CONFUSED_CUSTOMER),
        ("я не понял", ConversationIntent.CONFUSED_CUSTOMER),
        ("How much does it cost?", ConversationIntent.PRICING_INTEREST),
        ("сколько стоит", ConversationIntent.PRICING_INTEREST),
        ("Hi, how much?", ConversationIntent.PRICING_INTEREST),
        ("We want to start next week", ConversationIntent.IMPLEMENTATION_INTEREST),
        ("как начать", ConversationIntent.IMPLEMENTATION_INTEREST),
        ("нужен бот для сайта", ConversationIntent.IMPLEMENTATION_INTEREST),
        ("Can you integrate Bitrix24?", ConversationIntent.UNSUPPORTED_SYSTEM),
        ("Вы работаете с Salesforce?", ConversationIntent.UNSUPPORTED_SYSTEM),
        ("поддерживаете Odoo?", ConversationIntent.UNSUPPORTED_SYSTEM),
        (
            "How does Bitrix24 API integration work?",
            ConversationIntent.TECHNICAL_INTEREST,
        ),
        (
            "Как работает интеграция Salesforce через webhook?",
            ConversationIntent.TECHNICAL_INTEREST,
        ),
        ("How does n8n connect to your API?", ConversationIntent.TECHNICAL_INTEREST),
        ("Tell me about CRM integration in general", ConversationIntent.TECHNICAL_INTEREST),
        ("What is the weather in Bern?", ConversationIntent.OFF_TOPIC),
        ("погода в берне", ConversationIntent.OFF_TOPIC),
        ("Hello", ConversationIntent.SOCIAL_GREETING),
        ("привет", ConversationIntent.SOCIAL_GREETING),
        ("What can Alpstein AI do for my shop?", ConversationIntent.TECHNICAL_INTEREST),
    ],
)
def test_intent_detection_examples(message: str, expected: ConversationIntent):
    resolution = _resolve(message)
    assert resolution.intent is expected


def test_named_crm_does_not_route_to_implementation_interest():
    resolution = _resolve("We need Salesforce integration")
    assert resolution.intent is ConversationIntent.UNSUPPORTED_SYSTEM
    assert "named_salesforce" in resolution.matched_rule


def test_generic_need_integration_without_named_system():
    resolution = _resolve("We need integration for our shop workflow")
    assert resolution.intent is ConversationIntent.IMPLEMENTATION_INTEREST
    assert resolution.matched_rule.startswith("implementation_interest:")


def test_off_topic_conservative_with_product_tokens():
    resolution = _resolve("What is the weather for our CRM project?")
    assert resolution.intent is ConversationIntent.TECHNICAL_INTEREST
    assert resolution.intent is not ConversationIntent.OFF_TOPIC
    assert "technical_interest" in resolution.matched_rule


def test_short_reply_inherits_pricing_from_previous_customer_message():
    history = _customer_history("How much does it cost?")
    resolution = _resolve("Yes", history=history)
    assert resolution.intent is ConversationIntent.PRICING_INTEREST
    assert resolution.used_previous_message is True
    assert resolution.matched_rule.startswith("inherit:")


def test_short_reply_does_not_inherit_social_greeting():
    history = _customer_history("Hello")
    resolution = _resolve("Ok", history=history)
    assert resolution.intent is ConversationIntent.TECHNICAL_INTEREST
    assert resolution.used_previous_message is False


def test_short_reply_after_non_inheritable_previous_uses_current_message():
    history = _customer_history("Hello")
    resolution = _resolve("Why?", history=history)
    assert resolution.intent is ConversationIntent.TECHNICAL_INTEREST
    assert resolution.used_previous_message is False
    assert resolution.matched_rule == "default:technical_interest"


def test_all_intent_enum_values_are_reachable():
    seen: set[ConversationIntent] = set()
    samples = [
        "Hello",
        "How does the API work?",
        "We want to start next week",
        "price?",
        "Can you integrate SAP?",
        "I am confused",
        "погода",
        "random product question",
    ]
    for sample in samples:
        seen.add(_resolve(sample).intent)
    assert seen == set(ConversationIntent)


def test_langfuse_metadata_field_names_are_defined():
    assert LANGFUSE_METADATA_CONVERSATION_INTENT == "conversation_intent"
    assert LANGFUSE_METADATA_INTENT_MATCHED_RULE == "intent_matched_rule"


def test_matched_rule_is_non_empty_string():
    resolution = _resolve("сколько стоит")
    assert resolution.matched_rule
    assert isinstance(resolution.matched_rule, str)
