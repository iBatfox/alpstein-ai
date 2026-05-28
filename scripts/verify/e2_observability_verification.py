#!/usr/bin/env python3
"""E2.7 — observability chain runtime verification harness.

Checks route registration, model metadata, Alembic head, and optional pytest subset.
Does not require live Postgres for static checks.

Usage (from repo root):
  PYTHONPATH=backend python3 scripts/verify/e2_observability_verification.py
  PYTHONPATH=backend python3 scripts/verify/e2_observability_verification.py --run-pytest
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
VENV_SITE = BACKEND_DIR / ".venv" / "lib"
if VENV_SITE.exists():
    for site in sorted(VENV_SITE.glob("python*/site-packages")):
        sys.path.insert(0, str(site))
sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.delivery_event import DeliveryEvent  # noqa: E402
from app.models.message_trace import MessageTrace  # noqa: E402


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


def _route_paths() -> set[str]:
    return {getattr(route, "path", "") or "" for route in app.routes}


def check_startup(report: Report) -> None:
    try:
        assert app.title == "Alpstein AI Backend"
        report.add("E2-01", "FastAPI app imports", "PASS", f"title={app.title!r}")
    except Exception as exc:
        report.add("E2-01", "FastAPI app imports", "FAIL", str(exc))


def check_observability_routes(report: Report) -> None:
    paths = _route_paths()
    required = [
        ("/api/v1/observability/traces/{trace_id}", "trace by id"),
        ("/api/v1/observability/traces", "trace lookup"),
        ("/api/v1/observability/conversations/{conversation_id}/traces", "conversation traces"),
        ("/api/v1/observability/deliveries/{delivery_id}", "delivery by id"),
        ("/api/v1/observability/conversations/{conversation_id}/deliveries", "conversation deliveries"),
        ("/api/v1/observability/replays", "replay audit list (E3.1c)"),
    ]
    missing: list[str] = []
    for path, label in required:
        if path not in paths:
            missing.append(label)
    if missing:
        report.add(
            "E2-02",
            "Observability routes registered",
            "FAIL",
            f"missing: {', '.join(missing)}",
        )
    else:
        report.add("E2-02", "Observability routes registered", "PASS", f"{len(required)} routes")


def check_webhook_route(report: Report) -> None:
    paths = _route_paths()
    if "/api/v1/webhook/message" in paths:
        report.add("E2-03", "Webhook message route registered", "PASS")
    else:
        report.add("E2-03", "Webhook message route registered", "FAIL", str(sorted(paths)))


def check_model_metadata(report: Report) -> None:
    tables = set(Base.metadata.tables)
    needed = {"message_traces", "delivery_events"}
    if needed.issubset(tables):
        report.add(
            "E2-04",
            "E2 persistence tables in SQLAlchemy metadata",
            "PASS",
            ", ".join(sorted(needed)),
        )
    else:
        report.add(
            "E2-04",
            "E2 persistence tables in SQLAlchemy metadata",
            "FAIL",
            f"missing={needed - tables}",
        )


def check_model_tablenames(report: Report) -> None:
    try:
        assert MessageTrace.__tablename__ == "message_traces"
        assert DeliveryEvent.__tablename__ == "delivery_events"
        report.add("E2-05", "ORM tablename alignment", "PASS")
    except Exception as exc:
        report.add("E2-05", "ORM tablename alignment", "FAIL", str(exc))


def check_alembic_head(report: Report) -> None:
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        script = ScriptDirectory.from_config(cfg)
        heads = script.get_heads()
        if heads == ["0014"]:
            report.add("E2-06", "Alembic head revision", "PASS", "0014")
        else:
            report.add("E2-06", "Alembic head revision", "FAIL", f"heads={heads}")
    except Exception as exc:
        report.add("E2-06", "Alembic head revision", "FAIL", str(exc))


def check_delivery_indexes(report: Report) -> None:
    table = DeliveryEvent.__table__
    index_names = {idx.name for idx in table.indexes}
    if "delivery_events_outbound_message_id_unique" in index_names:
        report.add("E2-07", "delivery_events outbound unique index", "PASS")
    else:
        report.add(
            "E2-07",
            "delivery_events outbound unique index",
            "FAIL",
            f"indexes={sorted(index_names)}",
        )


def check_trace_indexes(report: Report) -> None:
    table = MessageTrace.__table__
    index_names = {idx.name for idx in table.indexes}
    if any("inbound" in name for name in index_names):
        report.add("E2-08", "message_traces inbound idempotency index present", "PASS")
    else:
        report.add(
            "E2-08",
            "message_traces inbound idempotency index present",
            "FAIL",
            f"indexes={sorted(index_names)}",
        )


def run_pytest_subset(report: Report) -> None:
    test_file = BACKEND_DIR / "tests" / "test_e2_observability_continuity.py"
    if not test_file.exists():
        report.add("E2-09", "E2.7 pytest continuity file", "FAIL", "file missing")
        return
    venv_python = BACKEND_DIR / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else sys.executable
    try:
        proc = subprocess.run(
            [python, "-m", "pytest", str(test_file), "-q", "--tb=no"],
            cwd=str(BACKEND_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            report.add(
                "E2-09",
                "E2.7 pytest continuity suite",
                "PASS",
                (proc.stdout or "").strip().splitlines()[-1:][0] or "ok",
            )
        else:
            report.add(
                "E2-09",
                "E2.7 pytest continuity suite",
                "FAIL",
                (proc.stderr or proc.stdout or "")[-500:],
            )
    except Exception as exc:
        report.add("E2-09", "E2.7 pytest continuity suite", "FAIL", str(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description="E2 observability verification harness")
    parser.add_argument(
        "--run-pytest",
        action="store_true",
        help="Run test_e2_observability_continuity.py subset",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report only")
    args = parser.parse_args()

    report = Report()
    check_startup(report)
    check_observability_routes(report)
    check_webhook_route(report)
    check_model_metadata(report)
    check_model_tablenames(report)
    check_alembic_head(report)
    check_delivery_indexes(report)
    check_trace_indexes(report)
    if args.run_pytest:
        run_pytest_subset(report)

    payload = report.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("E2 Observability Verification")
        print("=" * 40)
        for check in report.checks:
            print(f"[{check.status}] {check.id}: {check.description}")
            if check.evidence:
                print(f"         {check.evidence}")
        print("-" * 40)
        summary = payload["summary"]
        print(
            f"Total: {summary['total']}  "
            f"PASS: {summary['passed']}  "
            f"FAIL: {summary['failed']}  "
            f"SKIP: {summary['skipped']}"
        )

    return 1 if payload["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
