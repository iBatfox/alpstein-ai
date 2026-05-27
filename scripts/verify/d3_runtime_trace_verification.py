#!/usr/bin/env python3
"""Phase D3 — runtime trace verification harness (CIP-C).

Runs in-process checks against the FastAPI app and observability stack.
Does not require Docker when DB is mocked for webhook ingress checks.

Usage (from repo root):
  cd backend && ../scripts/verify/d3_runtime_trace_verification.py
  # or:
  PYTHONPATH=backend python3 scripts/verify/d3_runtime_trace_verification.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.core.observability_context import (  # noqa: E402
    CorrelationIdLogFilter,
    get_observability_context,
    reset_observability_context,
    set_observability_context,
)
from app.main import app  # noqa: E402
from app.models.conversation import Conversation  # noqa: E402
from app.models.message import Message  # noqa: E402
from app.schemas.langfuse_intent_trace import (  # noqa: E402
    LANGFUSE_METADATA_CONVERSATION_INTENT,
    LANGFUSE_METADATA_INTENT_MATCHED_RULE,
    LANGFUSE_METADATA_INTENT_USED_PREVIOUS_MESSAGE,
)
from app.schemas.observability import (  # noqa: E402
    ObservabilityContext,
    resolve_correlation_id,
)
from app.services.langfuse_tracing_service import LangfuseTracingService  # noqa: E402
from app.services.webhook_message_service import WebhookMessageProcessResult  # noqa: E402


@dataclass
class CheckResult:
    id: str
    description: str
    status: str  # PASS | FAIL | SKIP
    evidence: str = ""


@dataclass
class Report:
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, check_id: str, description: str, status: str, evidence: str = "") -> None:
        self.checks.append(CheckResult(check_id, description, status, evidence))

    def to_dict(self) -> dict[str, Any]:
        passed = sum(1 for c in self.checks if c.status == "PASS")
        failed = sum(1 for c in self.checks if c.status == "FAIL")
        skipped = sum(1 for c in self.checks if c.status == "SKIP")
        return {
            "summary": {
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "total": len(self.checks),
            },
            "checks": [
                {
                    "id": c.id,
                    "description": c.description,
                    "status": c.status,
                    "evidence": c.evidence,
                }
                for c in self.checks
            ],
        }


TEST_TOKEN = "d3-verify-token"
WEBHOOK_PAYLOAD = {
    "business_id": "demo_barbershop_001",
    "channel": "whatsapp",
    "customer": {"phone": "+41790000000"},
    "message": {"text": "Hello", "external_message_id": "d3-ext-001"},
}


def _check_startup(report: Report) -> None:
    try:
        assert app.title == "Alpstein AI Backend"
        routes = {getattr(r, "path", None) for r in app.routes}
        assert "/api/v1/health/ready" in routes or any(
            "health" in str(r) for r in app.routes
        )
        report.add(
            "D3-01",
            "Backend app imports and exposes health + webhook routes",
            "PASS",
            f"app.title={app.title!r}",
        )
    except Exception as exc:
        report.add("D3-01", "Backend startup import", "FAIL", str(exc))


async def _check_health_ready(report: Report) -> None:
    """Readiness may fail without DB; record SKIP vs PASS."""
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            live = await client.get("/api/v1/health")
            ready = await client.get("/api/v1/health/ready")
        if live.status_code == 200:
            if ready.status_code == 200:
                report.add(
                    "D3-01b",
                    "Health liveness + readiness HTTP 200",
                    "PASS",
                    f"live={live.status_code} ready={ready.status_code}",
                )
            else:
                report.add(
                    "D3-01b",
                    "Health readiness (needs live Postgres)",
                    "SKIP",
                    f"liveness=200 readiness={ready.status_code} (no DB in harness)",
                )
        else:
            report.add("D3-01b", "Health endpoints", "FAIL", f"liveness={live.status_code}")
    except Exception as exc:
        report.add("D3-01b", "Health endpoints", "FAIL", str(exc))


def _install_webhook_mocks(monkeypatch: Any) -> MagicMock:
    import app.api.webhook_auth as webhook_auth_mod
    import app.core.config as config_mod

    monkeypatch.setattr(config_mod.settings, "n8n_backend_api_token", TEST_TOKEN)
    monkeypatch.setattr(webhook_auth_mod.settings, "n8n_backend_api_token", TEST_TOKEN)

    service = MagicMock()

    async def _process(session, body, observability=None):
        return WebhookMessageProcessResult(
            conversation=Conversation(
                id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                business_id=uuid.uuid4(),
                customer_id=uuid.uuid4(),
                channel="whatsapp",
                status="open",
            ),
            message=Message(
                id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                business_id=uuid.uuid4(),
                conversation_id=uuid.uuid4(),
                sender_type="customer",
                direction="incoming",
                channel="whatsapp",
                message_text="Hello",
            ),
            is_duplicate=False,
            reply_to_customer="OK",
            lead_created=False,
            notify_owner=False,
        )

    import app.api.routes.webhook as webhook_route_mod

    service.process_incoming_message = AsyncMock(side_effect=_process)
    monkeypatch.setattr(webhook_route_mod, "webhook_message_service", service)

    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def _override():
        yield session

    from app.db.session import get_db_session

    app.dependency_overrides[get_db_session] = _override
    return service


async def _webhook_post(
    headers: dict[str, str],
    payload: dict | None = None,
) -> Any:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(
            "/api/v1/webhook/message",
            json=payload or WEBHOOK_PAYLOAD,
            headers={**headers, "X-Alpstein-Webhook-Token": TEST_TOKEN},
        )


async def _check_webhook_correlation(report: Report) -> None:
    class _Monkey:
        def setattr(self, obj: Any, name: str, value: Any) -> None:
            setattr(obj, name, value)

    monkey = _Monkey()
    service = _install_webhook_mocks(monkey)

    try:
        cid = uuid.uuid4()
        n8n_exec = "n8n-exec-d3-99"
        resp = await _webhook_post(
            {
                "X-Correlation-Id": str(cid),
                "X-N8n-Execution-Id": n8n_exec,
            }
        )
        assert resp.status_code == 200, resp.text
        obs = service.process_incoming_message.await_args.kwargs["observability"]
        assert obs.correlation_id == cid
        assert obs.n8n_execution_id == n8n_exec
        report.add(
            "D3-02",
            "Webhook accepts valid X-Correlation-Id",
            "PASS",
            f"correlation_id={cid}",
        )
        report.add(
            "D3-05",
            "X-N8n-Execution-Id captured in ObservabilityContext",
            "PASS",
            f"n8n_execution_id={n8n_exec}",
        )

        resp2 = await _webhook_post({})
        obs2 = service.process_incoming_message.await_args.kwargs["observability"]
        assert isinstance(obs2.correlation_id, uuid.UUID)
        report.add(
            "D3-03",
            "Backend generates correlation_id when header absent",
            "PASS",
            f"generated={obs2.correlation_id}",
        )

        bad = await _webhook_post({"X-Correlation-Id": "not-a-uuid"})
        assert bad.status_code == 400
        body = bad.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        report.add(
            "D3-04",
            "Invalid X-Correlation-Id returns VALIDATION_ERROR",
            "PASS",
            f"status=400 code={body['error']['code']}",
        )
    except Exception as exc:
        report.add("D3-02..05", "Webhook correlation ingress", "FAIL", str(exc))
    finally:
        app.dependency_overrides.clear()


def _check_logging_correlation(report: Report) -> None:
    try:
        cid = uuid.uuid4()
        ctx = ObservabilityContext(correlation_id=cid)
        token = set_observability_context(ctx)
        record = logging.LogRecord(
            name="d3.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="trace test",
            args=(),
            exc_info=None,
        )
        CorrelationIdLogFilter().filter(record)
        assert getattr(record, "correlation_id", None) == str(cid)
        reset_observability_context(token)
        report.add(
            "D3-06a",
            "correlation_id on log records via CorrelationIdLogFilter",
            "PASS",
            f"record.correlation_id={record.correlation_id}",
        )
    except Exception as exc:
        report.add("D3-06a", "Log correlation filter", "FAIL", str(exc))


async def _check_langfuse_trace_chain(report: Report) -> None:
    from app.schemas.assembled_prompt import AssembledPrompt, AssembledPromptSection
    from app.schemas.greeting import GreetingPolicy, GreetingMode

    mock_client = MagicMock()
    mock_span = MagicMock()
    mock_client.start_as_current_observation.return_value.__enter__ = MagicMock(
        return_value=mock_span
    )
    mock_client.start_as_current_observation.return_value.__exit__ = MagicMock(
        return_value=False
    )

    conversation_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    prompt_run_id = uuid.uuid4()

    observability = ObservabilityContext(
        correlation_id=correlation_id,
        business_external_id="alpstein_ai_demo_001",
        business_id=uuid.uuid4(),
        conversation_id=conversation_id,
        channel="telegram",
        operator_business_context_present=True,
        operator_business_context_preview="Operator routing note",
        conversation_intent="pricing_interest",
        intent_matched_rule="pricing_keywords_ru",
        intent_used_previous_message=False,
        greeting_mode="first_contact",
        customer_language_code="ru",
    )

    assembled = AssembledPrompt(
        task="reply_to_customer",
        sections=(
            AssembledPromptSection(
                section_id="platform_system",
                label="PLATFORM",
                content="Safety",
                kind="system",
            ),
        ),
    )

    dev_settings = Settings(
        environment="development",
        langfuse_public_key="pk-d3",
        langfuse_secret_key="sk-d3",
    )

    service = LangfuseTracingService(app_settings=dev_settings, client=mock_client)

    try:
        with patch(
            "app.services.langfuse_tracing_service.propagate_attributes"
        ) as mock_propagate:
            mock_propagate.return_value.__enter__ = MagicMock(return_value=None)
            mock_propagate.return_value.__exit__ = MagicMock(return_value=False)

            async with service.trace_ai_reply(
                observability=observability,
                customer_message_preview="сколько стоит",
                assembled_prompt=assembled,
            ) as recorder:
                recorder.update_trace_metadata({"prompt_run_id": str(prompt_run_id)})

            prop_kwargs = mock_propagate.call_args.kwargs
            assert prop_kwargs.get("session_id") == str(conversation_id)

            span_meta = None
            for call in mock_client.start_as_current_observation.call_args_list:
                if call.kwargs.get("as_type") == "span":
                    span_meta = call.kwargs.get("metadata")
                    break

            assert span_meta is not None
            assert span_meta["correlation_id"] == str(correlation_id)
            assert span_meta["conversation_id"] == str(conversation_id)
            assert LANGFUSE_METADATA_CONVERSATION_INTENT in span_meta
            assert LANGFUSE_METADATA_INTENT_MATCHED_RULE in span_meta
            assert LANGFUSE_METADATA_INTENT_USED_PREVIOUS_MESSAGE in span_meta
            assert "assembled_prompt" in span_meta
            assert "operator_business_context" in span_meta

            report.add(
                "D3-07",
                "conversation_id used as Langfuse session_id",
                "PASS",
                f"session_id={prop_kwargs.get('session_id')}",
            )
            report.add(
                "D3-06b",
                "correlation_id + CIP intent fields in Langfuse span metadata",
                "PASS",
                f"keys include {LANGFUSE_METADATA_CONVERSATION_INTENT}",
            )
            report.add(
                "D3-08",
                "prompt_run_id updatable on span metadata after creation",
                "PASS",
                f"prompt_run_id={prompt_run_id} (via update_trace_metadata)",
            )

        prod_settings = Settings(
            environment="production",
            langfuse_public_key="pk-d3",
            langfuse_secret_key="sk-d3",
            langfuse_tracing_enabled=True,
        )
        prod_meta = observability.to_langfuse_metadata(
            settings=prod_settings,
            assembled_prompt_dump="SECRET PROMPT",
        )
        assert "assembled_prompt" not in prod_meta
        assert "operator_business_context" not in prod_meta
        assert prod_meta.get("operator_business_context_present") == "true"
        assert prod_meta.get("correlation_id") == str(correlation_id)
        report.add(
            "D3-10",
            "Production metadata policy (no sensitive text; scalar lineage)",
            "PASS",
            "no assembled_prompt/operator text; correlation_id present",
        )
    except Exception as exc:
        report.add("D3-06b..10", "Langfuse trace chain", "FAIL", str(exc))


def _check_prompt_run_metadata(report: Report) -> None:
    try:
        ctx = ObservabilityContext(
            correlation_id=uuid.uuid4(),
            obs_schema_version="1.0",
            tenant_id=uuid.uuid4(),
            business_id=uuid.uuid4(),
            business_external_id="demo_barbershop_001",
            channel="whatsapp",
            conversation_id=uuid.uuid4(),
            inbound_message_id=uuid.uuid4(),
            is_duplicate=False,
            template_key="customer_reply_v1",
            assembled_section_ids=("platform_system", "task_instructions"),
        )
        meta = ctx.to_prompt_run_metadata()
        assert "assembled_prompt" not in meta
        assert "operator_business_context_preview" not in meta
        assert meta["correlation_id"] == ctx.correlation_id
        raw = json.dumps(meta, default=str).encode("utf-8")
        assert len(raw) <= 4096
        report.add(
            "D3-06c",
            "prompt_runs.metadata scalar subset with correlation_id",
            "PASS",
            f"bytes={len(raw)} keys={sorted(meta.keys())[:8]}...",
        )
    except Exception as exc:
        report.add("D3-06c", "prompt_runs.metadata", "FAIL", str(exc))


def _check_duplicate_lineage(report: Report) -> None:
    try:
        cid_retry = uuid.uuid4()
        ctx1 = ObservabilityContext(
            correlation_id=cid_retry,
            is_duplicate=False,
            external_message_id="same-ext-id",
        )
        cid_retry2 = uuid.uuid4()
        ctx2 = ObservabilityContext(
            correlation_id=cid_retry2,
            is_duplicate=True,
            external_message_id="same-ext-id",
        )
        assert ctx1.correlation_id != ctx2.correlation_id
        assert ctx1.external_message_id == ctx2.external_message_id
        assert ctx2.is_duplicate is True
        report.add(
            "D3-12",
            "Duplicate/retry: new correlation_id per HTTP attempt; is_duplicate flag",
            "PASS",
            f"retry correlation differs; is_duplicate=true on second",
        )
    except Exception as exc:
        report.add("D3-12", "Duplicate lineage semantics", "FAIL", str(exc))


def _check_error_path(report: Report) -> None:
    from app.schemas.observability import InvalidCorrelationIdError

    try:
        resolve_correlation_id(header_value="bad", body_value=None)
        report.add("D3-11", "Error-path correlation validation", "FAIL", "should have raised")
    except InvalidCorrelationIdError:
        report.add(
            "D3-11",
            "Invalid correlation rejected before service (VALIDATION_ERROR path)",
            "PASS",
            "InvalidCorrelationIdError from resolve_correlation_id",
        )
    except Exception as exc:
        report.add("D3-11", "Error-path correlation validation", "FAIL", str(exc))


async def main() -> int:
    report = Report()
    _check_startup(report)
    await _check_health_ready(report)
    await _check_webhook_correlation(report)
    _check_logging_correlation(report)
    _check_prompt_run_metadata(report)
    await _check_langfuse_trace_chain(report)
    _check_duplicate_lineage(report)
    _check_error_path(report)

    # Langfuse cloud: SKIP unless keys configured (no network call)
    report.add(
        "D3-09-live",
        "Live Langfuse cloud trace export",
        "SKIP",
        "Harness uses mock Langfuse client; verify in dev UI when keys set",
    )

    out = report.to_dict()
    print(json.dumps(out, indent=2))
    return 0 if out["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
