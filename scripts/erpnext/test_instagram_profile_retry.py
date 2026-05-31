"""Checks for Instagram profile retry Lead update planning."""

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("retry_instagram_profile_lead.py")
SPEC = importlib.util.spec_from_file_location("retry_instagram_profile_lead", SCRIPT_PATH)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
build_update = MODULE.build_update


def test_profile_retry_updates_fallback_lead_name() -> None:
    lead = {
        "lead_name": "instagram user 800712929645409",
        "alpstein_external_user_id": "800712929645409",
    }
    profile = {
        "id": "800712929645409",
        "username": "example_user",
        "name": "Example User",
    }

    assert build_update(lead, profile) == {
        "instagram_username": "example_user",
        "instagram_display_name": "Example User",
        "lead_name": "Example User",
        "first_name": "Example User",
        "title": "Example User",
    }


def test_profile_retry_never_overwrites_existing_with_null_profile_data() -> None:
    lead = {
        "lead_name": "Existing Name",
        "alpstein_external_user_id": "800712929645409",
        "instagram_username": "existing_user",
        "instagram_display_name": "Existing Name",
    }
    profile = {
        "id": "800712929645409",
        "username": None,
        "name": None,
    }

    assert build_update(lead, profile) == {}


def test_profile_retry_adds_later_profile_without_renaming_non_fallback_lead() -> None:
    lead = {
        "lead_name": "Operator Chosen Name",
        "alpstein_external_user_id": "800712929645409",
    }
    profile = {
        "id": "800712929645409",
        "username": "example_user",
        "name": "Example User",
    }

    assert build_update(lead, profile) == {
        "instagram_username": "example_user",
        "instagram_display_name": "Example User",
    }
