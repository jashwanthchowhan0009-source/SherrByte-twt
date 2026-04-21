"""Source ORM model — an RSS publisher (NDTV, Inshorts, etc.)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rss_url: Mapped[str] = mapped_column(Text, nullable=False)
    homepage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    country: Mapped[str] = mapped_column(String(5), default="IN", nullable=False)
    iab_tier1: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Editorial signals (populated later, null for now)
    bias_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    factuality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Ingestion bookkeeping
    last_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
