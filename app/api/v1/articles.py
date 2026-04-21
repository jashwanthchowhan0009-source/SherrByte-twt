"""Public article endpoints.

- GET /v1/articles            — latest, cursor-paginated by published_at desc
- GET /v1/articles/{id}       — full article with body + AI fields
- GET /v1/sources             — list of active sources
- GET /v1/taxonomy            — pillars + microtopics

These are public (no auth) for Phase C/D. Phase E will add /v1/feed which IS
personalized and requires auth.
"""

from __future__ import annotations

import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.deps import DB
from app.models.ai import ArticleAI, ArticleTag, Microtopic, Pillar
from app.models.article import Article
from app.models.source import Source
from app.repos.ai_repo import ArticleAIRepo, ArticleTagRepo, TaxonomyRepo
from app.repos.article_repo import ArticleRepo, SourceRepo
from app.schemas.article import (
    ArticleDetailOut,
    ArticleListOut,
    ArticleSummaryOut,
    MicrotopicOut,
    PillarOut,
    SourceOut,
    TagOut,
    TaxonomyOut,
)

router = APIRouter()
sources_router = APIRouter()
taxonomy_router = APIRouter()


def _encode_cursor(dt: datetime) -> str:
    return urlsafe_b64encode(dt.isoformat().encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> datetime | None:
    try:
        raw = urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


# ---------------- /sources ----------------


@sources_router.get("", response_model=list[SourceOut], tags=["sources"])
async def list_sources(db: DB) -> list[SourceOut]:
    rows = await SourceRepo(db).list_active()
    return [SourceOut.model_validate(r) for r in rows]


# ---------------- /taxonomy ----------------


@taxonomy_router.get("", response_model=TaxonomyOut, tags=["taxonomy"])
async def get_taxonomy(db: DB) -> TaxonomyOut:
    repo = TaxonomyRepo(db)
    pillars = await repo.list_pillars()
    microtopics = await repo.list_microtopics()
    pillar_map = {p.id: p.slug for p in pillars}

    return TaxonomyOut(
        pillars=[PillarOut.model_validate(p) for p in pillars],
        microtopics=[
            MicrotopicOut(
                id=m.id,
                slug=m.slug,
                name_en=m.name_en,
                name_hi=m.name_hi,
                pillar_slug=pillar_map.get(m.pillar_id, "unknown"),
            )
            for m in microtopics
        ],
    )


# ---------------- /articles ----------------


async def _load_ai_and_tags(
    db,  # type: ignore[no-untyped-def]
    article_ids: list[uuid.UUID],
) -> tuple[dict[uuid.UUID, ArticleAI], dict[uuid.UUID, list[TagOut]]]:
    """Batch-load AI + tags for N articles in two queries."""
    if not article_ids:
        return {}, {}

    ai_rows = (
        await db.execute(select(ArticleAI).where(ArticleAI.article_id.in_(article_ids)))
    ).scalars()
    ai_map: dict[uuid.UUID, ArticleAI] = {a.article_id: a for a in ai_rows}

    tag_rows = (
        await db.execute(
            select(ArticleTag, Microtopic, Pillar)
            .join(Microtopic, ArticleTag.microtopic_id == Microtopic.id)
            .join(Pillar, ArticleTag.pillar_id == Pillar.id)
            .where(ArticleTag.article_id.in_(article_ids))
            .order_by(ArticleTag.confidence.desc())
        )
    ).all()
    tag_map: dict[uuid.UUID, list[TagOut]] = {}
    for tag, mt, p in tag_rows:
        tag_map.setdefault(tag.article_id, []).append(
            TagOut(
                microtopic_slug=mt.slug,
                microtopic_name=mt.name_en,
                pillar_slug=p.slug,
                confidence=round(tag.confidence, 3),
            )
        )
    return ai_map, tag_map


@router.get("", response_model=ArticleListOut, tags=["articles"])
async def list_articles(
    db: DB,
    cursor: str | None = Query(default=None, description="Opaque pagination cursor"),
    limit: int = Query(default=20, ge=1, le=50),
    source: str | None = Query(default=None, description="Filter by source slug"),
    language: str | None = Query(default=None, description="Filter by language"),
    pillar: str | None = Query(default=None, description="Filter by pillar slug"),
) -> ArticleListOut:
    before = _decode_cursor(cursor) if cursor else None

    source_id: int | None = None
    if source:
        src = await SourceRepo(db).get_by_slug(source)
        if src is None:
            return ArticleListOut(items=[], next_cursor=None)
        source_id = src.id

    pillar_id: int | None = None
    if pillar:
        pr = (
            await db.execute(select(Pillar).where(Pillar.slug == pillar))
        ).scalar_one_or_none()
        if pr is None:
            return ArticleListOut(items=[], next_cursor=None)
        pillar_id = pr.id

    stmt = (
        select(Article, Source)
        .join(Source, Article.source_id == Source.id)
        .where(Article.deleted_at.is_(None))
        .order_by(Article.published_at.desc())
        .limit(limit + 1)
    )
    if before is not None:
        stmt = stmt.where(Article.published_at < before)
    if source_id is not None:
        stmt = stmt.where(Article.source_id == source_id)
    if language:
        stmt = stmt.where(Article.language == language)
    if pillar_id is not None:
        stmt = stmt.join(ArticleTag, ArticleTag.article_id == Article.id).where(
            ArticleTag.pillar_id == pillar_id
        ).distinct()

    rows = (await db.execute(stmt)).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    article_ids = [a.id for (a, _s) in rows]
    ai_map, tag_map = await _load_ai_and_tags(db, article_ids)

    items: list[ArticleSummaryOut] = []
    for a, s in rows:
        ai = ai_map.get(a.id)
        items.append(
            ArticleSummaryOut(
                id=a.id,
                title=a.title,
                subtitle=a.subtitle,
                url=a.url,
                image_url=a.image_url,
                language=a.language,
                author=a.author,
                published_at=a.published_at,
                source=SourceOut.model_validate(s),
                headline_rewrite=ai.headline_rewrite if ai else None,
                summary_60w=ai.summary_60w if ai else None,
                tags=tag_map.get(a.id, []),
            )
        )

    next_cursor = _encode_cursor(items[-1].published_at) if has_more and items else None
    return ArticleListOut(items=items, next_cursor=next_cursor)


@router.get("/{article_id}", response_model=ArticleDetailOut, tags=["articles"])
async def get_article(article_id: uuid.UUID, db: DB) -> ArticleDetailOut:
    article = await ArticleRepo(db).get_by_id(article_id)
    if article is None or article.deleted_at is not None:
        raise NotFoundError("Article not found.")
    source = await db.get(Source, article.source_id)
    if source is None:
        raise NotFoundError("Article source missing.")

    ai = await ArticleAIRepo(db).get(article.id)
    tag_rows = (
        await db.execute(
            select(ArticleTag, Microtopic, Pillar)
            .join(Microtopic, ArticleTag.microtopic_id == Microtopic.id)
            .join(Pillar, ArticleTag.pillar_id == Pillar.id)
            .where(ArticleTag.article_id == article.id)
            .order_by(ArticleTag.confidence.desc())
        )
    ).all()
    tags = [
        TagOut(
            microtopic_slug=mt.slug,
            microtopic_name=mt.name_en,
            pillar_slug=p.slug,
            confidence=round(t.confidence, 3),
        )
        for t, mt, p in tag_rows
    ]

    return ArticleDetailOut(
        id=article.id,
        title=article.title,
        subtitle=article.subtitle,
        url=article.url,
        image_url=article.image_url,
        language=article.language,
        author=article.author,
        published_at=article.published_at,
        body=article.body,
        source=SourceOut.model_validate(source),
        headline_rewrite=ai.headline_rewrite if ai else None,
        summary_60w=ai.summary_60w if ai else None,
        wwww=ai.wwww if ai else None,
        key_entities=ai.key_entities if ai else None,
        quality_score=ai.quality_score if ai else None,
        tags=tags,
    )
