"""AI enrichment service.

For each unenriched article:
  1. Check Redis cache keyed on (content_hash, prompt_version). If hit, reuse.
  2. Otherwise call the LLM router for WWWW + summary + headline + entities.
  3. Categorize via zero-shot embedding against microtopic glosses.
  4. Encode article embedding.
  5. Persist all three outputs.

Each article touches the LLM at most once. Articles with quality_score < 0.3
get flagged but still stored — the feed ranker will downweight them.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get_json, cache_set_json
from app.core.logging import get_logger
from app.core.text import normalize_body
from app.db.session import session_scope
from app.models.article import Article
from app.models.ai import Microtopic
from app.repos.ai_repo import (
    ArticleAIRepo,
    ArticleTagRepo,
    EmbeddingRepo,
    TaxonomyRepo,
)
from app.services import embedding, llm_router
from app.services.prompts import PROMPT_VERSION, build_wwww_prompt

log = get_logger(__name__)


# Categorization thresholds
TOP_K_TAGS = 3                    # max tags per article
MIN_TAG_CONFIDENCE = 0.25         # cosine threshold in normalized space
CACHE_TTL_SECONDS = 14 * 24 * 3600  # 14 days


@dataclass
class EnrichmentStats:
    processed: int = 0
    enriched: int = 0
    cache_hits: int = 0
    llm_failures: int = 0
    tagged: int = 0
    embedded: int = 0


def _cache_key(content_hash: str, prompt_version: str) -> str:
    return f"ai:wwww:{prompt_version}:{content_hash}"


def _hash_prompt_input(body: str) -> str:
    """What we key cache by — normalized body so formatting-only changes share cache."""
    return hashlib.sha256(normalize_body(body).encode("utf-8")).hexdigest()


# ---------------- Gloss matrix (built once per process) ----------------


_GLOSS_MATRIX: tuple[np.ndarray, list[tuple[int, int]]] | None = None
_GLOSS_READY = False


async def _ensure_gloss_matrix(db: AsyncSession) -> tuple[np.ndarray, list[tuple[int, int]]] | None:
    """Load and encode all microtopic glosses once. Returns (matrix, [(microtopic_id, pillar_id), ...])."""
    global _GLOSS_MATRIX, _GLOSS_READY
    if _GLOSS_READY and _GLOSS_MATRIX is not None:
        return _GLOSS_MATRIX

    rows = (await db.execute(select(Microtopic))).scalars().all()
    if not rows:
        log.warning("no_microtopics_seeded")
        _GLOSS_READY = True  # don't keep retrying this query
        return None

    glosses = [r.prompt_gloss or r.name_en for r in rows]
    vecs = await embedding.encode(glosses)
    matrix = np.asarray(vecs, dtype=np.float32)  # (N, 384), already L2-normalized
    meta = [(r.id, r.pillar_id) for r in rows]
    _GLOSS_MATRIX = (matrix, meta)
    _GLOSS_READY = True
    log.info("gloss_matrix_built", microtopics=len(rows))
    return _GLOSS_MATRIX


# ---------------- Per-article pipeline ----------------


async def enrich_article(db: AsyncSession, article: Article, stats: EnrichmentStats) -> None:
    # --- Summarization (with cache) ---
    cache_key = _cache_key(_hash_prompt_input(article.body), PROMPT_VERSION)
    cached = await cache_get_json(cache_key)

    ai_data: dict | None = None
    ai_model = "cache"
    if cached is not None:
        ai_data = cached
        stats.cache_hits += 1
    else:
        try:
            resp = await llm_router.complete_json(build_wwww_prompt(article.body))
            ai_data = resp.data
            ai_model = f"{resp.provider}:{resp.model}"
            await cache_set_json(cache_key, ai_data, ttl_seconds=CACHE_TTL_SECONDS)
        except llm_router.LLMUnavailableError as e:
            stats.llm_failures += 1
            log.warning("enrich_llm_unavailable", article_id=str(article.id), error=str(e))
        except Exception as e:
            stats.llm_failures += 1
            log.warning("enrich_llm_failed", article_id=str(article.id), error=str(e))

    if ai_data is not None:
        await ArticleAIRepo(db).upsert(
            article_id=article.id,
            headline_rewrite=ai_data.get("headline_rewrite"),
            summary_60w=ai_data.get("summary_60w"),
            wwww=ai_data.get("wwww"),
            key_entities=ai_data.get("key_entities"),
            quality_score=ai_data.get("quality_score"),
            ai_model_used=ai_model,
            prompt_version=PROMPT_VERSION,
        )
        stats.enriched += 1

    # --- Embedding (always, cheap) ---
    text_for_embed = article.title
    if ai_data and ai_data.get("summary_60w"):
        text_for_embed = f"{article.title}. {ai_data['summary_60w']}"
    elif article.subtitle:
        text_for_embed = f"{article.title}. {article.subtitle}"

    vec = await embedding.encode_one(text_for_embed)
    await EmbeddingRepo(db).upsert(
        article_id=article.id,
        embedding=vec,
        model_name=embedding.model_name(),
    )
    stats.embedded += 1

    # --- Categorization (zero-shot cosine vs gloss matrix) ---
    gloss = await _ensure_gloss_matrix(db)
    if gloss is not None:
        matrix, meta = gloss
        query = np.asarray(vec, dtype=np.float32)
        # Both matrices are L2-normalized, so dot product == cosine similarity.
        scores = matrix @ query  # shape: (N,)
        top_idx = np.argsort(-scores)[:TOP_K_TAGS]
        tags: list[tuple[int, int, float]] = []
        for idx in top_idx:
            conf = float(scores[idx])
            if conf < MIN_TAG_CONFIDENCE:
                continue
            microtopic_id, pillar_id = meta[idx]
            tags.append((microtopic_id, pillar_id, conf))
        if tags:
            await ArticleTagRepo(db).replace_tags(
                article_id=article.id,
                tags=tags,
                classifier_version="zs-minilm-v1",
            )
            stats.tagged += 1


# ---------------- Batch runner ----------------


async def enrich_batch(limit: int = 50) -> EnrichmentStats:
    """Process up to `limit` un-enriched articles. Safe to run concurrently."""
    stats = EnrichmentStats()

    async with session_scope() as db:
        ai_repo = ArticleAIRepo(db)
        article_ids = await ai_repo.list_missing_ai(limit=limit)
        if not article_ids:
            log.info("enrich_nothing_to_do")
            return stats

        log.info("enrich_batch_starting", count=len(article_ids))
        # Pre-warm the gloss matrix so we pay the cost once per run
        await _ensure_gloss_matrix(db)

        for aid in article_ids:
            article = await db.get(Article, aid)
            if article is None:
                continue
            stats.processed += 1
            try:
                await enrich_article(db, article, stats)
            except Exception as e:
                log.exception("enrich_article_failed", article_id=str(aid), error=str(e))

    log.info(
        "enrich_batch_complete",
        processed=stats.processed,
        enriched=stats.enriched,
        cache_hits=stats.cache_hits,
        embedded=stats.embedded,
        tagged=stats.tagged,
        llm_failures=stats.llm_failures,
    )
    return stats
