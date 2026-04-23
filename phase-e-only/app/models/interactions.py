"""Phase E ORM models — interactions, affinity, profile vectors, feed state."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger, Column, DateTime, Float, ForeignKey,
    Index, Integer, SmallInteger, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.session import Base


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    article_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    dwell_ms: Mapped[int] = mapped_column(Integer, default=0)
    scroll_pct: Mapped[int] = mapped_column(SmallInteger, default=0)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    interacted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), primary_key=True
    )

    __table_args__ = (
        Index("ix_ui_user_time", "user_id", "interacted_at"),
        Index("ix_ui_article", "article_id"),
        {"postgresql_partition_by": "RANGE (interacted_at)"},
    )


class UserTopicAffinity(Base):
    __tablename__ = "user_topic_affinity"

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    topic_slug: Mapped[str] = mapped_column(Text, primary_key=True)
    pillar_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    explicit_weight: Mapped[float] = mapped_column(Float, default=0.0)
    implicit_score: Mapped[float] = mapped_column(Float, default=0.0)
    combined_score: Mapped[float] = mapped_column(Float, default=0.0)
    article_count: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_uta_user", "user_id"),)


class UserProfileVector(Base):
    __tablename__ = "user_profile_vectors"

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    long_term_vec = Column(Vector(384), nullable=True)
    short_term_vec = Column(Vector(384), nullable=True)
    interaction_cnt: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FeedImpression(Base):
    __tablename__ = "feed_impressions"

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    article_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    served_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_fi_user", "user_id", "served_at"),)


class OnboardingState(Base):
    __tablename__ = "onboarding_state"

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    step: Mapped[int] = mapped_column(SmallInteger, default=0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_selections: Mapped[dict] = mapped_column(JSONB, default=dict)
