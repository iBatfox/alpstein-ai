#!/usr/bin/env python3
"""Verify Instagram n8n branch reads backend.data.reply_to_customer (not hardcoded text)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPO / "scripts/n8n/build_e1_8_unified_workflow.py"
WORKFLOW_JSON = REPO / "n8n/workflows/e1_8_unified_customer_ingress_skeleton.json"


def test_prepare_instagram_reply_context_uses_backend_reply_to_customer() -> None:
    source = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert "backend.data.reply_to_customer" in source
    assert "PREPARE_INSTAGRAM_REPLY_CONTEXT" in source
    assert "operator_business_context" not in source.split("PREPARE_INSTAGRAM_REPLY_CONTEXT")[1].split("SHAPE_CANONICAL")[0]


def test_workflow_json_instagram_send_uses_reply_to_customer() -> None:
    payload = WORKFLOW_JSON.read_text(encoding="utf-8")
    assert '"name": "Prepare Instagram Reply Context"' in payload
    assert "backend.data.reply_to_customer" in payload
    assert '"name": "POST Instagram Send via Backend"' in payload
    assert "reply_to_customer" in payload
    assert '"id": "aYrRmAGKhP4TJbG9"' in payload
    assert '"name": "alpstein-customer-ingress"' in payload


def main() -> int:
    test_prepare_instagram_reply_context_uses_backend_reply_to_customer()
    test_workflow_json_instagram_send_uses_reply_to_customer()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
