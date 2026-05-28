#!/usr/bin/env bash
# Alpstein AI — n8n workflow export scrub + parity gate (C2 / T14.6)
# Contract: docs/ops/n8n-runtime-export-parity.md — gate G-EXP-2
#
# Usage:
#   scripts/n8n/export-scrub.sh              # check only (exit 0 = pass)
#   scripts/n8n/export-scrub.sh --scrub      # normalize in place (canonical + backups)
#
# Does not contact n8n runtime. Safe from clean clone (needs python3).

set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORKFLOWS_DIR="${WORKFLOWS_DIR:-${REPO_ROOT}/n8n/workflows}"
MODE="check"

if [ "${1:-}" = "--scrub" ]; then
  MODE="scrub"
elif [ -n "${1:-}" ]; then
  echo "usage: $0 [--scrub]" >&2
  exit 2
fi

export REPO_ROOT WORKFLOWS_DIR MODE

python3 <<'PY'
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(os.environ["REPO_ROOT"])
WORKFLOWS_DIR = Path(os.environ["WORKFLOWS_DIR"])
MODE = os.environ["MODE"]

CANONICAL_FILES = {
    "t13_workflow1_test_webhook_skeleton.json": "alpstein-incoming-message-test",
    "t14_workflow_telegram_customer_ingress_skeleton.json": "alpstein-incoming-message-telegram",
    "e1_6_workflow_website_chat_mvp_skeleton.json": "alpstein-incoming-message-website-chat",
}

NON_CANONICAL_BLOCKLIST = {"My_workflow.json"}


def is_tracked_in_git(path: Path) -> bool:
    try:
        import subprocess

        rel = path.relative_to(REPO_ROOT).as_posix()
        r = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", rel],
            capture_output=True,
            text=True,
        )
        return r.returncode == 0
    except (OSError, ValueError):
        return False

FORBIDDEN_ROOT_KEYS = frozenset({"pinData", "shared", "staticData"})
ALLOWED_CREDENTIAL_KEYS = frozenset({"name"})

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("accessToken literal", re.compile(r'"accessToken"\s*:\s*"(?!\{\{)[^"]{8,}')),
    ("apiKey literal", re.compile(r'"apiKey"\s*:\s*"(?!\{\{)[^"]{8,}')),
    ("Bearer token literal", re.compile(r'Bearer\s+[A-Za-z0-9._-]{20,}')),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    (
        "Telegram bot token shape",
        re.compile(r"\b\d{8,}:[A-Za-z0-9_-]{30,}\b"),
    ),
    (
        "hardcoded webhook token header",
        re.compile(
            r'"X-Alpstein-Webhook-Token"\s*,\s*"value"\s*:\s*"(?!\=\{\{)[^"]{8,}'
        ),
    ),
]

