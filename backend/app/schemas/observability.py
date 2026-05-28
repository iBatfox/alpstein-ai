"""Observability metadata contract (D2 — CIP-C / Phase D)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, fields, replace
from typing import Any

from app.core.config import LANGFUSE_DEV_ENVIRONMENTS, Settings, langfuse_tracing_active
from app.schemas.langfuse_intent_trace import (
    LANGFUSE_METADATA_CONVERSATION_INTENT,
    LANGFUSE_METADATA_INTENT_MATCHED_RULE,
    LANGFUSE_METADATA_INTENT_USED_PREVIOUS_MESSAGE,
)
from app.schemas.webhook import NormalizedWebhookMessageRequest
from app.schemas.webhook_attribution import WebhookAttribution

OBS_SCHEMA_VERSION = "1.0"
PROMPT_RUN_METADATA_MAX_BYTES = 4096
ATTRIBUTION_SUMMARY_MAX_CHARS = 500
OPERATOR_CONTEXT_TRACE_MAX_CHARS = 4000
ASSEMBLED_PROMPT_TRACE_MAX_CHARS = 24_000

ALPSTEIN_DEMO_BUSINESS_EXTERNAL_ID = "alpstein_ai_demo_001"

X_CORRELATION_ID_HEADER = "X-Correlation-Id"
X_N8N_EXECUTION_ID_HEADER = "X-N8n-Execution-Id"

# Optional keys dropped first when prompt_runs.metadata exceeds byte cap (§16.3).
_PROMPT_RUN_METADATA_DROP_ORDER: tuple[str, ...] = (
    "attribution_summary",
    "assembled_section_ids",
    "n8n_execution_id",
    "n8n_workflow_id",
    "source_platform",
    "source_account_id",
    "external_conversation_id",
    "external_message_id",
    "intent_used_previous_message",
    "intent_matched_rule",
    "conversation_intent",
    "gateway_provider",
    "gateway_model",
    "prompt_version",
    "prompt_template_id",
    "template_key",
    "prompt_task",
    "greeting_mode",
    "outbound_message_id",
)


class InvalidCorrelationIdError(ValueError):
    """Raised when an optional correlation id is present but not a valid UUID."""


def resolve_correlation_id(
    *,
    header_value: str | None,
    body_value: str | None,
) -> uuid.UUID:
    """Header wins when both are valid; generate when both absent."""
    header_id = _parse_optional_uuid(header_value, field_name="X-Correlation-Id")
    body_id = _parse_optional_uuid(body_value, field_name="correlation_id")
    if header_id is not None:
        return header_id
    if body_id is not None:
        return body_id
    return uuid.uuid4()


def _parse_optional_uuid(value: str | None, *, field_name: str) -> uuid.UUID | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return uuid.UUID(stripped)
    except ValueError as exc:
        raise InvalidCorrelationIdError(
            f"{field_name} must be a valid UUID"
        ) from exc


def build_attribution_summary(attribution: WebhookAttribution | None) -> str | None:
    if attribution is None:
        return None
    parts: list[str] = []
    for key, value in (
        ("utm_source", attribution.utm_source),
        ("utm_medium", attribution.utm_medium),
        ("utm_campaign", attribution.utm_campaign),
        ("utm_content", attribution.utm_content),
        ("utm_term", attribution.utm_term),
        ("marketing_source", attribution.marketing_source),
        ("campaign_id", attribution.campaign_id),
    ):
        if value:
            parts.append(f"{key}={value}")
    if not parts:
        return None
    summary = "; ".join(parts)
    if len(summary) > ATTRIBUTION_SUMMARY_MAX_CHARS:
        return summary[: ATTRIBUTION_SUMMARY_MAX_CHARS - 3] + "..."
    return summary


def observability_context_from_webhook(
    request: NormalizedWebhookMessageRequest,
    *,
    correlation_id: uuid.UUID,
    n8n_execution_id: str | None = None,
) -> ObservabilityContext:
    operator_present = bool(
        request.operator_business_context
        and request.operator_business_context.strip()
    )
    return ObservabilityContext(
        correlation_id=correlation_id,
        channel=request.channel.value,
        external_message_id=request.message.external_message_id,
        external_conversation_id=request.message.external_conversation_id,
        source_platform=request.source.platform if request.source else None,
        source_account_id=request.source.account_id if request.source else None,
        attribution_summary=build_attribution_summary(request.attribution),
        operator_business_context_present=operator_present,
        n8n_execution_id=_normalize_optional_string(n8n_execution_id),
    )


@dataclass(frozen=True)
class ObservabilityContext:
    correlation_id: uuid.UUID
    obs_schema_version: str = OBS_SCHEMA_VERSION
    tenant_id: uuid.UUID | None = None
    business_id: uuid.UUID | None = None
    business_external_id: str | None = None
    flow_id: uuid.UUID | None = None
    flow_key: str | None = None
    channel: str | None = None
    conversation_id: uuid.UUID | None = None
    inbound_message_id: uuid.UUID | None = None
    is_duplicate: bool | None = None
    external_message_id: str | None = None
    external_conversation_id: str | None = None
    prompt_run_id: uuid.UUID | None = None
    outbound_message_id: uuid.UUID | None = None
    template_key: str | None = None
    prompt_template_id: uuid.UUID | None = None
    prompt_version: str | None = None
    assembled_section_ids: tuple[str, ...] = field(default_factory=tuple)
    prompt_task: str | None = None
    gateway_model: str | None = None
    gateway_provider: str | None = None
    ai_success: bool | None = None
    used_fallback: bool | None = None
    greeting_mode: str | None = None
    conversation_intent: str | None = None
    intent_matched_rule: str | None = None
    intent_used_previous_message: bool | None = None
    operator_business_context_present: bool = False
    operator_business_context_preview: str | None = None
    n8n_workflow_id: str | None = None
    n8n_execution_id: str | None = None
    source_platform: str | None = None
    source_account_id: str | None = None
    attribution_summary: str | None = None
    error_code: str | None = None
    customer_language_code: str | None = None

    def with_business(
        self,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        business_external_id: str,
    ) -> ObservabilityContext:
        return replace(
            self,
            tenant_id=tenant_id,
            business_id=business_id,
            business_external_id=business_external_id,
        )

    def with_flow(
        self,
        *,
        flow_id: uuid.UUID,
        flow_key: str,
    ) -> ObservabilityContext:
        return replace(
            self,
            flow_id=flow_id,
            flow_key=flow_key,
        )

    def with_session(
        self,
        *,
        conversation_id: uuid.UUID,
        inbound_message_id: uuid.UUID,
        is_duplicate: bool,
    ) -> ObservabilityContext:
        return replace(
            self,
            conversation_id=conversation_id,
            inbound_message_id=inbound_message_id,
            is_duplicate=is_duplicate,
        )

    def with_prompt_lineage(
        self,
        *,
        template_key: str,
        prompt_template_id: uuid.UUID,
        prompt_version: str,
        prompt_task: str,
        assembled_section_ids: tuple[str, ...],
    ) -> ObservabilityContext:
        return replace(
            self,
            template_key=template_key,
            prompt_template_id=prompt_template_id,
            prompt_version=prompt_version,
            prompt_task=prompt_task,
            assembled_section_ids=assembled_section_ids,
        )

    def with_greeting(self, *, greeting_mode: str, customer_language_code: str) -> ObservabilityContext:
        return replace(
            self,
            greeting_mode=greeting_mode,
            customer_language_code=customer_language_code,
        )

    def with_intent(
        self,
        *,
        conversation_intent: str,
        intent_matched_rule: str,
        intent_used_previous_message: bool,
    ) -> ObservabilityContext:
        return replace(
            self,
            conversation_intent=conversation_intent,
            intent_matched_rule=intent_matched_rule,
            intent_used_previous_message=intent_used_previous_message,
        )

    def with_gateway(
        self,
        *,
        gateway_model: str | None,
        gateway_provider: str | None,
        ai_success: bool,
    ) -> ObservabilityContext:
        return replace(
            self,
            gateway_model=gateway_model,
            gateway_provider=gateway_provider,
            ai_success=ai_success,
        )

    def with_prompt_run(self, *, prompt_run_id: uuid.UUID) -> ObservabilityContext:
        return replace(self, prompt_run_id=prompt_run_id)

    def with_outbound_message(self, *, outbound_message_id: uuid.UUID) -> ObservabilityContext:
        return replace(self, outbound_message_id=outbound_message_id)

    def with_used_fallback(self, *, used_fallback: bool) -> ObservabilityContext:
        return replace(self, used_fallback=used_fallback)

    def with_operator_preview(self, *, operator_business_context: str | None) -> ObservabilityContext:
        present = bool(operator_business_context and operator_business_context.strip())
        preview = None
        if present and operator_business_context is not None:
            preview = _truncate(operator_business_context, OPERATOR_CONTEXT_TRACE_MAX_CHARS)
        return replace(
            self,
            operator_business_context_present=present,
            operator_business_context_preview=preview,
        )

    def to_prompt_run_metadata(self) -> dict[str, Any]:
        payload = self._scalar_dict()
        return _fit_prompt_run_metadata(payload)

    def to_langfuse_metadata(
        self,
        *,
        settings: Settings,
        assembled_prompt_dump: str | None = None,
    ) -> dict[str, str]:
        metadata: dict[str, str] = {}

        def put(key: str, value: object | None) -> None:
            if value is None:
                return
            if isinstance(value, bool):
                metadata[key] = "true" if value else "false"
            elif isinstance(value, uuid.UUID):
                metadata[key] = str(value)
            elif isinstance(value, tuple):
                metadata[key] = ",".join(str(item) for item in value)
            else:
                metadata[key] = str(value)

        put("obs_schema_version", self.obs_schema_version)
        put("correlation_id", self.correlation_id)
        put("tenant_id", self.tenant_id)
        put("business_uuid", self.business_id)
        put("business_id", self.business_external_id)
        put("flow_id", self.flow_id)
        put("flow_key", self.flow_key)
        put("conversation_id", self.conversation_id)
        put("channel", self.channel)
        put("inbound_message_id", self.inbound_message_id)
        put("is_duplicate", self.is_duplicate)
        put("external_message_id", self.external_message_id)
        put("external_conversation_id", self.external_conversation_id)
        put("prompt_run_id", self.prompt_run_id)
        put("outbound_message_id", self.outbound_message_id)
        put("template_key", self.template_key)
        put("prompt_template_id", self.prompt_template_id)
        put("prompt_version", self.prompt_version)
        put("assembled_section_ids", self.assembled_section_ids)
        put("prompt_task", self.prompt_task)
        put("gateway_model", self.gateway_model)
        put("gateway_provider", self.gateway_provider)
        put("ai_success", self.ai_success)
        put("used_fallback", self.used_fallback)
        put("greeting_mode", self.greeting_mode)
        put("customer_language", self.customer_language_code)
        put(LANGFUSE_METADATA_CONVERSATION_INTENT, self.conversation_intent)
        put(LANGFUSE_METADATA_INTENT_MATCHED_RULE, self.intent_matched_rule)
        put(
            LANGFUSE_METADATA_INTENT_USED_PREVIOUS_MESSAGE,
            self.intent_used_previous_message,
        )
        put("operator_business_context_present", self.operator_business_context_present)
        put("n8n_execution_id", self.n8n_execution_id)
        put("n8n_workflow_id", self.n8n_workflow_id)
        put("source_platform", self.source_platform)
        put("source_account_id", self.source_account_id)
        put("attribution_summary", self.attribution_summary)
        put("error_code", self.error_code)

        if (
            _langfuse_allows_sensitive_text_metadata(settings)
            and self.operator_business_context_preview
        ):
            metadata["operator_business_context"] = self.operator_business_context_preview

        if (
            _langfuse_allows_sensitive_text_metadata(settings)
            and assembled_prompt_dump
        ):
            metadata["assembled_prompt"] = _truncate(
                assembled_prompt_dump,
                ASSEMBLED_PROMPT_TRACE_MAX_CHARS,
            )

        return metadata

    def _scalar_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for item in fields(self):
            if item.name == "operator_business_context_preview":
                continue
            value = getattr(self, item.name)
            if value is None:
                continue
            if item.name == "assembled_section_ids":
                result[item.name] = list(value)
            else:
                result[item.name] = value
        return result


def _langfuse_allows_sensitive_text_metadata(settings: Settings) -> bool:
    """§16.2 — truncated operator context and assembled_prompt in Langfuse dev/test only."""
    return (
        langfuse_tracing_active(settings)
        and settings.environment.lower() in LANGFUSE_DEV_ENVIRONMENTS
    )


def _fit_prompt_run_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    required_keys = {
        "obs_schema_version",
        "correlation_id",
        "tenant_id",
        "business_id",
        "business_external_id",
        "channel",
        "conversation_id",
        "inbound_message_id",
        "is_duplicate",
    }
    working = dict(payload)
    while len(_json_bytes(working)) > PROMPT_RUN_METADATA_MAX_BYTES:
        dropped = False
        for key in _PROMPT_RUN_METADATA_DROP_ORDER:
            if key in working:
                del working[key]
                dropped = True
                break
        if not dropped:
            for key in list(working.keys()):
                if key not in required_keys:
                    del working[key]
                    dropped = True
                    break
        if not dropped:
            break
    return working


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, default=str, separators=(",", ":")).encode("utf-8")


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."
