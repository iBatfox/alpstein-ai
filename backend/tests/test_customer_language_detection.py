import pytest

from app.services.customer_language_detection import (
    detect_language_from_message_text,
    extract_telegram_language_code,
    resolve_reply_language,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hallo, wie sind Ihre Öffnungszeiten?", "de"),
        ("Hello, what are your opening hours?", "en"),
        ("Привет, во сколько вы открыты?", "ru"),
        ("Bonjour, quelles sont vos heures d'ouverture?", "fr"),
        ("Ciao, quali sono gli orari di apertura?", "it"),
        ("Hola, ¿cuál es el horario de apertura?", "es"),
        ("Привіт, о котрій ви відкриваєтесь?", "uk"),
    ],
)
def test_detect_language_from_customer_message(text: str, expected: str):
    assert detect_language_from_message_text(text) == expected


def test_resolve_reply_language_prefers_message_over_telegram_code():
    assert (
        resolve_reply_language(
            customer_message_text="Привет",
            telegram_language_code="de",
        )
        == "ru"
    )


def test_resolve_reply_language_uses_telegram_when_message_unclear():
    assert (
        resolve_reply_language(
            customer_message_text="👍",
            telegram_language_code="fr",
        )
        == "fr"
    )


def test_resolve_reply_language_defaults_to_english():
    assert resolve_reply_language(customer_message_text="👍") == "en"


def test_extract_telegram_language_code_from_nested_message():
    payload = {
        "message": {
            "from": {"id": 1, "language_code": "uk"},
            "text": "Hi",
        }
    }
    assert extract_telegram_language_code(payload) == "uk"