errors: list[str] = []
warnings: list[str] = []
scrubbed: list[str] = []


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def fail(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def discover_json_files() -> list[Path]:
    if not WORKFLOWS_DIR.is_dir():
        fail(f"workflows directory missing: {WORKFLOWS_DIR}")
        return []
    files: list[Path] = []
    for path in sorted(WORKFLOWS_DIR.rglob("*.json")):
        rel = path.relative_to(WORKFLOWS_DIR)
        if rel.parts and rel.parts[0] == "backups":
            files.append(path)
            continue
        if path.name in NON_CANONICAL_BLOCKLIST:
            if is_tracked_in_git(path):
                fail(
                    f"non-canonical export tracked in git: {rel} — "
                    "remove from index; use canonical skeleton files only"
                )
            else:
                warn(
                    f"local non-canonical export ignored by gate scan: {rel} "
                    "(gitignored — delete locally to silence)"
                )
            continue
        if path.name not in CANONICAL_FILES and path.parent == WORKFLOWS_DIR:
            fail(f"unexpected workflow JSON at workflow directory root: {rel}")
            continue
        if path.name in CANONICAL_FILES:
            files.append(path)
    return files


def check_secret_literals(raw: str, rel: str) -> None:
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(raw):
            fail(f"{rel}: suspected secret ({label})")


def walk_credentials(obj: Any, rel: str, path: str = "") -> None:
    if isinstance(obj, dict):
        if "credentials" in obj and isinstance(obj["credentials"], dict):
            for cred_type, cred_val in obj["credentials"].items():
                if not isinstance(cred_val, dict):
                    continue
                cred_path = f"{path}.credentials.{cred_type}"
                extra = set(cred_val.keys()) - ALLOWED_CREDENTIAL_KEYS
                if extra:
                    fail(
                        f"{rel}: credential {cred_type} has forbidden keys "
                        f"{sorted(extra)} at {cred_path} (name-only policy)"
                    )
                if "id" in cred_val:
                    fail(f"{rel}: credential {cred_type} must not include id")
                name = cred_val.get("name")
                if name is not None and not isinstance(name, str):
                    fail(f"{rel}: credential name must be string")
        for key, val in obj.items():
            walk_credentials(val, rel, f"{path}.{key}" if path else key)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            walk_credentials(item, rel, f"{path}[{idx}]")


def scrub_document(data: dict[str, Any]) -> dict[str, Any]:
    for key in list(data.keys()):
        if key in FORBIDDEN_ROOT_KEYS:
            del data[key]
    if "id" in data and isinstance(data.get("id"), str):
        del data["id"]
    data["active"] = False

    def scrub_node(obj: Any) -> None:
        if isinstance(obj, dict):
            creds = obj.get("credentials")
            if isinstance(creds, dict):
                for cred_type, cred_val in list(creds.items()):
                    if isinstance(cred_val, dict):
                        cleaned = {
                            k: v
                            for k, v in cred_val.items()
                            if k in ALLOWED_CREDENTIAL_KEYS
                        }
                        creds[cred_type] = cleaned
            for val in obj.values():
                scrub_node(val)
        elif isinstance(obj, list):
            for item in obj:
                scrub_node(item)

    scrub_node(data.get("nodes"))
    return data


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def validate_file(path: Path) -> dict[str, Any] | None:
    rel = display_path(path)
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"{rel}: invalid JSON ({exc})")
        return None

    if not isinstance(data, dict):
        fail(f"{rel}: root must be JSON object")
        return None

    check_secret_literals(raw, rel)

    for key in FORBIDDEN_ROOT_KEYS:
        if key in data:
            if MODE == "scrub":
                pass
            else:
                fail(f"{rel}: forbidden runtime field {key!r}")

    if "id" in data and isinstance(data.get("id"), str):
        if MODE != "scrub":
            fail(f"{rel}: workflow-level id is runtime-only (remove or scrub)")

    active = data.get("active")
    if active is not False:
        if MODE == "scrub":
            pass
        else:
            fail(f"{rel}: active must be false in git (got {active!r})")

    version_id = data.get("versionId")
    if not version_id or not isinstance(version_id, str):
        fail(f"{rel}: versionId must be a non-empty string stamp")
    elif not re.match(r"^[a-z0-9][a-z0-9._-]*$", version_id, re.I):
        warn(f"{rel}: versionId {version_id!r} is unusual (expected stamp like t14-...)")

    expected_name = CANONICAL_FILES.get(path.name)
    if expected_name and data.get("name") != expected_name:
        fail(
            f"{rel}: workflow name must be {expected_name!r} (got {data.get('name')!r})"
        )

    if "nodes" not in data or not isinstance(data["nodes"], list):
        fail(f"{rel}: nodes array required")

    walk_credentials(data, rel)

    # HTTP must use env for backend URL/token (spot-check raw file)
    if re.search(
        r'"url"\s*:\s*"https?://(?!.*\$env)[^"]+api/v1/webhook',
        raw,
        re.I,
    ):
        warn(f"{rel}: literal backend URL in export (prefer $env.BACKEND_BASE_URL)")

    if MODE == "scrub":
        scrubbed_data = scrub_document(data)
        new_raw = json.dumps(scrubbed_data, indent=2, ensure_ascii=False) + "\n"
        if new_raw != raw:
            path.write_text(new_raw, encoding="utf-8")
            scrubbed.append(rel)

    return data


def main() -> int:
    log(f"export-scrub: mode={MODE} workflows={WORKFLOWS_DIR}")
    files = discover_json_files()
    if not files:
        fail("no canonical workflow exports found to validate")

    for path in files:
        validate_file(path)

    for w in warnings:
        log(f"WARN: {w}")
    for e in errors:
        log(f"ERROR: {e}")
    if scrubbed:
        for s in scrubbed:
            log(f"SCRUBBED: {s}")

    if errors:
        log(f"G-EXP-2: FAIL ({len(errors)} error(s))")
        return 1

    log(f"G-EXP-2: PASS ({len(files)} file(s) checked)")
    if scrubbed:
        log(f"normalized {len(scrubbed)} file(s) — review diff before commit")
    return 0


sys.exit(main())
PY
