"""AI-derived article content, stored separately from `articles`.

Design reasoning:
- `article_ai` — summary, WWWW, headline rewrite. Regenerable.
- `article_tags` — multi-label categorization (pillar + microtopic + confidence).
- `article_embeddings` — one pgvector row per article for semantic search.
- `pillars` / `microtopics` — canonical taxonomy (seeded once).

Keeping AI output separate from canonical article content means we can rerun
prompts after a model upgrade without risking the raw body.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# Embedding dimension of all-MiniLM-L6-v2 (the default local encoder)
EMBEDDING_DIM = 384


class Pillar(Base):
    """Top-level taxonomy bucket: 9 rows."""

    __tablename__ = "pillars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_hi: Mapped[str | None] = mapped_column(String(100), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Microtopic(Base):
    """Leaf taxonomy node. ~400 rows, seeded from sources_seed."""

    __tablename__ = "microtopics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pillar_id: Mapped[int] = mapped_column(
        ForeignKey("pillars.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_hi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prompt_gloss: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=""
    )  # Natural-language sentence used for zero-shot embedding matching


class ArticleAI(Base):
    """AI-generated fields for one article. 1:1 with `articles`."""

    __tablename__ = "article_ai"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    headline_rewrite: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_60w: Mapped[str | None] = mapped_column(Text, nullable=True)
    wwww: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # noqa: UP006
    key_entities: Mapped[list | None] = mapped_column(JSON, nullable=True)  # noqa: UP006

    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    readability_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    ai_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ArticleTag(Base):
    """Multi-label classification. One row per (article, microtopic)."""

    __tablename__ = "article_tags"
    __table_args__ = (
        Index("ix_article_tags_microtopic_confidence", "microtopic_id", "confidence"),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    microtopic_id: Mapped[int] = mapped_column(
        ForeignKey("microtopics.id", ondelete="CASCADE"),
        primary_key=True,
    )
    pillar_id: Mapped[int] = mapped_column(
        ForeignKey("pillars.id", ondelete="CASCADE"), nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    classifier_version: Mapped[str] = mapped_column(
        String(20), default="zs-minilm-v1", nullable=False
    )


class ArticleEmbedding(Base):
    """384-dim vector (all-MiniLM-L6-v2) for each article. Used for semantic
    search, clustering, and the recommender's content-similarity term."""

    __tablename__ = "article_embeddings"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    model_name: Mapped[str] = mapped_column(
        String(100), default="all-MiniLM-L6-v2", nullable=False
    )
    embedded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
