"""Rule-based conversation intent detection (CIP-A — no prompt assembly)."""

from __future__ import annotations

import re

from app.schemas.conversation_context import ConversationHistory
from app.schemas.conversation_intent import (
    ConversationIntent,
    ConversationIntentResolution,
)

SHORT_REPLY_MAX_WORDS = 4
SHORT_REPLY_MAX_CHARS = 30

# Named CRM/ERP systems — feasibility questions route here unless technical-how.
_NAMED_SYSTEM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("bitrix24", re.compile(r"\bbitrix\s*24\b|\bbitrix24\b", re.I)),
    ("salesforce", re.compile(r"\bsalesforce\b", re.I)),
    ("hubspot", re.compile(r"\bhubspot\b", re.I)),
    ("odoo", re.compile(r"\bodoo\b", re.I)),
    ("zoho", re.compile(r"\bzoho\b", re.I)),
    ("sap", re.compile(r"\bsap\b", re.I)),
    ("erpnext", re.compile(r"\berp\s*next\b|\berpnext\b", re.I)),
    ("1c", re.compile(r"\b1[\s-]?c\b|\b1с\b", re.I)),
)

_CONFUSED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("en_dont_understand", re.compile(r"\b(i\s+)?don'?t\s+understand\b|\bconfused\b", re.I)),
    ("en_what_mean", re.compile(r"\bwhat\s+do\s+you\s+mean\b", re.I)),
    ("ru_confused", re.compile(r"не\s+понял|не\s+понимаю|непонятно|не\s+ясно|поясни\s+проще", re.I)),
    ("de_confused", re.compile(r"was\s+meinst\s+du|verstehe\s+nicht", re.I)),
)

_PRICING_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("en_price", re.compile(r"\b(price|pricing|cost|budget)\b|\bhow\s+much\b", re.I)),
    ("ru_price", re.compile(r"сколько\s+стоит|стоимост|цена|прайс", re.I)),
    ("de_price", re.compile(r"\bpreis\b|was\s+kostet", re.I)),
)

_IMPLEMENTATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("en_get_started", re.compile(r"\bget\s+started\b|\bhow\s+(to|do\s+i)\s+start\b", re.I)),
    ("en_want_implement", re.compile(r"\bwant\s+to\s+implement\b|\bneed\s+(an?\s+)?assistant\b", re.I)),
    ("en_need_bot", re.compile(r"\bneed\s+(a\s+)?bot\b|\bbook\s+a\s+call\b", re.I)),
    ("en_start_project", re.compile(
        r"\bstart\s+(the\s+)?project\b|\blet'?s\s+start\b|\bwant\s+to\s+start\b",
        re.I,
    )),
    ("ru_implement", re.compile(r"как\s+начать|хочу\s+внедрить|начать\s+проект|нужен\s+бот", re.I)),
    ("ru_order", re.compile(r"\bзаказать\b", re.I)),
    ("generic_need_integration", re.compile(r"\bneed\s+integration\b|\bнужна\s+интеграция\b", re.I)),
)

_TECHNICAL_HOW_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "en_how_api",
        re.compile(
            r"\bhow\s+(does|do|can|would|is)\b.{0,80}\b(api|webhook|integration)\b",
            re.I | re.S,
        ),
    ),
    ("en_how_work", re.compile(r"\bhow\s+.{0,60}\bwork(s)?\b", re.I | re.S)),
    ("en_explain_api", re.compile(r"\bexplain\b.{0,40}\b(api|webhook|integration)\b", re.I | re.S)),
    ("ru_how_works", re.compile(r"как\s+работает|как\s+.{0,40}(api|webhook|интеграц)", re.I | re.S)),
)

