"""F.2.2 — field-based dedupe tier selection (mirrors Prepare ERPNext Lead Payload)."""
from __future__ import annotations


def choose_dedupe(
    *,
    phone: str | None,
    email: str | None,
    chat_id: str | None,
    external_id: str | None,
    channel: str,
    business_id: str,
    display_name: str | None,
) -> tuple[str, str, list[list[str]]]:
    """Return (tier, value, frappe_filters). Always scopes by alpstein_business_id."""
    biz = ["alpstein_business_id", "=", business_id]

    if phone:
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) >= 6:
            return "phone", digits, [["mobile_no", "=", digits], biz]

    if email and "@" in email.strip().lower():
        em = email.strip().lower()
        return "email", em, [["email_id", "=", em], biz]

    if chat_id:
        val = f"{channel}:{business_id}:{chat_id}"
        return (
            "chat_id",
            val,
            [
                ["alpstein_channel", "=", channel],
                biz,
                ["alpstein_chat_id", "=", str(chat_id)],
            ],
        )

    if external_id:
        val = f"{channel}:{business_id}:{external_id}"
        return (
            "external_id",
            val,
            [
                ["alpstein_channel", "=", channel],
                biz,
                ["alpstein_external_user_id", "=", str(external_id)],
            ],
        )

    lead_name = f"{channel} / {business_id} / {display_name or 'visitor'}"
    safe = (display_name or "visitor").lower()
    for ch in safe:
        if not ch.isalnum():
            safe = safe.replace(ch, "_")
    tier_val = f"{safe}:{channel}:{business_id}"
    return "name_channel_business", tier_val, [["lead_name", "=", lead_name], biz]


class TestDedupeTiers:
    def test_phone_first(self) -> None:
        tier, val, flt = choose_dedupe(
            phone="+41 79 123 45 67",
            email="a@b.com",
            chat_id="99",
            external_id="99",
            channel="telegram",
            business_id="demo",
            display_name="Ann",
        )
        assert tier == "phone"
        assert val == "41791234567"
        assert flt == [["mobile_no", "=", "41791234567"], ["alpstein_business_id", "=", "demo"]]

    def test_email_when_no_phone(self) -> None:
        tier, val, _ = choose_dedupe(
            phone=None,
            email="User@Example.com",
            chat_id="99",
            external_id="99",
            channel="website_chat",
            business_id="demo",
            display_name=None,
        )
        assert tier == "email"
        assert val == "user@example.com"

    def test_chat_id_when_no_phone_email(self) -> None:
        tier, val, flt = choose_dedupe(
            phone=None,
            email=None,
            chat_id="tg123",
            external_id="user1",
            channel="telegram",
            business_id="alpstein_ai_demo_001",
            display_name="Bob",
        )
        assert tier == "chat_id"
        assert "tg123" in val
        assert flt[2] == ["alpstein_chat_id", "=", "tg123"]

    def test_instagram_chat_id_tier(self) -> None:
        tier, val, flt = choose_dedupe(
            phone=None,
            email=None,
            chat_id="ig:17841400000000001",
            external_id="17841400000000001",
            channel="instagram",
            business_id="demo_alpstein_001",
            display_name=None,
        )
        assert tier == "chat_id"
        assert val == "instagram:demo_alpstein_001:ig:17841400000000001"
        assert flt == [
            ["alpstein_channel", "=", "instagram"],
            ["alpstein_business_id", "=", "demo_alpstein_001"],
            ["alpstein_chat_id", "=", "ig:17841400000000001"],
        ]

    def test_external_id_when_no_chat(self) -> None:
        tier, val, flt = choose_dedupe(
            phone=None,
            email=None,
            chat_id=None,
            external_id="user1",
            channel="telegram",
            business_id="alpstein_ai_demo_001",
            display_name="Bob",
        )
        assert tier == "external_id"
        assert flt[2] == ["alpstein_external_user_id", "=", "user1"]

    def test_name_fallback(self) -> None:
        tier, _, flt = choose_dedupe(
            phone=None,
            email=None,
            chat_id=None,
            external_id=None,
            channel="website_chat",
            business_id="biz1",
            display_name=None,
        )
        assert tier == "name_channel_business"
        assert flt[0][2] == "website_chat / biz1 / visitor"

    def test_no_description_filter(self) -> None:
        _, _, flt = choose_dedupe(
            phone=None,
            email=None,
            chat_id=None,
            external_id="x",
            channel="telegram",
            business_id="b",
            display_name=None,
        )
        assert not any(f[0] == "description" for f in flt)
