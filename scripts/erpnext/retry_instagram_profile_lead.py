#!/usr/bin/env python3
"""Retry Instagram profile enrichment for one ERPNext Lead.

Default mode is dry-run. Profile fetch runs inside the backend container so it
uses the same Instagram settings as live ingress. ERPNext is updated only with
non-empty profile values.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

DEFAULT_BACKEND_CONTAINER = "alpstein_backend"
DEFAULT_ERPNEXT_BASE_URL = "https://crm.alpstein-ai.ch"
DEFAULT_ERPNEXT_AUTH_ENV = "/etc/alpstein/erpnext-n8n-api.env"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sender-id", required=True)
    parser.add_argument("--lead-id", required=True)
    parser.add_argument("--apply", action="store_true", help="update ERPNext Lead")
    parser.add_argument("--backend-container", default=DEFAULT_BACKEND_CONTAINER)
    parser.add_argument("--erpnext-base-url", default=os.getenv("ERPNEXT_BASE_URL", DEFAULT_ERPNEXT_BASE_URL))
    parser.add_argument("--erpnext-auth-env", default=DEFAULT_ERPNEXT_AUTH_ENV)
    return parser.parse_args()


def load_env_file(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    if not Path(path).exists():
        return values
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def erpnext_session(args: argparse.Namespace) -> requests.Session:
    auth_env = load_env_file(args.erpnext_auth_env)
    api_key = os.getenv("ERPNEXT_API_KEY") or auth_env.get("ERPNEXT_API_KEY")
    api_secret = os.getenv("ERPNEXT_API_SECRET") or auth_env.get("ERPNEXT_API_SECRET")
    if not api_key or not api_secret:
        raise RuntimeError("ERPNEXT_API_KEY / ERPNEXT_API_SECRET are required")
    session = requests.Session()
    session.headers.update({"Authorization": f"token {api_key}:{api_secret}"})
    return session


def erpnext_url(args: argparse.Namespace, path: str) -> str:
    return args.erpnext_base_url.rstrip("/") + path


def fetch_instagram_profile(args: argparse.Namespace) -> dict[str, Any]:
    code = r"""
import json
import sys
from app.services.instagram_client import InstagramClientError, InstagramGraphClient

sender = sys.argv[1]
try:
    profile = InstagramGraphClient().get_user_profile(sender)
    print(json.dumps({
        "status": "success",
        "id": profile.id,
        "username": profile.username,
        "name": profile.name,
        "profile_pic_present": bool(profile.profile_pic),
    }, ensure_ascii=False))
except InstagramClientError as exc:
    print(json.dumps({
        "status": "failed",
        "type": type(exc).__name__,
        "code": exc.code,
        "message": str(exc),
    }, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({
        "status": "failed",
        "type": type(exc).__name__,
        "message": str(exc),
    }, ensure_ascii=False))
"""
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            args.backend_container,
            "python",
            "-c",
            code,
            args.sender_id,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("Instagram profile retry returned no output")
    return json.loads(lines[-1])


def get_lead(session: requests.Session, args: argparse.Namespace) -> dict[str, Any]:
    fields = [
        "name",
        "lead_name",
        "first_name",
        "title",
        "alpstein_channel",
        "alpstein_external_user_id",
        "instagram_username",
        "instagram_display_name",
    ]
    response = session.get(
        erpnext_url(args, f"/api/resource/Lead/{quote(args.lead_id, safe='')}"),
        params={"fields": json.dumps(fields)},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("data", {})


def build_update(lead: dict[str, Any], profile: dict[str, Any]) -> dict[str, str]:
    username = clean(profile.get("username"))
    display_name = clean(profile.get("name"))
    update: dict[str, str] = {}

    if username:
        update["instagram_username"] = username
    if display_name:
        update["instagram_display_name"] = display_name

    profile_name = display_name or username
    current_lead_name = clean(lead.get("lead_name"))
    fallback_names = {
        f"instagram user {lead.get('alpstein_external_user_id')}",
        f"instagram user {profile.get('id')}",
        f"instagram user {profile.get('id') or ''}".strip(),
    }
    if profile_name and (not current_lead_name or current_lead_name in fallback_names):
        update["lead_name"] = profile_name
        update["first_name"] = profile_name
        update["title"] = profile_name

    return {key: value for key, value in update.items() if value}


def update_lead(
    session: requests.Session,
    args: argparse.Namespace,
    body: dict[str, str],
) -> None:
    response = session.put(
        erpnext_url(args, f"/api/resource/Lead/{quote(args.lead_id, safe='')}"),
        json=body,
        timeout=30,
    )
    response.raise_for_status()


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def main() -> int:
    args = parse_args()
    profile = fetch_instagram_profile(args)
    print(json.dumps({"profile_retry": profile}, ensure_ascii=False, indent=2))
    if profile.get("status") != "success":
        print("No ERPNext update: Instagram profile is unavailable for this sender.")
        return 2

    session = erpnext_session(args)
    lead = get_lead(session, args)
    if not lead:
        raise RuntimeError(f"Lead not found: {args.lead_id}")
    if clean(lead.get("alpstein_channel")) != "instagram":
        raise RuntimeError(f"Lead {args.lead_id} is not an Instagram Lead")
    if clean(lead.get("alpstein_external_user_id")) != args.sender_id:
        raise RuntimeError(
            "Lead external user id does not match sender id: "
            f"{lead.get('alpstein_external_user_id')} != {args.sender_id}"
        )

    update = build_update(lead, profile)
    print(json.dumps({"lead": lead, "planned_update": update}, ensure_ascii=False, indent=2))
    if not update:
        print("No ERPNext update: profile has no non-empty fields to apply.")
        return 0
    if not args.apply:
        print("Dry-run only. Re-run with --apply to update ERPNext.")
        return 0

    update_lead(session, args, update)
    print(f"Updated Lead {args.lead_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