_TECHNICAL_INTEREST_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("api", re.compile(r"\bapi\b", re.I)),
    ("webhook", re.compile(r"\bwebhook", re.I)),
    ("crm", re.compile(r"\bcrm\b", re.I)),
    ("n8n", re.compile(r"\bn8n\b", re.I)),
    ("integration", re.compile(r"\bintegration\b|\bинтеграц", re.I)),
    ("postgres", re.compile(r"\bpostgres", re.I)),
    ("assistant_product", re.compile(r"\bassistant\b|\bассистент", re.I)),
    ("channel", re.compile(r"\btelegram\b|\bwhatsapp\b|\bweb\s*chat\b", re.I)),
    ("how_technical", re.compile(r"\bhow\s+does\b.{0,40}\bwork\b", re.I | re.S)),
    ("ru_technical", re.compile(r"техническ|архитектур|как\s+это\s+работает", re.I)),
)

_OFF_TOPIC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("weather", re.compile(r"\bweather\b|погод", re.I)),
    ("recipe", re.compile(r"\brecipe\b|рецепт", re.I)),
    ("sports", re.compile(r"\bfootball\b|футбол", re.I)),
    ("trivia", re.compile(r"\bcapital\s+of\b|\bwho\s+is\s+the\s+president\b", re.I)),
)

_PRODUCT_SCOPE_TOKENS = re.compile(
    r"\b(crm|api|webhook|n8n|bot|alpstein|telegram|whatsapp|assistant|"
    r"интеграц|ассистент|битрикс|salesforce)\b",
    re.I,
)

_SOCIAL_GREETING_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("en_hello", re.compile(r"^(hi|hello|hey|thanks|thank\s+you)\b", re.I)),
    ("ru_hello", re.compile(r"^(привет|здравств|добрый\s+день|спасибо)\b", re.I)),
    ("de_hello", re.compile(r"^(hallo|danke)\b", re.I)),
)

class ConversationIntentService:
    """Heuristic intent resolver for a single customer turn."""

    def resolve(
        self,
        *,
        current_customer_message: str,
        history: ConversationHistory | None = None,
    ) -> ConversationIntentResolution:
        current = current_customer_message.strip()
        previous = _previous_customer_message(history, current_customer_message=current)

        if current and _is_short_reply(current) and previous:
            inherited = _resolve_inheritable_intents(previous)
            if inherited is not None:
                return ConversationIntentResolution(
                    intent=inherited.intent,
                    matched_rule=f"inherit:{inherited.matched_rule}",
                    used_previous_message=True,
                )

        return _resolve_message(current)


def _resolve_inheritable_intents(text: str) -> ConversationIntentResolution | None:
    """Priorities 1–4 only — for short-reply inheritance (spec §7.4)."""
    normalized = text.strip()
    if not normalized:
        return None

    lowered = _normalize_for_matching(normalized)

    matched = _match_confused(lowered)
    if matched:
        return ConversationIntentResolution(
            intent=ConversationIntent.CONFUSED_CUSTOMER,
            matched_rule=matched,
        )

    matched = _match_pricing(lowered)
    if matched:
        return ConversationIntentResolution(
            intent=ConversationIntent.PRICING_INTEREST,
            matched_rule=matched,
        )

    matched = _match_implementation(lowered)
    if matched:
        return ConversationIntentResolution(
            intent=ConversationIntent.IMPLEMENTATION_INTEREST,
            matched_rule=matched,
        )

    named = _detect_named_system(lowered)
    if named and not _is_technical_how_about_system(lowered):
        return ConversationIntentResolution(
            intent=ConversationIntent.UNSUPPORTED_SYSTEM,
            matched_rule=f"unsupported_system:named_{named}",
        )

    return None


