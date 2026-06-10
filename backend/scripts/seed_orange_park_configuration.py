#!/usr/bin/env python3
"""Run Orange Park Telegram-only MVP configuration seed."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.seed.orange_park_configuration import (  # noqa: E402
    ORANGE_PARK_TENANT_NAME,
    ORANGE_PARK_TENANT_SLUG,
    seed_orange_park_configuration,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed Orange Park Telegram-only MVP backend configuration.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run lookups and writes, print planned changes, then roll back.",
    )
    parser.add_argument(
        "--tenant-slug",
        default=ORANGE_PARK_TENANT_SLUG,
        help="Tenant slug to create/update. Default: orange-park.",
    )
    parser.add_argument(
        "--tenant-name",
        default=ORANGE_PARK_TENANT_NAME,
        help="Tenant display name to create/update. Default: Orange Park.",
    )
    return parser.parse_args()


async def run_seed(
    *,
    dry_run: bool,
    tenant_slug: str,
    tenant_name: str,
) -> None:
    async with AsyncSessionLocal() as session:
        try:
            result = await seed_orange_park_configuration(
                session,
                tenant_slug=tenant_slug,
                tenant_name=tenant_name,
            )
            if dry_run:
                await session.rollback()
            else:
                await session.commit()
        except Exception:
            await session.rollback()
            raise

    mode = "DRY RUN rolled back" if dry_run else "committed"
    print(
        "Orange Park configuration seed complete:",
        mode,
        f"tenant={result.tenant_slug}",
        f"business={result.business_external_id}",
        f"tenant_id={result.tenant_id}",
        f"business_id={result.business_id}",
    )
    for action in result.actions:
        print(f"- {action}")


def main() -> None:
    args = parse_args()
    asyncio.run(
        run_seed(
            dry_run=args.dry_run,
            tenant_slug=args.tenant_slug,
            tenant_name=args.tenant_name,
        )
    )


if __name__ == "__main__":
    main()
