"""Ingestion orchestration.

Pulls every active source, fetches each feed, for each item runs the three-layer
dedup (URL → content hash → simhash Hamming), fetches body, and inserts.
Per-source isolation: one broken publisher doesn't kill the whole run.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

from langdetect import DetectorFactory, LangDetectException, detect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.text import content_hash as hash_content
from app.core.text import hamming_distance, simhash64
from app.db.session import session_scope
from app.models.article import Article
from app.models.source import Source
from app.repos.article_repo import ArticleRepo, SourceRepo
from app.services.rss_fetcher import (
    FeedItem,
    build_http_client,
    fetch_article_body,
    fetch_feed,
)

# Deterministic language detection results
DetectorFactory.seed = 0

log = get_logger(__name__)

MIN_BODY_CHARS = 400          # reject stubs, index pages
SIMHASH_DUP_THRESHOLD = 3     # Hamming distance ≤ 3 → near-duplicate
CONCURRENT_ARTICLES = 5       # per source, to be polite


@dataclass
class IngestStats:
    source_slug: str
    fetched: int = 0
    skipped_url: int = 0
    skipped_hash: int = 0
    skipped_simhash: int = 0
    skipped_short: int = 0
    inserted: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, int | str]:
        return {
            "source": self.source_slug,
            "fetched": self.fetched,
            "inserted": self.inserted,
            "skipped_url": self.skipped_url,
            "skipped_hash": self.skipped_hash,
            "skipped_simhash": self.skipped_simhash,
            "skipped_short": self.skipped_short,
            "errors": self.errors,
        }


def _detect_language(text: str, fallback: str) -> str:
    if not text or len(text) < 50:
        return fallback
    try:
        return detect(text[:500])
    except LangDetectException:
        return fallback


async def ingest_one_source(
    db: AsyncSession,
    source: Source,
    recent_simhashes: list[tuple[uuid.UUID, int]],
) -> IngestStats:
    """Ingest one feed end-to-end. Mutates DB within the given session."""
    stats = IngestStats(source_slug=source.slug)
    articles = ArticleRepo(db)
    sources = SourceRepo(db)

    async with build_http_client() as client:
        try:
            items = await fetch_feed(client, source.rss_url)
        except Exception as e:
            stats.errors += 1
            await sources.mark_error(source.id, str(e))
            log.warning("source_fetch_failed", slug=source.slug, error=str(e))
            return stats

        stats.fetched = len(items)

        sem = asyncio.Semaphore(CONCURRENT_ARTICLES)

        async def process(item: FeedItem) -> None:
            async with sem:
                await _process_item(
                    client, db, source, item, recent_simhashes, stats
                )

        await asyncio.gather(*(process(i) for i in items), return_exceptions=False)

        await sources.mark_fetched(source.id)

    return stats


async def _process_item(
    client,  # type: ignore[no-untyped-def]
    db: AsyncSession,
    source: Source,
    item: FeedItem,
    recent_simhashes: list[tuple[uuid.UUID, int]],
    stats: IngestStats,
) -> None:
    articles = ArticleRepo(db)

    # Layer 1: URL dedup (cheapest)
    if await articles.exists_by_url(item.url):
        stats.skipped_url += 1
        return

    # Fetch body only after URL check passes
    try:
        body, og_image = await fetch_article_body(client, item.url)
    except Exception as e:
        stats.errors += 1
        log.info("article_body_failed", url=item.url, error=str(e))
        return

    # Fall back to RSS summary if body extraction failed
    if not body or len(body) < MIN_BODY_CHARS:
        if item.summary and len(item.summary) >= MIN_BODY_CHARS // 2:
            body = item.summary
        else:
            stats.skipped_short += 1
            return

    # Layer 2: exact content hash
    ch = hash_content(body)
    if await articles.exists_by_content_hash(ch):
        stats.skipped_hash += 1
        return

    # Layer 3: near-dup simhash
    sh = simhash64(body)
    if any(hamming_distance(sh, existing) <= SIMHASH_DUP_THRESHOLD for _, existing in recent_simhashes):
        stats.skipped_simhash += 1
        return

    # Compose and insert
    language = _detect_language(body, source.language)

    article = Article(
        id=uuid.uuid4(),
        source_id=source.id,
        url=item.url,
        title=item.title,
        subtitle=item.summary[:500] if item.summary else None,
        body=body,
        author=item.author,
        image_url=item.image_url or og_image,
        language=language,
        published_at=item.published_at,
        content_hash=ch,
        simhash=sh,
    )
    inserted = await articles.insert_ignore_duplicate(article)
    if inserted is None:
        stats.skipped_url += 1
        return

    # Add to in-memory simhash set so later items in the same run also dedup
    recent_simhashes.append((article.id, sh))
    stats.inserted += 1


async def run_ingestion(language: str | None = None) -> list[IngestStats]:
    """Top-level ingestion entry point. Called by the scheduled worker."""
    all_stats: list[IngestStats] = []

    async with session_scope() as db:
        sources_repo = SourceRepo(db)
        active = await sources_repo.list_active(language=language)
        if not active:
            log.warning("no_active_sources")
            return all_stats

        # Load recent simhashes once; mutated as we insert
        recent = await ArticleRepo(db).recent_simhashes(hours=72)
        log.info("ingestion_starting", sources=len(active), recent_items=len(recent))

        # Sources in parallel, but cap concurrency to avoid overwhelming memory/sockets
        src_sem = asyncio.Semaphore(4)

        async def run_one(src: Source) -> IngestStats:
            async with src_sem:
                return await ingest_one_source(db, src, recent)

        results = await asyncio.gather(*(run_one(s) for s in active))
        all_stats.extend(results)

    totals = {
        "sources": len(all_stats),
        "fetched": sum(s.fetched for s in all_stats),
        "inserted": sum(s.inserted for s in all_stats),
        "skipped_url": sum(s.skipped_url for s in all_stats),
        "skipped_hash": sum(s.skipped_hash for s in all_stats),
        "skipped_simhash": sum(s.skipped_simhash for s in all_stats),
        "skipped_short": sum(s.skipped_short for s in all_stats),
        "errors": sum(s.errors for s in all_stats),
    }
    log.info("ingestion_complete", **totals)
    return all_stats
