"""Adapter monitoring observability API schemas (E3.3b / E3.4b)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

FORBIDDEN_ADAPTER_RESPONSE_FIELDS = frozenset(
    {
        "raw_payload",
        "provider_payload",
        "api_key",
        "secret",
        "bot_token",
        "password",
        "message_text",
        "prompt",
        "system_prompt",
    }
)

AdapterStatusValue = Literal["healthy", "warning", "degraded", "inactive"]
ContainmentStatusValue = Literal[
    "normal",
    "contained",
    "peer_at_risk",
    "shared_at_risk",
]
IsolationStatusValue = Literal["intact", "at_risk", "unknown"]


class AdapterDeliveryBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_by_status: dict[str, int]


class PeerAdapterSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter: str
    status: AdapterStatusValue
    ingress_status: AdapterStatusValue
    delivery_status: AdapterStatusValue
    containment_status: ContainmentStatusValue


class AdapterHealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter: str
    status: AdapterStatusValue
    status_reasons: list[str]
    ingress_status: AdapterStatusValue
    delivery_status: AdapterStatusValue
    ingress_status_reasons: list[str]
    delivery_status_reasons: list[str]
    containment_status: ContainmentStatusValue
    recent_messages: int
    ingress_failed_count: int
    ingress_retry_count: int
    ingress_dead_letter_count: int
    delivery_success_count: int
    delivery_failure_count: int
    delivery_pending_count: int
    retry_count: int
    dead_letter_count: int
    rate_limit_violation_count: int = 0
    delivery_failure_rate: float | None = None
    last_activity_at: datetime | None = None
    evaluated_at: datetime | None = None
    breakdown: AdapterDeliveryBreakdown | None = None
    peer_adapter: PeerAdapterSummary | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            forbidden = FORBIDDEN_ADAPTER_RESPONSE_FIELDS.intersection(data.keys())
            if forbidden:
                raise ValueError(
                    f"Forbidden adapter response fields: {', '.join(sorted(forbidden))}"
                )
        return data


class IsolationSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    isolation_status: IsolationStatusValue
    spread_risk: bool
    affected_adapters: list[str]
    healthy_adapters: list[str]
    inactive_adapters: list[str]
    containment_notes: list[str]


class AdapterHealthListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_hours: int
    isolation_summary: IsolationSummaryResponse
    items: list[AdapterHealthResponse]


class AdapterHealthListSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: AdapterHealthListResponse


class AdapterHealthSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: AdapterHealthResponse
