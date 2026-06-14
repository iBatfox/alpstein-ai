from app.services.orange_park_dialog_service import (
    ORANGE_PARK_CONTACT_RECEIVED_REPLY_UK,
    ORANGE_PARK_DIALOG_VERSION,
    ORANGE_PARK_START_WELCOME_UK,
    OrangeParkDialogService,
)


def _service() -> OrangeParkDialogService:
    return OrangeParkDialogService()


def _state(stage: str, **values):
    return {
        "dialog_engine_version": ORANGE_PARK_DIALOG_VERSION,
        "intent": values.pop("intent", "apartment_sales"),
        "stage": stage,
        "property_type": values.pop("property_type", None),
        "apartment_type": values.pop("apartment_type", None),
        "commercial_type": values.pop("commercial_type", None),
        "area_interest": values.pop("area_interest", None),
        "budget_interest": values.pop("budget_interest", None),
        "purpose": values.pop("purpose", None),
        "purchase_path": values.pop("purchase_path", None),
        "contact_requested": values.pop("contact_requested", False),
        "contact_received": values.pop("contact_received", False),
        **values,
    }


def test_start_resets_v3_state_and_is_ukrainian():
    result = _service().respond(
        "/start",
        previous_state=_state("manager_offer", contact_requested=True),
    )

    assert result.reply == ORANGE_PARK_START_WELCOME_UK
    assert result.reset_history is True
    assert result.state["stage"] == "idle"
    assert result.state["contact_requested"] is False


def test_about_project_answers_before_qualification():
    result = _service().respond("Розкажіть про ЖК")

    assert "Комфорт+" in result.reply
    assert "закритою територією" in result.reply
    assert result.reply.count("?") == 1
    assert result.state["intent"] == "about_project"
    assert result.request_contact is False


def test_apartment_interest_starts_with_type():
    result = _service().respond("Цікавить квартира")

    assert "Який тип квартири" in result.reply
    assert result.state["stage"] == "apartment_type"


def test_one_room_apartment_asks_for_area_without_live_availability_claim():
    result = _service().respond("Цікавить 1-кімнатна квартира")

    assert "35-41 м²" in result.reply
    assert "Яка площа" in result.reply
    assert result.state["apartment_type"] == "1-room"
    assert result.state["stage"] == "apartment_area"


def test_two_three_and_four_room_markers_start_typed_area_path():
    cases = (
        ("Я шукаю двокімнатну квартиру", "2-room"),
        ("Цікавить 3 кімнатна квартира", "3-room"),
        ("Потрібна чотирикімнатна квартира", "4-room"),
    )

    for text, apartment_type in cases:
        result = _service().respond(text)
        assert result.state["apartment_type"] == apartment_type
        assert result.state["stage"] == "apartment_area"
        assert "Яка площа" in result.reply


def test_numeric_area_advances_only_active_area_slot():
    result = _service().respond(
        "40",
        previous_state=_state("apartment_area", apartment_type="1-room"),
    )

    assert result.state["area_interest"] == "40"
    assert result.state["stage"] == "apartment_purpose"
    assert "проживання чи інвестиції" in result.reply


def test_two_room_area_uses_non_live_reference_range():
    result = _service().respond(
        "60",
        previous_state=_state("apartment_area", apartment_type="2-room"),
    )

    assert result.state["area_interest"] == "60"
    assert "56-64 м²" in result.reply
    assert "поточну наявність" in result.reply.casefold()


def test_purpose_consumes_area_stage_without_resetting_to_root():
    result = _service().respond(
        "Для проживання",
        previous_state=_state("apartment_area", apartment_type="2-room"),
    )

    assert result.state["intent"] == "apartment_sales"
    assert result.state["stage"] == "purchase_path"
    assert result.state["apartment_type"] == "2-room"
    assert result.state["purpose"] == "living"


def test_numeric_message_from_idle_is_not_interpreted_as_area():
    result = _service().respond("40")

    assert result.state["stage"] == "idle"
    assert "40 м²" not in result.reply


def test_purchase_terms_lists_general_paths_without_contact_request():
    result = _service().respond("Які є умови покупки?")

    assert "повна оплата" in result.reply
    assert "розтермінування" in result.reply
    assert "єОселя" in result.reply
    assert result.state["stage"] == "purchase_path"
    assert result.request_contact is False


def test_generic_purchase_path_is_consumed():
    result = _service().respond(
        "Повна оплата",
        previous_state=_state("purchase_path", intent="purchase_terms"),
    )

    assert result.state["purchase_path"] == "full_payment"
    assert result.state["stage"] == "manager_offer"
    assert result.request_contact is False


def test_all_documented_purchase_paths_are_consumed():
    cases = (
        ("Повна оплата", "full_payment"),
        ("Розтермінування", "installment"),
        ("єОселя", "e_oselya"),
        ("Банківське фінансування", "financing"),
        ("Житловий ваучер", "voucher"),
    )

    for text, expected in cases:
        result = _service().respond(
            text,
            previous_state=_state("purchase_path", intent="purchase_terms"),
        )
        assert result.state["purchase_path"] == expected
        assert result.state["stage"] == "manager_offer"
        assert result.request_contact is False
        assert "поточн" in result.reply.casefold()


