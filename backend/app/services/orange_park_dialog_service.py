"""Deterministic Orange Park v3 dialog routing and state transitions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

ORANGE_PARK_DIALOG_VERSION = "orange_park_v3"
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
ORANGE_PARK_CONTACT_BUTTON_REPLY_UK = (
    "Для зв'язку з менеджером натисніть кнопку «📱 Поділитися номером»."
)
ORANGE_PARK_CONTACT_RECEIVED_REPLY_UK = (
    "Дякуємо. Запит передано менеджеру. Очікуйте дзвінок."
)
ORANGE_PARK_PURCHASE_TERMS_REPLY_UK = (
    "Доступні повна оплата, розтермінування, єОселя, банківські програми та "
    "житлові ваучери. Точні актуальні умови, ставки, знижки й розрахунки "
    "підтвердить менеджер.\n\n"
    "Який варіант вам ближчий: повна оплата, розтермінування чи фінансування?"
)

_NUMBER_RE = re.compile(r"^\s*(\d{1,3})(?:\s*(?:м2|м²|кв\.?\s*м))?\s*$", re.I)
ORANGE_PARK_UNKNOWN_REPLY_UK = (
    "Підкажіть, будь ласка, що саме вас цікавить: квартира, комерційне "
    "приміщення чи умови придбання?"
)
ORANGE_PARK_PURCHASE_PATH_QUESTION_UK = (
    "Який спосіб придбання розглядаєте: повна оплата, розтермінування чи "
    "фінансування?"
)


@dataclass(frozen=True)
class OrangeParkDialogResult:
    reply: str
    state: dict[str, Any]
    request_contact: bool = False
    reset_history: bool = False


class OrangeParkDialogService:
    def respond(
        self,
        text: str,
        *,
        previous_state: dict[str, Any] | None = None,
        contact_received: bool = False,
    ) -> OrangeParkDialogResult:
        normalized = " ".join(text.casefold().replace("’", "'").replace("ʼ", "'").split())
        state = _valid_state(previous_state)

        if normalized == "/start" or normalized.startswith("/start "):
            return OrangeParkDialogResult(
                reply=ORANGE_PARK_START_WELCOME_UK,
                state=_state(intent="unknown", stage="idle"),
                reset_history=True,
            )

        if contact_received:
            return OrangeParkDialogResult(
                reply=ORANGE_PARK_CONTACT_RECEIVED_REPLY_UK,
                state={
                    **state,
                    "stage": "completed",
                    "contact_requested": True,
                    "contact_received": True,
                },
            )

        if _is_manager_request(normalized):
            return self._manager_contact(state, intent="manager_contact")

        if normalized in {"так", "ок", "добре", "давай", "+"}:
            if state.get("stage") == "manager_offer":
                return self._manager_contact(state, intent="manager_contact")
            return OrangeParkDialogResult(
                reply=ORANGE_PARK_UNKNOWN_REPLY_UK,
                state=_state(intent="unknown", stage="idle"),
            )

        purpose = _purpose(normalized)
        if (
            purpose is not None
            and state.get("stage")
            in {
                "qualification",
                "apartment_type",
                "apartment_area",
                "apartment_purpose",
            }
            and _apartment_type(normalized) is None
        ):
            apartment_type = state.get("apartment_type")
            if apartment_type:
                return OrangeParkDialogResult(
                    reply=ORANGE_PARK_PURCHASE_PATH_QUESTION_UK,
                    state={
                        **state,
                        "intent": "apartment_sales",
                        "stage": "purchase_path",
                        "property_type": "apartment",
                        "purpose": purpose,
                    },
                )
            return OrangeParkDialogResult(
                reply=(
                    "Зрозуміло. Який формат квартири вас цікавить: "
                    "1-, 2-, 3- чи 4-кімнатна?"
                ),
                state={
                    **state,
                    "intent": "apartment_sales",
                    "stage": "apartment_type",
                    "property_type": "apartment",
                    "purpose": purpose,
                },
            )

        number = _NUMBER_RE.fullmatch(normalized)
        if number and state.get("stage") == "apartment_area":
            area = int(number.group(1))
            apartment_type = state.get("apartment_type")
            area_context = (
                " Для 2-кімнатних квартир довідковий діапазон становить "
                "56-64 м²; це не підтвердження поточної наявності."
                if apartment_type == "2-room"
                else ""
            )
            if state.get("purpose"):
                return OrangeParkDialogResult(
                    reply=(
                        f"Зафіксував бажану площу близько {area} м²."
                        f"{area_context} Поточну наявність конкретних квартир "
                        "підтвердить менеджер.\n\n"
                        f"{ORANGE_PARK_PURCHASE_PATH_QUESTION_UK}"
                    ),
                    state={
                        **state,
                        "stage": "purchase_path",
                        "area_interest": str(area),
                    },
                )
            return OrangeParkDialogResult(
                reply=(
                    f"Зафіксував бажану площу близько {area} м²."
                    f"{area_context} Поточну наявність конкретних квартир "
                    "підтвердить менеджер.\n\n"
                    "Розглядаєте квартиру для проживання чи інвестиції?"
                ),
                state={
                    **state,
                    "stage": "apartment_purpose",
                    "area_interest": str(area),
                },
            )

        if state.get("stage") == "purchase_path":
            purchase_path = _purchase_path(normalized)
            if purchase_path is None:
                return OrangeParkDialogResult(
                    reply=(
                        "Оберіть, будь ласка, варіант: повна оплата, "
                        "розтермінування чи фінансування?"
                    ),
                    state=state,
                )
            return OrangeParkDialogResult(
                reply=_purchase_path_reply(purchase_path),
                state={
                    **state,
                    "stage": "manager_offer",
                    "purchase_path": purchase_path,
                },
            )

        if state.get("stage") == "commercial_business_type":
            return OrangeParkDialogResult(
                reply="Який формат або орієнтовна площа приміщення вам потрібні?",
                state={
                    **state,
                    "stage": "commercial_format",
                    "commercial_type": text.strip()[:200],
                },
            )

        if state.get("stage") == "commercial_format":
            return OrangeParkDialogResult(
                reply="Розглядаєте приміщення для власного бізнесу, оренди чи інвестиції?",
                state={
                    **state,
                    "stage": "commercial_purpose",
                    "area_interest": text.strip()[:100],
                },
            )

        if state.get("stage") == "commercial_purpose":
            return OrangeParkDialogResult(
                reply=(
                    "Дякую, цього контексту достатньо для підбору поточних "
                    "приміщень і цін.\n\nПідключити менеджера?"
                ),
                state={**state, "stage": "manager_offer", "purpose": text.strip()[:100]},
            )

        purchase_path = _purchase_path(normalized)
        if purchase_path is not None:
            return OrangeParkDialogResult(
                reply=_purchase_path_reply(purchase_path),
                state={
                    **_state(intent="purchase_terms", stage="manager_offer"),
                    "purchase_path": purchase_path,
                },
            )

        if _is_purchase_terms(normalized):
            return OrangeParkDialogResult(
                reply=ORANGE_PARK_PURCHASE_TERMS_REPLY_UK,
                state=_state(intent="purchase_terms", stage="purchase_path"),
            )

        if _is_commercial(normalized):
            return OrangeParkDialogResult(
                reply=(
                    "В Orange Park передбачені фасадні комерційні приміщення на "
                    "перших поверхах, із зручними входами та парковочною зоною.\n\n"
                    "Для якого типу бізнесу шукаєте приміщення?"
                ),
                state=_state(
                    intent="commercial_sales",
                    stage="commercial_business_type",
                    property_type="commercial",
                ),
            )

        if _is_apartment(normalized):
            apartment_type = _apartment_type(normalized)
            if apartment_type:
                type_label = {
                    "1-room": "1-кімнатну",
                    "2-room": "2-кімнатну",
                    "3-room": "3-кімнатну",
                    "4-room": "4-кімнатну",
                }[apartment_type]
                detail = (
                    " Для 1-кімнатних квартир орієнтир за площею становить "
                    "35-41 м², а актуальну наявність потрібно уточнювати."
                    if apartment_type == "1-room"
                    else (
                        " Для 2-кімнатних квартир довідковий діапазон становить "
                        "56-64 м²; це не підтвердження поточної наявності."
                        if apartment_type == "2-room"
                        else ""
                    )
                )
                explicit_purpose = _purpose(normalized) or state.get("purpose")
                if explicit_purpose:
                    return OrangeParkDialogResult(
                        reply=(
                            f"Зафіксував {type_label} квартиру.{detail}\n\n"
                            f"{ORANGE_PARK_PURCHASE_PATH_QUESTION_UK}"
                        ),
                        state={
                            **_state(
                                intent="apartment_sales",
                                stage="purchase_path",
                                property_type="apartment",
                                purpose=explicit_purpose,
                            ),
                            "apartment_type": apartment_type,
                        },
                    )
                return OrangeParkDialogResult(
                    reply=(
                        f"Зафіксував {type_label} квартиру.{detail}\n\n"
                        "Яка площа вам ближча?"
                    ),
                    state={
                        **_state(
                            intent="apartment_sales",
                            stage="apartment_area",
                            property_type="apartment",
                            purpose=None,
                        ),
                        "apartment_type": apartment_type,
                        "area_interest": None,
                    },
                )
            return OrangeParkDialogResult(
                reply=(
                    "В Orange Park є різні формати квартир, зокрема 1-, 2-, "
                    "3-кімнатні, дворівневі та квартири з патіо. Точна наявність "
                    "змінюється.\n\nЯкий тип квартири вас цікавить?"
                ),
                state=_state(
                    intent="apartment_sales",
                    stage="apartment_type",
                    property_type="apartment",
                ),
            )

        if state.get("stage") == "apartment_type":
            return OrangeParkDialogResult(
                reply="Оберіть, будь ласка: 1-, 2-, 3- чи 4-кімнатна квартира?",
                state=state,
            )

        if state.get("stage") == "qualification":
            return OrangeParkDialogResult(
                reply=ORANGE_PARK_UNKNOWN_REPLY_UK,
                state=state,
            )

        if state.get("stage") == "apartment_purpose":
            return OrangeParkDialogResult(
                reply="Розглядаєте квартиру для проживання чи інвестиції?",
                state=state,
            )

        fact_reply = _about_project_reply(normalized)
        if fact_reply:
            return OrangeParkDialogResult(
                reply=fact_reply,
                state=_state(intent="about_project", stage="qualification"),
            )

        return OrangeParkDialogResult(
            reply=(
                ORANGE_PARK_UNKNOWN_REPLY_UK
            ),
            state=_state(intent="unknown", stage="idle"),
        )

    def _manager_contact(
        self,
        state: dict[str, Any],
        *,
        intent: str,
    ) -> OrangeParkDialogResult:
        return OrangeParkDialogResult(
            reply=ORANGE_PARK_CONTACT_BUTTON_REPLY_UK,
            state={
                **state,
                "intent": intent,
                "stage": "awaiting_contact",
                "contact_requested": True,
                "contact_received": False,
            },
            request_contact=True,
        )


def _state(*, intent: str, stage: str, **values: Any) -> dict[str, Any]:
    return {
        "dialog_engine_version": ORANGE_PARK_DIALOG_VERSION,
        "intent": intent,
        "stage": stage,
        "property_type": values.get("property_type"),
        "apartment_type": values.get("apartment_type"),
        "commercial_type": values.get("commercial_type"),
        "area_interest": values.get("area_interest"),
        "budget_interest": values.get("budget_interest"),
        "purpose": values.get("purpose"),
        "purchase_path": values.get("purchase_path"),
        "contact_requested": False,
        "contact_received": False,
    }


def _valid_state(value: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, dict):
        return _state(intent="unknown", stage="idle")
    if value.get("dialog_engine_version") != ORANGE_PARK_DIALOG_VERSION:
        return _state(intent="unknown", stage="idle")
    return dict(value)


def _contains(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _is_manager_request(text: str) -> bool:
    return _contains(
        text,
        (
            "менеджер",
            "зв'яж",
            "зателефон",
            "передзвон",
            "контакт",
            "консультац",
            "перегляд",
            "актуальна ціна",
            "актуальні ціни",
            "ціна",
            "вартість",
            "скільки кошту",
            "наявність",
            "бюджет",
            "до 100000",
            "до 1000000",
            "до 1600000",
        ),
    )


def _is_purchase_terms(text: str) -> bool:
    return _contains(text, ("умови покуп", "умови придбан", "варіанти оплат", "фінансуван"))


def _is_installment(text: str) -> bool:
    return _contains(text, ("розтермін", "рассроч"))


def _is_eoselia(text: str) -> bool:
    return "єосел" in text or "еосел" in text


def _is_commercial(text: str) -> bool:
    return _contains(text, ("комерц", "приміщенн", "бізнес-приміщ"))


def _is_apartment(text: str) -> bool:
    return _contains(
        text,
        (
            "квартир",
            "1-кімнат",
            "1 кімнат",
            "однокімнат",
            "2-кімнат",
            "2 кімнат",
            "двокімнат",
            "3-кімнат",
            "3 кімнат",
            "трикімнат",
            "4-кімнат",
            "4 кімнат",
            "чотирикімнат",
            "патіо",
        ),
    )


def _apartment_type(text: str) -> str | None:
    if _contains(text, ("1-кімнат", "однокімнат", "1 кімнат")):
        return "1-room"
    if _contains(text, ("2-кімнат", "двокімнат", "2 кімнат")):
        return "2-room"
    if _contains(text, ("3-кімнат", "трикімнат", "3 кімнат")):
        return "3-room"
    if _contains(text, ("4-кімнат", "чотирикімнат", "4 кімнат")):
        return "4-room"
    return None


def _purpose(text: str) -> str | None:
    if _contains(text, ("інвест", "оренд", "перепрод")):
        return "investment"
    if _contains(text, ("прожив", "для себе", "сім", "жити")):
        return "living"
    return None


def _purchase_path(text: str) -> str | None:
    if _is_installment(text):
        return "installment"
    if _is_eoselia(text):
        return "e_oselya"
    if _contains(text, ("повна оплат", "повністю", "100%")):
        return "full_payment"
    if "ваучер" in text:
        return "voucher"
    if _contains(text, ("банк", "кредит", "фінансув")):
        return "financing"
    return None


def _purchase_path_reply(purchase_path: str) -> str:
    explanations = {
        "full_payment": (
            "Зафіксував повну оплату. Поточну ціну та умови для повної оплати "
            "потрібно підтвердити."
        ),
        "installment": (
            "Зафіксував розтермінування. Перший внесок, строк, доступні "
            "квартири та щомісячний платіж є поточними умовами."
        ),
        "e_oselya": (
            "Зафіксував єОселю. Вимоги програми, відповідність покупця та "
            "доступні квартири потрібно підтвердити."
        ),
        "financing": (
            "Зафіксував фінансування. Вимоги банку, погодження, ставки та "
            "доступні квартири залежать від поточної програми."
        ),
        "voucher": (
            "Зафіксував житловий ваучер. Прийняття ваучера, документи, оцінку "
            "та доступні квартири потрібно підтвердити."
        ),
    }
    return (
        f"{explanations[purchase_path]}\n\n"
        "Потрібно, щоб менеджер підготував або підтвердив поточний розрахунок?"
    )


def _about_project_reply(text: str) -> str | None:
    if _contains(text, ("транспорт", "метро", "маршрут", "дістати")):
        return (
            "Orange Park розташований у Крюківщині, приблизно за 5 км від Києва. "
            "Поруч є зупинка OrangePark і маршрути громадського транспорту; "
            "найближче метро в матеріалах комплексу — Теремки.\n\n"
            "Для вас важливіше сполучення з метро чи виїзд автомобілем?"
        )
    if _contains(text, ("white box", "вайт бокс", "оздоблен")):
        return (
            "White Box включає базову підготовку до фінального ремонту: стяжку, "
            "штукатурку, вікна, вхідні двері, радіатори, індивідуальне опалення "
            "та лічильники. Це скорочує обсяг чорнових робіт.\n\n"
            "Ви плануєте швидкий переїзд чи ремонт під власний дизайн?"
        )
    if _contains(text, ("парков", "авто", "машин")):
        return (
            "У комплексі передбачені наземні паркомісця по зовнішньому периметру, "
            "а внутрішні двори організовані без автомобілів. Наявність і умови "
            "паркування потрібно підтвердити.\n\nПаркування є важливим критерієм для вас?"
        )
    if _contains(text, ("укрит", "бомбосхов")):
        return (
            "В Orange Park передбачене укриття з вентиляцією, запасом "
            "води, освітленням, опаленням і Wi-Fi-зоною. Його поточну готовність "
            "та правила доступу має підтвердити менеджер.\n\n"
            "Потрібно уточнити актуальний стан укриття?"
        )
    if _contains(text, ("де знаход", "локац", "адрес", "розташован")):
        return (
            "Orange Park розташований у Крюківщині за адресою вул. Одеська, 23, "
            "приблизно за 5 км від Києва. Поруч є щоденна інфраструктура та "
            "транспортне сполучення.\n\nВи розглядаєте проживання чи інвестицію?"
        )
    if _contains(text, ("orange park", "жк", "комплекс", "розкаж")):
        return (
            "Orange Park — житловий комплекс класу Комфорт+ у Крюківщині із "
            "закритою територією, дворами без авто та власною інфраструктурою. "
            "Квартири у форматі White Box допомагають швидше перейти до "
            "фінального ремонту.\n\nЩо для вас важливіше: квартира для життя чи інвестиція?"
        )
    return None
