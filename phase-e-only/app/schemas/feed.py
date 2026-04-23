"""Phase E — Pydantic schemas for feed responses and onboarding flow."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class FeedArticle(BaseModel):
    id: uuid.UUID
    title: str
    cached_summary: Optional[str] = None
    image_url: Optional[str] = None
    source_name: Optional[str] = None
    category: Optional[str] = None
    micro_topic: Optional[str] = None
    published_at: Optional[datetime] = None
    is_trending: bool = False
    relevance_score: float = 0.0


class FeedResponse(BaseModel):
    articles: list[FeedArticle]
    next_cursor: Optional[str] = None
    feed_type: Literal["personalised", "cold_start", "fallback"] = "personalised"


class TopicSelection(BaseModel):
    topic_slugs: list[str] = Field(
        min_length=5, max_length=30,
        description="Minimum 5 topics required to unlock personalised feed"
    )

    @field_validator("topic_slugs")
    @classmethod
    def no_duplicates(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out = []
        for slug in v:
            if slug not in seen:
                seen.add(slug)
                out.append(slug)
        return out


class SourceOptOut(BaseModel):
    source_ids: list[uuid.UUID] = Field(default_factory=list)


class OnboardingStatus(BaseModel):
    step: int
    is_complete: bool
    selected_topics: list[str]
    opted_out_sources: list[uuid.UUID]
