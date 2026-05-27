#!/usr/bin/env python3
"""Run development-only AI configuration seed (not for production)."""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.seed.dev_ai_configuration import seed_dev_ai_configuration  # noqa: E402


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await seed_dev_ai_configuration(session)
        await session.commit()

    print(
        "Dev AI configuration seed complete:",
        f"tenant={result.tenant_slug}",
        f"business={result.business_external_id}",
        f"templates={','.join(result.prompt_template_keys)}",
    )


if __name__ == "__main__":
    asyncio.run(main())
