"""Seed the `sources` table with the curated Indian RSS list.

Usage:
    python -m app.workers.seed_sources
"""

from __future__ import annotations

import asyncio

from app.core.logging import configure_logging, get_logger
from app.db.session import session_scope
from app.repos.article_repo import SourceRepo
from app.workers.sources_seed import SEED_SOURCES

configure_logging()
log = get_logger(__name__)


async def main() -> None:
    async with session_scope() as db:
        repo = SourceRepo(db)
        for seed in SEED_SOURCES:
            src = await repo.upsert_from_seed(
                slug=seed.slug,
                name=seed.name,
                rss_url=seed.rss_url,
                homepage_url=seed.homepage_url,
                domain=seed.domain,
                language=seed.language,
                country=seed.country,
                priority_weight=seed.priority_weight,
                active=seed.active,
            )
            log.info("source_upserted", slug=src.slug, lang=src.language)
    log.info("seed_complete", total=len(SEED_SOURCES))


if __name__ == "__main__":
    asyncio.run(main())