def _resolve_message(text: str) -> ConversationIntentResolution:
    normalized = text.strip()
    if not normalized:
        return ConversationIntentResolution(
            intent=ConversationIntent.TECHNICAL_INTEREST,
            matched_rule="default:empty_message",
        )

    lowered = _normalize_for_matching(normalized)

    matched = _match_confused(lowered)
    if matched:
        return ConversationIntentResolution(
            intent=ConversationIntent.CONFUSED_CUSTOMER,
            matched_rule=matched,
        )

    matched = _match_pricing(lowered)
    if matched:
        return ConversationIntentResolution(
            intent=ConversationIntent.PRICING_INTEREST,
            matched_rule=matched,
        )

    matched = _match_implementation(lowered)
    if matched:
        return ConversationIntentResolution(
            intent=ConversationIntent.IMPLEMENTATION_INTEREST,
            matched_rule=matched,
        )

    named = _detect_named_system(lowered)
    if named and not _is_technical_how_about_system(lowered):
        return ConversationIntentResolution(
            intent=ConversationIntent.UNSUPPORTED_SYSTEM,
            matched_rule=f"unsupported_system:named_{named}",
        )

    matched = _match_technical(lowered)
    if matched:
        return ConversationIntentResolution(
            intent=ConversationIntent.TECHNICAL_INTEREST,
            matched_rule=matched,
        )

    matched = _match_off_topic(lowered)
    if matched:
        return ConversationIntentResolution(
            intent=ConversationIntent.OFF_TOPIC,
            matched_rule=matched,
        )

    matched = _match_social_greeting(lowered)
    if matched:
        return ConversationIntentResolution(
            intent=ConversationIntent.SOCIAL_GREETING,
            matched_rule=matched,
        )

    return ConversationIntentResolution(
        intent=ConversationIntent.TECHNICAL_INTEREST,
        matched_rule="default:technical_interest",
    )


def _normalize_for_matching(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip().lower())
    return collapsed


def _is_short_reply(text: str) -> bool:
    words = text.split()
    return len(words) <= SHORT_REPLY_MAX_WORDS or len(text) <= SHORT_REPLY_MAX_CHARS


def _previous_customer_message(
    history: ConversationHistory | None,
    *,
    current_customer_message: str,
) -> str | None:
    if history is None or not history.messages:
        return None

    messages = history.messages
    last = messages[-1]
    if (
        last.sender_type == "customer"
        and last.message_text.strip() == current_customer_message.strip()
    ):
        prior = messages[:-1]
    else:
        prior = messages

    for message in reversed(prior):
        if message.sender_type == "customer":
            body = message.message_text.strip()
            if body:
                return body
    return None


def _detect_named_system(text: str) -> str | None:
    for system_id, pattern in _NAMED_SYSTEM_PATTERNS:
        if pattern.search(text):
            return system_id
    return None


def _is_technical_how_about_system(text: str) -> bool:
    if not _detect_named_system(text):
        return False
    return _first_matching_rule(text, _TECHNICAL_HOW_PATTERNS) is not None


def _match_implementation(text: str) -> str | None:
    named = _detect_named_system(text)
    for rule_id, pattern in _IMPLEMENTATION_PATTERNS:
        if rule_id == "generic_need_integration" and named:
            continue
        if pattern.search(text):
            return f"implementation_interest:{rule_id}"
    return None


def _match_confused(text: str) -> str | None:
    return _first_matching_rule(text, _CONFUSED_PATTERNS)


def _match_pricing(text: str) -> str | None:
    return _first_matching_rule(text, _PRICING_PATTERNS)


def _match_technical(text: str) -> str | None:
    if _is_technical_how_about_system(text):
        rule = _first_matching_rule(text, _TECHNICAL_HOW_PATTERNS)
        if rule:
            return f"technical_interest:{rule}"
    rule = _first_matching_rule(text, _TECHNICAL_INTEREST_PATTERNS)
    if rule:
        return f"technical_interest:{rule}"
    return None


def _match_off_topic(text: str) -> str | None:
    if _PRODUCT_SCOPE_TOKENS.search(text):
        return None
    return _first_matching_rule(text, _OFF_TOPIC_PATTERNS)


def _match_social_greeting(text: str) -> str | None:
    if _match_pricing(text) or _match_technical(text) or _detect_named_system(text):
        return None
    if len(text) > 80:
        return None
    return _first_matching_rule(text, _SOCIAL_GREETING_PATTERNS)


def _first_matching_rule(
    text: str,
    patterns: tuple[tuple[str, re.Pattern[str]], ...],
) -> str | None:
    for rule_id, pattern in patterns:
        if pattern.search(text):
            return rule_id
    return None
