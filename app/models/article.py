"""Article ORM model.

Raw canonical article content. AI-derived fields (summary, WWWW, categories,
embeddings) live in separate tables so we can regenerate them without touching
the immutable article body.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        Index("ix_articles_published_at_desc", "published_at"),
        Index("ix_articles_source_published", "source_id", "published_at"),
        Index("ix_articles_simhash", "simhash"),
        Index("ix_articles_cluster_id", "cluster_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )

    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Dedup fingerprints — populated during ingestion.
    content_hash: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )  # sha256 of normalized body
    
    # Change from Numeric to String
    simhash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # Stored as string to prevent 64-bit overflow
    

    # Clustering (populated in Phase D when we have embeddings)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Editorial + engagement counters
    is_editorial_pick: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    view_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    save_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    share_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Soft delete — for editorial takedowns or DPDP-triggered removal
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )