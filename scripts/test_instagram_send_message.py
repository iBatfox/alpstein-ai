#!/usr/bin/env python3
"""Send one manual Instagram text message to a webhook sender id.

Usage (from repo root, with INSTAGRAM_* in environment or /opt/alpstein-ai/.env):
  PYTHONPATH=backend python3 scripts/test_instagram_send_message.py \
    --recipient-id 17841400000000000 \
    --text "Manual Alpstein Instagram test"

From host with project .env:
  cd /opt/alpstein-ai && set -a && . ./.env && set +a && \
    PYTHONPATH=backend python3 scripts/test_instagram_send_message.py \
      --recipient-id 17841400000000000 \
      --text "Manual Alpstein Instagram test"
"""

from __future__ import annotations

import argparse
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send one manual Instagram text reply to a real webhook sender id.",
    )
    parser.add_argument(
        "--recipient-id",
        required=True,
        help="Instagram scoped sender id from a real inbound webhook payload.",
    )
    parser.add_argument(
        "--text",
        required=True,
        help="Text to send. Use only for a manual smoke test.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = InstagramGraphClient(app_settings=settings)

    try:
        result = client.send_text_message(
            recipient_id=args.recipient_id,
            text=args.text,
        )
    except InstagramClientError as exc:
        print(f"Instagram send failed [{exc.code}]: {exc}", file=sys.stderr)
        return 1

    print("Instagram send: OK")
    print(f"recipient_id: {result.recipient_id}")
    print(f"message_id: {result.message_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
