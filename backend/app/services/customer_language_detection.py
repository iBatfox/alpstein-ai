"""Detect customer reply language for greeting orchestration (MVP heuristics)."""

from __future__ import annotations

import re

from app.schemas.greeting import SUPPORTED_GREETING_LANGUAGE_CODES

DEFAULT_REPLY_LANGUAGE_CODE = "en"

LANGUAGE_NAMES: dict[str, str] = {
    "de": "German",
    "en": "English",
    "ru": "Russian",
    "fr": "French",
    "it": "Italian",
    "es": "Spanish",
    "uk": "Ukrainian",
}

_TELEGRAM_LANGUAGE_ALIASES: dict[str, str] = {
    "de": "de",
    "en": "en",
    "ru": "ru",
    "fr": "fr",
    "it": "it",
    "es": "es",
    "uk": "uk",
    "ua": "uk",
}

_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
_UKRAINIAN_CHARS_RE = re.compile(r"[іїєґІЇЄҐ]")
_RUSSIAN_SPECIFIC_RE = re.compile(r"[ёъыэЁЪЫЭ]")
_UKRAINIAN_WORD_HINT_RE = re.compile(
    r"\b(що|ти|так|ціна|ціни|цінами|цікавить|чому|російській|будь ласка|дякую|добрий|вітаю)\b",
    re.IGNORECASE,
)
_RUSSIAN_WORD_HINT_RE = re.compile(
    r"\b(что|ты|да|цена|стоимость|почему|русском|привет|пожалуйста|спасибо|свяжи|меня|давай|можешь)\b",
    re.IGNORECASE,
)

_GERMAN_HINT_RE = re.compile(
    r"(ä|ö|ü|ß|\b(hallo|danke|guten|morgen|tag|abend|bitte|termin)\b)",
    re.IGNORECASE,
)
_FRENCH_HINT_RE = re.compile(
    r"(à|â|ç|é|è|ê|ë|î|ï|ô|ù|û|ü|œ|\b(bonjour|merci|salut|jour)\b)",
    re.IGNORECASE,
)
_ITALIAN_HINT_RE = re.compile(
    r"(à|è|é|ì|ò|ù|\b(ciao|grazie|buongiorno|salve|prego)\b)",
    re.IGNORECASE,
)
_SPANISH_HINT_RE = re.compile(
    r"(ñ|¿|¡|\b(hola|gracias|buenos|días|tarde|por favor)\b)",
    re.IGNORECASE,
)


def normalize_language_code(code: str | None) -> str | None:
    if code is None:
        return None
    normalized = code.strip().lower().replace("_", "-")
    if not normalized:
        return None
    base = normalized.split("-", 1)[0]
    mapped = _TELEGRAM_LANGUAGE_ALIASES.get(base, base)
    if mapped in SUPPORTED_GREETING_LANGUAGE_CODES:
        return mapped
    return None


def detect_language_from_message_text(message_text: str) -> str | None:
    text = message_text.strip()
    if not text:
        return None

    if _CYRILLIC_RE.search(text):
        if _UKRAINIAN_CHARS_RE.search(text):
            return "uk"
        if _RUSSIAN_SPECIFIC_RE.search(text):
            return "ru"
        if _UKRAINIAN_WORD_HINT_RE.search(text):
            return "uk"
        if _RUSSIAN_WORD_HINT_RE.search(text):
            return "ru"
        return None

    if _GERMAN_HINT_RE.search(text):
        return "de"
    if _FRENCH_HINT_RE.search(text):
        return "fr"
    if _ITALIAN_HINT_RE.search(text):
        return "it"
    if _SPANISH_HINT_RE.search(text):
        return "es"

    if re.search(r"[A-Za-z]", text):
        return "en"

    return None


def extract_telegram_language_code(raw_payload: dict | None) -> str | None:
    if not raw_payload:
        return None

    candidates: list[object] = []
    message = raw_payload.get("message")
    if isinstance(message, dict):
        from_user = message.get("from")
        if isinstance(from_user, dict):
            candidates.append(from_user.get("language_code"))

    from_user = raw_payload.get("from")
    if isinstance(from_user, dict):
        candidates.append(from_user.get("language_code"))

    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = normalize_language_code(candidate)
            if normalized is not None:
                return normalized
    return None


def resolve_reply_language(
    *,
    customer_message_text: str,
    telegram_language_code: str | None = None,
    default_language_code: str | None = None,
) -> str:
    from_text = detect_language_from_message_text(customer_message_text)
    if from_text is not None:
        return from_text

    from_default = normalize_language_code(default_language_code)
    if from_default is not None:
        return from_default

    from_telegram = normalize_language_code(telegram_language_code)
    if from_telegram is not None:
        return from_telegram

    return DEFAULT_REPLY_LANGUAGE_CODE


def language_display_name(language_code: str) -> str:
    return LANGUAGE_NAMES.get(language_code, "English")
