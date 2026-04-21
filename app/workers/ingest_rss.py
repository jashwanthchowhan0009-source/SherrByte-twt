"""RSS ingestion runner.

Usage:
    python -m app.workers.ingest_rss            # all active sources
    python -m app.workers.ingest_rss --lang=hi  # only Hindi sources

Wire this into a cron (GitHub Actions / Fly scheduled machine) every 15-30 min.
"""

from __future__ import annotations

import argparse
import asyncio

from app.core.logging import configure_logging, get_logger
from app.services.ingestion_service import run_ingestion

configure_logging()
log = get_logger(__name__)


async def main(language: str | None) -> None:
    stats = await run_ingestion(language=language)
    for s in stats:
        log.info("source_stats", **s.as_dict())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default=None, help="Limit to one language code, e.g. 'hi'")
    args = parser.parse_args()
    asyncio.run(main(args.lang))
