"""Langfuse metadata field names for conversation intent (CIP-C wiring prep)."""

from __future__ import annotations

# Span / trace metadata keys — wired via ObservabilityContext (D2).
LANGFUSE_METADATA_CONVERSATION_INTENT = "conversation_intent"
LANGFUSE_METADATA_INTENT_MATCHED_RULE = "intent_matched_rule"

# Reserved for CIP-C (documented in conversation-intent-policy-mvp.md).
LANGFUSE_METADATA_INTENT_USED_PREVIOUS_MESSAGE = "intent_used_previous_message"
