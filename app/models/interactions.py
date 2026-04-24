from sqlalchemy import Column, String, DateTime, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base

import uuid

class OnboardingState(Base):
    __tablename__ = "onboarding_state"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step = Column(Integer, default=0)
    selected_topics = Column(JSON, default=list)
    raw_selections = Column(JSON, default=dict)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class FeedImpression(Base):
    __tablename__ = "feed_impressions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), index=True)
    article_id = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())