"""Run AI enrichment on un-enriched articles.

Usage:
    python -m app.workers.enrich_ai              # default batch of 50
    python -m app.workers.enrich_ai --limit=200
"""

from __future__ import annotations

import argparse
import asyncio

from app.core.cache import close as close_cache
from app.core.logging import configure_logging, get_logger
from app.services.ai_service import enrich_batch

configure_logging()
log = get_logger(__name__)


async def main(limit: int) -> None:
    try:
        await enrich_batch(limit=limit)
    finally:
        await close_cache()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    asyncio.run(main(args.limit))
