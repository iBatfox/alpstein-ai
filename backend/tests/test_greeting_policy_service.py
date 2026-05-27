from datetime import datetime, timedelta, timezone

from app.schemas.conversation_context import ConversationHistory, ConversationHistoryMessage
from app.schemas.greeting import GreetingMode
from app.services.greeting_policy_service import GreetingPolicyService


def _msg(sender: str, text: str, at: datetime) -> ConversationHistoryMessage:
    return ConversationHistoryMessage(
        sender_type=sender,
        message_text=text,
        created_at=at,
    )


def test_first_contact_when_no_prior_ai_messages():
    now = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    history = ConversationHistory(
        messages=(
            _msg("customer", "Hello", now),
        )
    )
    policy = GreetingPolicyService().resolve(
        history=history,
        current_customer_message="Hello",
        message_timestamp=now,
    )

    assert policy.mode is GreetingMode.FIRST_CONTACT
    assert policy.reply_language_code == "en"


def test_follow_up_when_ai_already_replied():
    now = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    history = ConversationHistory(
        messages=(
            _msg("customer", "Hello", now - timedelta(minutes=5)),
            _msg("ai", "Hi there", now - timedelta(minutes=4)),
            _msg("customer", "What services?", now),
        )
    )
    policy = GreetingPolicyService().resolve(
        history=history,
        current_customer_message="What services?",
        message_timestamp=now,
    )

    assert policy.mode is GreetingMode.FOLLOW_UP


def test_soft_return_after_inactivity():
    now = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    history = ConversationHistory(
        messages=(
            _msg("customer", "Hello", now - timedelta(days=2)),
            _msg("ai", "Welcome", now - timedelta(days=2, minutes=-1)),
            _msg("customer", "Back again", now),
        )
    )
    policy = GreetingPolicyService().resolve(
        history=history,
        current_customer_message="Back again",
        message_timestamp=now,
    )

    assert policy.mode is GreetingMode.SOFT_RETURN
