"""v1 API router.

Phase A: /health. Phase B: /auth. Phase C: /articles + /sources.
Phase D: /taxonomy + AI fields on article responses.
"""

from fastapi import APIRouter

from app.api.v1 import articles, auth, health

from app.api.v1.endpoints import feed, interactions, onboarding

api_router.include_router(feed.router, tags=["feed"])
api_router.include_router(interactions.router, tags=["interactions"])
api_router.include_router(onboarding.router, tags=["onboarding"])
api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(articles.router, prefix="/articles", tags=["articles"])
api_router.include_router(articles.sources_router, prefix="/sources", tags=["sources"])
api_router.include_router(articles.taxonomy_router, prefix="/taxonomy", tags=["taxonomy"])

# Phase E: api_router.include_router(feed.router, prefix="/feed", tags=["feed"])
