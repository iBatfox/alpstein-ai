#!/usr/bin/env python3
"""Verify Instagram Graph API credentials (profile fetch only).

Usage (from repo root, with INSTAGRAM_* in environment or /opt/alpstein-ai/.env):
  PYTHONPATH=backend python3 scripts/test_instagram_connection.py

From host with project .env (recommended):
  cd /opt/alpstein-ai && set -a && . ./.env && set +a && \\
    PYTHONPATH=backend python3 scripts/test_instagram_connection.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
VENV_SITE = BACKEND_DIR / ".venv" / "lib"
if VENV_SITE.exists():
    for site in sorted(VENV_SITE.glob("python*/site-packages")):
        sys.path.insert(0, str(site))
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.services.instagram_client import (  # noqa: E402
    InstagramClientError,
    InstagramGraphClient,
)


def main() -> int:
    client = InstagramGraphClient(app_settings=settings)
    try:
        profile = client.get_profile()
    except InstagramClientError as exc:
        print(f"Instagram connectivity check failed [{exc.code}]: {exc}", file=sys.stderr)
        return 1

    print("Instagram Graph API connectivity: OK")
    print(f"instagram user id: {profile.id}")
    print(f"username: {profile.username}")
    print(f"account type: {profile.account_type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
