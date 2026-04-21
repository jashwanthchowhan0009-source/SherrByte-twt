"""Data access for AI-derived content."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import ArticleAI, ArticleEmbedding, ArticleTag, Microtopic, Pillar


class TaxonomyRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_pillars(self) -> list[Pillar]:
        rows = await self.db.execute(select(Pillar).order_by(Pillar.sort_order))
        return list(rows.scalars())

    async def list_microtopics(self) -> list[Microtopic]:
        rows = await self.db.execute(select(Microtopic).order_by(Microtopic.id))
        return list(rows.scalars())

    async def upsert_pillar(
        self,
        *,
        slug: str,
        name_en: str,
        name_hi: str | None,
        icon: str | None,
        sort_order: int,
    ) -> Pillar:
        existing = (
            await self.db.execute(select(Pillar).where(Pillar.slug == slug))
        ).scalar_one_or_none()
        if existing is not None:
            existing.name_en = name_en
            existing.name_hi = name_hi
            existing.icon = icon
            existing.sort_order = sort_order
            await self.db.flush()
            return existing
        p = Pillar(
            slug=slug, name_en=name_en, name_hi=name_hi, icon=icon, sort_order=sort_order
        )
        self.db.add(p)
        await self.db.flush()
        await self.db.refresh(p)
        return p

    async def upsert_microtopic(
        self,
        *,
        slug: str,
        pillar_id: int,
        name_en: str,
        name_hi: str | None,
        prompt_gloss: str,
    ) -> Microtopic:
        existing = (
            await self.db.execute(select(Microtopic).where(Microtopic.slug == slug))
        ).scalar_one_or_none()
        if existing is not None:
            existing.pillar_id = pillar_id
            existing.name_en = name_en
            existing.name_hi = name_hi
            existing.prompt_gloss = prompt_gloss
            await self.db.flush()
            return existing
        m = Microtopic(
            slug=slug,
            pillar_id=pillar_id,
            name_en=name_en,
            name_hi=name_hi,
            prompt_gloss=prompt_gloss,
        )
        self.db.add(m)
        await self.db.flush()
        await self.db.refresh(m)
        return m


class ArticleAIRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, article_id: uuid.UUID) -> ArticleAI | None:
        return await self.db.get(ArticleAI, article_id)

    async def upsert(
        self,
        *,
        article_id: uuid.UUID,
        headline_rewrite: str | None,
        summary_60w: str | None,
        wwww: dict[str, Any] | None,
        key_entities: list[dict[str, Any]] | None,
        quality_score: float | None,
        ai_model_used: str,
        prompt_version: str,
    ) -> ArticleAI:
        stmt = (
            pg_insert(ArticleAI)
            .values(
                article_id=article_id,
                headline_rewrite=headline_rewrite,
                summary_60w=summary_60w,
                wwww=wwww,
                key_entities=key_entities,
                quality_score=quality_score,
                ai_model_used=ai_model_used,
                prompt_version=prompt_version,
            )
            .on_conflict_do_update(
                index_elements=["article_id"],
                set_={
                    "headline_rewrite": headline_rewrite,
                    "summary_60w": summary_60w,
                    "wwww": wwww,
                    "key_entities": key_entities,
                    "quality_score": quality_score,
                    "ai_model_used": ai_model_used,
                    "prompt_version": prompt_version,
                },
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()
        # Refetch so expire_on_commit=False callers get fresh values
        got = await self.get(article_id)
        assert got is not None  # just-upserted row must exist
        return got

    async def list_missing_ai(self, limit: int = 100) -> list[uuid.UUID]:
        """Articles without AI enrichment yet. Used by the enrichment worker."""
        from app.models.article import Article  # local import avoids cycle

        stmt = (
            select(Article.id)
            .outerjoin(ArticleAI, ArticleAI.article_id == Article.id)
            .where(ArticleAI.article_id.is_(None), Article.deleted_at.is_(None))
            .order_by(Article.published_at.desc())
            .limit(limit)
        )
        return [r[0] for r in (await self.db.execute(stmt)).all()]


class EmbeddingRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(
        self,
        *,
        article_id: uuid.UUID,
        embedding: list[float],
        model_name: str,
    ) -> None:
        stmt = (
            pg_insert(ArticleEmbedding)
            .values(
                article_id=article_id,
                embedding=embedding,
                model_name=model_name,
            )
            .on_conflict_do_update(
                index_elements=["article_id"],
                set_={"embedding": embedding, "model_name": model_name},
            )
        )
        await self.db.execute(stmt)

    async def list_missing_embedding(self, limit: int = 100) -> list[uuid.UUID]:
        from app.models.article import Article

        stmt = (
            select(Article.id)
            .outerjoin(
                ArticleEmbedding, ArticleEmbedding.article_id == Article.id
            )
            .where(
                ArticleEmbedding.article_id.is_(None), Article.deleted_at.is_(None)
            )
            .order_by(Article.published_at.desc())
            .limit(limit)
        )
        return [r[0] for r in (await self.db.execute(stmt)).all()]


class ArticleTagRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def replace_tags(
        self,
        article_id: uuid.UUID,
        tags: list[tuple[int, int, float]],  # (microtopic_id, pillar_id, confidence)
        classifier_version: str,
    ) -> None:
        """Atomically replace all tags for an article."""
        await self.db.execute(
            delete(ArticleTag).where(ArticleTag.article_id == article_id)
        )
        for microtopic_id, pillar_id, confidence in tags:
            self.db.add(
                ArticleTag(
                    article_id=article_id,
                    microtopic_id=microtopic_id,
                    pillar_id=pillar_id,
                    confidence=confidence,
                    classifier_version=classifier_version,
                )
            )
        await self.db.flush()

    async def list_for_article(self, article_id: uuid.UUID) -> list[ArticleTag]:
        stmt = (
            select(ArticleTag)
            .where(ArticleTag.article_id == article_id)
            .order_by(ArticleTag.confidence.desc())
        )
        return list((await self.db.execute(stmt)).scalars())
