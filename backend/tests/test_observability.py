"""Observability context contract tests (D2)."""

from __future__ import annotations

import json
import uuid

import pytest

from app.schemas.observability import (
    ALPSTEIN_DEMO_BUSINESS_EXTERNAL_ID,
    InvalidCorrelationIdError,
    ObservabilityContext,
    OBS_SCHEMA_VERSION,
    PROMPT_RUN_METADATA_MAX_BYTES,
    build_attribution_summary,
    observability_context_from_webhook,
    resolve_correlation_id,
)
from app.schemas.webhook import (
    NormalizedWebhookMessageRequest,
    WebhookChannel,
    WebhookCustomer,
    WebhookMessage,
)
from app.schemas.webhook_attribution import WebhookAttribution


def _webhook_request(**overrides) -> NormalizedWebhookMessageRequest:
    payload = {
        "business_id": "alpstein_ai_demo_001",
        "channel": WebhookChannel.TELEGRAM,
        "customer": WebhookCustomer(
            phone="+41790000001",
            external_customer_id="user-123",
        ),
        "message": WebhookMessage(
            text="Hello",
            external_message_id="ext-1",
            external_conversation_id="tg:conv-1",
        ),
    }
    payload.update(overrides)
    return NormalizedWebhookMessageRequest(**payload)


def test_resolve_correlation_id_header_wins():
    header_id = uuid.uuid4()
    body_id = uuid.uuid4()
    resolved = resolve_correlation_id(
        header_value=str(header_id),
        body_value=str(body_id),
    )
    assert resolved == header_id


def test_resolve_correlation_id_generates_when_absent():
    resolved = resolve_correlation_id(header_value=None, body_value=None)
    assert isinstance(resolved, uuid.UUID)


def test_resolve_correlation_id_rejects_invalid():
    with pytest.raises(InvalidCorrelationIdError):
        resolve_correlation_id(header_value="not-a-uuid", body_value=None)


def test_observability_context_from_webhook_ingress_fields():
    correlation_id = uuid.uuid4()
    request = _webhook_request(
        attribution=WebhookAttribution(utm_source="google", utm_campaign="spring"),
        operator_business_context="  Russian supported  ",
    )
    context = observability_context_from_webhook(
        request,
        correlation_id=correlation_id,
        n8n_execution_id="exec-123",
    )
    assert context.correlation_id == correlation_id
    assert context.channel == "telegram"
    assert context.external_message_id == "ext-1"
    assert context.user_external_id == "user-123"
    assert context.n8n_execution_id == "exec-123"
    assert context.operator_business_context_present is True
    assert context.attribution_summary == "utm_source=google; utm_campaign=spring"


def test_build_attribution_summary_empty_when_no_values():
    assert build_attribution_summary(WebhookAttribution()) is None


def test_to_prompt_run_metadata_fits_byte_cap():
    context = ObservabilityContext(
        correlation_id=uuid.uuid4(),
        obs_schema_version=OBS_SCHEMA_VERSION,
        tenant_id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        business_external_id="biz",
        channel="whatsapp",
        conversation_id=uuid.uuid4(),
        inbound_message_id=uuid.uuid4(),
        is_duplicate=False,
        attribution_summary="x" * 5000,
        assembled_section_ids=tuple(f"section_{index}" for index in range(200)),
    )
    metadata = context.to_prompt_run_metadata()
    assert len(json.dumps(metadata, default=str).encode("utf-8")) <= PROMPT_RUN_METADATA_MAX_BYTES
    assert metadata["correlation_id"] == context.correlation_id
    assert metadata["obs_schema_version"] == OBS_SCHEMA_VERSION


def test_production_langfuse_metadata_excludes_sensitive_text_previews():
    from app.core.config import Settings

    settings = Settings(
        environment="production",
        LANGFUSE_PUBLIC_KEY="pk-prod",
        LANGFUSE_SECRET_KEY="sk-prod",
        LANGFUSE_TRACING_ENABLED=True,
    )
    context = ObservabilityContext(
        correlation_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        operator_business_context_present=True,
        operator_business_context_preview="Operator-only routing notes",
    )
    metadata = context.to_langfuse_metadata(
        settings=settings,
        assembled_prompt_dump="=== platform_system ===\n[SECRET PROMPT BODY]",
    )

    assert "operator_business_context" not in metadata
    assert "assembled_prompt" not in metadata
    assert metadata["operator_business_context_present"] == "true"


def test_dev_langfuse_metadata_excludes_sensitive_text_payloads():
    from app.core.config import Settings

    settings = Settings(
        environment="development",
        LANGFUSE_PUBLIC_KEY="pk-dev",
        LANGFUSE_SECRET_KEY="sk-dev",
    )
    context = ObservabilityContext(
        correlation_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        operator_business_context_present=True,
        operator_business_context_preview="Reply in Russian when appropriate",
    )
    metadata = context.to_langfuse_metadata(
        settings=settings,
        assembled_prompt_dump="=== platform_system ===\nSafety rules.",
    )

    assert metadata["operator_business_context_present"] == "true"
    assert "operator_business_context" not in metadata
    assert "assembled_prompt" not in metadata


def test_langfuse_metadata_demo_tag_value_is_external_id():
    from app.core.config import Settings
    from app.services.langfuse_tracing_service import _build_tags

    context = ObservabilityContext(
        correlation_id=uuid.uuid4(),
        business_external_id=ALPSTEIN_DEMO_BUSINESS_EXTERNAL_ID,
        channel="telegram",
        conversation_id=uuid.uuid4(),
    )
    tags = _build_tags(context)
    assert ALPSTEIN_DEMO_BUSINESS_EXTERNAL_ID in tags
    metadata = context.to_langfuse_metadata(
        settings=Settings(environment="development", LANGFUSE_PUBLIC_KEY="pk"),
    )
    assert metadata["business_id"] == ALPSTEIN_DEMO_BUSINESS_EXTERNAL_ID
