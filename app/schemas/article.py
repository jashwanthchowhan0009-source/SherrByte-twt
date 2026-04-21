"""Article API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    domain: str
    language: str


class TagOut(BaseModel):
    microtopic_slug: str
    microtopic_name: str
    pillar_slug: str
    confidence: float


class ArticleSummaryOut(BaseModel):
    """Lightweight shape for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    subtitle: str | None
    url: str
    image_url: str | None
    language: str
    author: str | None
    published_at: datetime
    source: SourceOut

    # Optional AI-enriched fields — populated if available, else null
    headline_rewrite: str | None = None
    summary_60w: str | None = None
    tags: list[TagOut] = []


class ArticleDetailOut(ArticleSummaryOut):
    """Full article body + full AI enrichment."""

    body: str
    wwww: dict[str, Any] | None = None
    key_entities: list[dict[str, Any]] | None = None
    quality_score: float | None = None


class ArticleListOut(BaseModel):
    items: list[ArticleSummaryOut]
    next_cursor: str | None = None


class PillarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name_en: str
    name_hi: str | None
    icon: str | None


class MicrotopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name_en: str
    name_hi: str | None
    pillar_slug: str


class TaxonomyOut(BaseModel):
    pillars: list[PillarOut]
    microtopics: list[MicrotopicOut]
