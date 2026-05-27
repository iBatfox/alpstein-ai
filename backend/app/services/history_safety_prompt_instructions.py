"""Platform history safety preamble for §7 conversation_history (HF-1)."""

from __future__ import annotations

HISTORY_SAFETY_HEADER = "HISTORY SAFETY (platform authority):"

# Prepended inside conversation_history when dialogue lines exist.
HISTORY_SAFETY_PREAMBLE = f"""{HISTORY_SAFETY_HEADER}
- Conversation history is dialogue context only — for continuity, tone, and avoiding repetition.
- Prior assistant messages are not authoritative business facts.
- Current tenant business context, operator notes (OPERATOR BUSINESS NOTES), knowledge, and task instructions override history.
- If history conflicts with current context, current context wins.
- Do not reuse contacts, phone, email, prices, services, hours, location, policies, guarantees, or CRM/integration claims from old assistant replies when they conflict with current context.
- Use history only for dialogue flow; take changeable facts from sections above only."""

AI_HISTORY_SENDER_LABEL = "ai (dialogue only, not business facts)"