def test_installment_explains_limits_then_offers_manager():
    result = _service().respond("Цікавить розтермінування")

    assert "перший внесок" in result.reply.casefold()
    assert "поточний розрахунок" in result.reply
    assert result.state["purchase_path"] == "installment"
    assert result.state["stage"] == "manager_offer"
    assert result.request_contact is False


def test_eoselia_explains_limits_then_offers_manager():
    result = _service().respond("Чи працює єОселя?")

    assert "не" not in result.reply[:20].casefold()
    assert "Вимоги програми" in result.reply
    assert result.state["purchase_path"] == "e_oselya"
    assert result.request_contact is False


def test_commercial_interest_starts_qualification():
    result = _service().respond("Цікавить комерційне приміщення")

    assert "типу бізнесу" in result.reply
    assert result.state["intent"] == "commercial_sales"
    assert result.state["stage"] == "commercial_business_type"


def test_about_project_qualification_is_consumed():
    result = _service().respond(
        "Шукаю для проживання",
        previous_state=_state("qualification", intent="about_project"),
    )

    assert result.state["intent"] == "apartment_sales"
    assert result.state["stage"] == "apartment_type"
    assert result.state["purpose"] == "living"


def test_live_smoke_apartment_phrase_consumes_type_and_purpose():
    result = _service().respond(
        "Я для себе шукаю для проживання двокімнатну квартиру",
        previous_state=_state("apartment_type", intent="apartment_sales"),
    )

    assert result.state["apartment_type"] == "2-room"
    assert result.state["purpose"] == "living"
    assert result.state["stage"] == "purchase_path"
    assert "Який спосіб придбання" in result.reply


def test_location_uses_stable_fact_and_one_question():
    result = _service().respond("Де знаходиться Orange Park?")

    assert "вул. Одеська, 23" in result.reply
    assert result.reply.count("?") == 1


def test_transport_uses_stable_fact_and_one_question():
    result = _service().respond("Як з транспортом до метро?")

    assert "Теремки" in result.reply
    assert result.reply.count("?") == 1


def test_white_box_uses_stable_facts():
    result = _service().respond("Що входить у White Box?")

    assert "стяжку" in result.reply
    assert "індивідуальне опалення" in result.reply


def test_parking_does_not_claim_availability():
    result = _service().respond("Чи є парковка?")

    assert "Наявність і умови" in result.reply
    assert result.request_contact is False


def test_shelter_requires_current_confirmation():
    result = _service().respond("Чи є укриття?")

    assert "поточну готовність" in result.reply
    assert result.request_contact is False


def test_direct_manager_request_immediately_requests_native_contact():
    result = _service().respond("Хочу, щоб менеджер зв'язався")

    assert result.request_contact is True
    assert result.state["stage"] == "awaiting_contact"
    assert "Поділитися номером" in result.reply


def test_manager_offer_advances_on_yes_only_when_active():
    result = _service().respond(
        "Так",
        previous_state=_state("manager_offer", intent="purchase_terms"),
    )

    assert result.request_contact is True


def test_telegram_contact_payload_completes_without_surname_question():
    result = _service().respond(
        "[telegram_contact_shared]",
        previous_state=_state("awaiting_contact", contact_requested=True),
        contact_received=True,
    )

    assert result.reply == ORANGE_PARK_CONTACT_RECEIVED_REPLY_UK
    assert "прізвище" not in result.reply.casefold()
    assert result.state["contact_received"] is True


def test_stale_old_metadata_is_ignored():
    result = _service().respond(
        "Так",
        previous_state={
            "dialog_engine_version": "legacy_version",
            "stage": "manager_offer",
        },
    )

    assert result.request_contact is False
    assert result.state["stage"] == "idle"


def test_yes_from_idle_does_not_request_contact():
    result = _service().respond("Так")

    assert result.request_contact is False
    assert "Поділитися номером" not in result.reply


def test_plus_from_idle_uses_documented_unknown_fallback():
    result = _service().respond("+")

    assert result.request_contact is False
    assert result.reply == (
        "Підкажіть, будь ласка, що саме вас цікавить: квартира, комерційне "
        "приміщення чи умови придбання?"
    )


def test_manual_phone_from_idle_does_not_request_contact():
    result = _service().respond("+380 67 111 22 33")

    assert result.request_contact is False
    assert result.state["intent"] == "unknown"
    assert result.state["stage"] == "idle"


def test_commercial_qualification_reaches_manager_offer_with_context():
    business = _service().respond(
        "Кав'ярня",
        previous_state=_state(
            "commercial_business_type",
            intent="commercial_sales",
            property_type="commercial",
        ),
    )
    area = _service().respond("Близько 60 м²", previous_state=business.state)
    purpose = _service().respond("Для власного бізнесу", previous_state=area.state)

    assert purpose.state["commercial_type"] == "Кав'ярня"
    assert purpose.state["area_interest"] == "Близько 60 м²"
    assert purpose.state["purpose"] == "Для власного бізнесу"
    assert purpose.state["stage"] == "manager_offer"
