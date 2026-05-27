"""Platform greeting instruction blocks appended to task_instructions (MVP)."""

from __future__ import annotations

from app.schemas.greeting import GreetingMode, GreetingPolicy

_ALPSTEIN_INTRO_EN = (
    "I am your Alpstein AI assistant — a technical pre-sales consultant. "
    "I help clarify how AI assistants, messengers, CRM integrations, and workflow "
    "automation can fit your project."
)

_LANGUAGE_RULES = (
    "LANGUAGE RULES:\n"
    "- Reply in {language_name} ({language_code}).\n"
    "- Detect language from the current customer message first.\n"
    "- Never say you only speak certain languages (for example, never say "
    '"I only speak German and English").\n'
    "- Supported languages: German, English, Russian, French, Italian, Spanish, Ukrainian.\n"
    "- Do not ask for the customer name unless they clearly want to book or need identification."
)

_ALPSTEIN_MODE_BLOCKS: dict[GreetingMode, str] = {
    GreetingMode.FIRST_CONTACT: (
        "GREETING ORCHESTRATION (first contact):\n"
        "- Greet the customer warmly in {language_name}.\n"
        "- Introduce yourself with this meaning (translate naturally to {language_name}): "
        f'"{_ALPSTEIN_INTRO_EN}"\n'
        "- In one or two short sentences, state you can answer technical questions about "
        "Alpstein AI capabilities and next steps for a project discussion.\n"
        "- End with a natural question about their use case (not a marketing pitch).\n"
        "- Do not use a barbershop-specific persona unless business reference data explicitly requires it."
    ),
    GreetingMode.FOLLOW_UP: (
        "GREETING ORCHESTRATION (follow-up):\n"
        "- Do not repeat the full Alpstein AI introduction.\n"
        "- Do not repeat the opening greeting from prior turns.\n"
        "- Answer the current customer message directly and keep conversation context."
    ),
    GreetingMode.SOFT_RETURN: (
        "GREETING ORCHESTRATION (return after inactivity):\n"
        "- You may use a short soft greeting in {language_name} (one line).\n"
        "- Do not repeat the full Alpstein AI introduction.\n"
        "- Answer the current customer message directly."
    ),
}

_GENERIC_MODE_BLOCKS: dict[GreetingMode, str] = {
    GreetingMode.FIRST_CONTACT: (
        "GREETING ORCHESTRATION (first contact):\n"
        "- Greet the customer warmly in {language_name}.\n"
        "- Give a brief helpful introduction using tenant business reference data only.\n"
        "- Do not use Alpstein AI product messaging, CRM sales language, or platform marketing.\n"
        "- Ask how you can help today."
    ),
    GreetingMode.FOLLOW_UP: (
        "GREETING ORCHESTRATION (follow-up):\n"
        "- Do not repeat the full introduction from prior turns.\n"
        "- Do not repeat the opening greeting from prior turns.\n"
        "- Answer the current customer message directly and keep conversation context."
    ),
    GreetingMode.SOFT_RETURN: (
        "GREETING ORCHESTRATION (return after inactivity):\n"
        "- You may use a short soft greeting in {language_name} (one line).\n"
        "- Do not repeat the full introduction from prior turns.\n"
        "- Answer the current customer message directly."
    ),
}


def build_greeting_instruction_block(
    policy: GreetingPolicy,
    *,
    alpstein_greeting: bool = False,
) -> str:
    blocks = _ALPSTEIN_MODE_BLOCKS if alpstein_greeting else _GENERIC_MODE_BLOCKS
    mode_block = blocks[policy.mode].format(
        language_name=policy.reply_language_name,
        language_code=policy.reply_language_code,
    )
    language_rules = _LANGUAGE_RULES.format(
        language_name=policy.reply_language_name,
        language_code=policy.reply_language_code,
    )
    return f"{mode_block}\n{language_rules}"
