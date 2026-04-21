"""Article + Source data access."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.source import Source


class SourceRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active(self, language: str | None = None) -> list[Source]:
        stmt = select(Source).where(Source.active.is_(True))
        if language:
            stmt = stmt.where(Source.language == language)
        stmt = stmt.order_by(Source.priority_weight.desc(), Source.id)
        return list((await self.db.execute(stmt)).scalars())

    async def get_by_slug(self, slug: str) -> Source | None:
        stmt = select(Source).where(Source.slug == slug)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def upsert_from_seed(
        self,
        *,
        slug: str,
        name: str,
        rss_url: str,
        homepage_url: str | None,
        domain: str,
        language: str,
        country: str,
        iab_tier1: str | None = None,  # Add '= None' here
        iab_tier2: str | None = None,  # Add '= None' here
        priority_weight: float,
        active: bool,
    ) -> Source:
        """Insert or update by slug — used by the seed worker so we don't dupe rows."""
        existing = await self.get_by_slug(slug)
        if existing is not None:
            existing.name = name
            existing.rss_url = rss_url
            existing.homepage_url = homepage_url
            existing.domain = domain
            existing.language = language
            existing.country = country
            existing.iab_tier1 = iab_tier1
            existing.priority_weight = priority_weight
            existing.active = active
            await self.db.flush()
            return existing

        src = Source(
            slug=slug,
            name=name,
            rss_url=rss_url,
            homepage_url=homepage_url,
            domain=domain,
            language=language,
            country=country,
            iab_tier1=iab_tier1,
            priority_weight=priority_weight,
            active=active,
        )
        self.db.add(src)
        await self.db.flush()
        await self.db.refresh(src)
        return src

    async def mark_fetched(self, source_id: int) -> None:
        stmt = (
            update(Source)
            .where(Source.id == source_id)
            .values(
                last_fetched_at=datetime.now(UTC),
                last_error=None,
                consecutive_errors=0,
            )
        )
        await self.db.execute(stmt)

    async def mark_error(self, source_id: int, error: str) -> None:
        stmt = (
            update(Source)
            .where(Source.id == source_id)
            .values(
                last_fetched_at=datetime.now(UTC),
                last_error=error[:2000],
                consecutive_errors=Source.consecutive_errors + 1,
            )
        )
        await self.db.execute(stmt)


class ArticleRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, article_id: uuid.UUID) -> Article | None:
        return await self.db.get(Article, article_id)

    async def exists_by_url(self, url: str) -> bool:
        stmt = select(Article.id).where(Article.url == url).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def exists_by_content_hash(self, content_hash: str) -> bool:
        stmt = select(Article.id).where(Article.content_hash == content_hash).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def recent_simhashes(self, hours: int = 72) -> list[tuple[uuid.UUID, int]]:
        """Return (id, simhash) pairs for articles ingested in the last N hours.
        Used by the near-dup check. Small table at our scale."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        stmt = select(Article.id, Article.simhash).where(
            and_(Article.ingested_at >= cutoff, Article.simhash.is_not(None))
        )
        rows = (await self.db.execute(stmt)).all()
        return [(r[0], r[1]) for r in rows]

    async def insert_ignore_duplicate(self, article: Article) -> Article | None:
        """Insert; if URL collides (race with another worker) return None."""
        stmt = (
            pg_insert(Article)
            .values(
                id=article.id,
                source_id=article.source_id,
                url=article.url,
                canonical_url=article.canonical_url,
                title=article.title,
                subtitle=article.subtitle,
                body=article.body,
                author=article.author,
                image_url=article.image_url,
                language=article.language,
                published_at=article.published_at,
                content_hash=article.content_hash,
                simhash=str(article.simhash) if article.simhash else None,
            )
            .on_conflict_do_nothing(index_elements=["url"])
            .returning(Article.id)
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if row is None:
            return None
        return article

    async def list_recent(
        self,
        *,
        limit: int = 20,
        before: datetime | None = None,
        source_id: int | None = None,
    ) -> list[Article]:
        stmt = (
            select(Article)
            .where(Article.deleted_at.is_(None))
            .order_by(Article.published_at.desc())
            .limit(limit)
        )
        if before is not None:
            stmt = stmt.where(Article.published_at < before)
        if source_id is not None:
            stmt = stmt.where(Article.source_id == source_id)
        return list((await self.db.execute(stmt)).scalars())
