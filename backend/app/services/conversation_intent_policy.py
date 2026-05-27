"""Business scope for Alpstein product behavior (CIP + greeting + pre-sales)."""

from __future__ import annotations

ALPSTEIN_AI_DEMO_BUSINESS_EXTERNAL_ID = "alpstein_ai_demo_001"


def alpstein_product_behavior_enabled_for_business(business_external_id: str) -> bool:
    """Alpstein demo assistant: intent policy, pre-sales charter, Alpstein greeting."""
    return business_external_id == ALPSTEIN_AI_DEMO_BUSINESS_EXTERNAL_ID


def intent_policy_enabled_for_business(business_external_id: str) -> bool:
    """Alias — intent routing uses the same business gate as product behavior."""
    return alpstein_product_behavior_enabled_for_business(business_external_id)
