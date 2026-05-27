"""Resolve greeting mode and reply language from conversation state (MVP)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas.conversation_context import ConversationHistory
from app.schemas.greeting import GreetingMode, GreetingPolicy
from app.services.customer_language_detection import (
    extract_telegram_language_code,
    language_display_name,
    resolve_reply_language,
)

GREETING_INACTIVITY_HOURS = 24


class GreetingPolicyService:
    def resolve(
        self,
        *,
        history: ConversationHistory,
        current_customer_message: str,
        message_timestamp: datetime | None = None,
        raw_payload: dict | None = None,
    ) -> GreetingPolicy:
        now = _coerce_utc(message_timestamp) or datetime.now(timezone.utc)
        prior_messages = _prior_messages_excluding_current(
            history,
            current_customer_message=current_customer_message,
        )
        prior_ai_turns = sum(
            1 for message in prior_messages if message.sender_type == "ai"
        )

        if prior_ai_turns == 0:
            mode = GreetingMode.FIRST_CONTACT
        elif _inactive_long_enough(prior_messages, now=now):
            mode = GreetingMode.SOFT_RETURN
        else:
            mode = GreetingMode.FOLLOW_UP

        language_code = resolve_reply_language(
            customer_message_text=current_customer_message,
            telegram_language_code=extract_telegram_language_code(raw_payload),
        )
        return GreetingPolicy(
            mode=mode,
            reply_language_code=language_code,
            reply_language_name=language_display_name(language_code),
        )


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _prior_messages_excluding_current(
    history: ConversationHistory,
    *,
    current_customer_message: str,
) -> tuple:
    if not history.messages:
        return ()

    messages = history.messages
    last = messages[-1]
    if (
        last.sender_type == "customer"
        and last.message_text.strip() == current_customer_message.strip()
    ):
        return messages[:-1]
    return messages


def _inactive_long_enough(prior_messages: tuple, *, now: datetime) -> bool:
    if not prior_messages:
        return False

    last_prior = prior_messages[-1]
    last_at = _coerce_utc(last_prior.created_at)
    if last_at is None:
        return False

    return now - last_at >= timedelta(hours=GREETING_INACTIVITY_HOURS)
