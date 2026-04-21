"""Seed the pillars + microtopics tables.

Usage: python -m app.workers.seed_taxonomy

Safe to re-run — uses upsert. Re-run after you edit PILLARS or MICROTOPICS.
"""

from __future__ import annotations

import asyncio

from app.core.logging import configure_logging, get_logger
from app.db.session import session_scope
from app.repos.ai_repo import TaxonomyRepo
from app.workers.taxonomy_seed import MICROTOPICS, PILLARS

configure_logging()
log = get_logger(__name__)


async def main() -> None:
    async with session_scope() as db:
        repo = TaxonomyRepo(db)

        # Pillars first (microtopics FK onto them)
        slug_to_pillar_id: dict[str, int] = {}
        for seed in PILLARS:
            p = await repo.upsert_pillar(
                slug=seed.slug,
                name_en=seed.name_en,
                name_hi=seed.name_hi,
                icon=seed.icon,
                sort_order=seed.sort_order,
            )
            slug_to_pillar_id[seed.slug] = p.id

        for mt in MICROTOPICS:
            pid = slug_to_pillar_id.get(mt.pillar_slug)
            if pid is None:
                log.warning("microtopic_orphaned", slug=mt.slug, pillar=mt.pillar_slug)
                continue
            await repo.upsert_microtopic(
                slug=mt.slug,
                pillar_id=pid,
                name_en=mt.name_en,
                name_hi=mt.name_hi,
                prompt_gloss=mt.prompt_gloss,
            )

    log.info("taxonomy_seeded", pillars=len(PILLARS), microtopics=len(MICROTOPICS))


if __name__ == "__main__":
    asyncio.run(main())
