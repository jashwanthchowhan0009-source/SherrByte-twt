"""Phase D unit tests.

All pure-logic — no DB, no Redis, no network. Runs in CI without any secrets.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.services.ai_service import (
    MIN_TAG_CONFIDENCE,
    TOP_K_TAGS,
    _cache_key,
    _hash_prompt_input,
)
from app.services.prompts import PROMPT_VERSION, build_wwww_prompt


# ---------------- Prompt ----------------


def test_prompt_contains_article_body() -> None:
    body = "The Reserve Bank of India kept the repo rate unchanged today."
    prompt = build_wwww_prompt(body)
    assert body in prompt
    assert "JSON" in prompt  # format instruction present
    assert "55-65 words" in prompt  # word budget enforced


def test_prompt_truncates_long_articles() -> None:
    long_body = "x" * 20_000
    prompt = build_wwww_prompt(long_body, max_chars=8000)
    # Body should be clipped; a sentinel marker should appear
    assert "[...truncated]" in prompt
    # And the embedded body portion must be shorter than the original
    assert len(prompt) < len(long_body) + 2000


def test_prompt_leaves_short_articles_intact() -> None:
    body = "Short article body."
    prompt = build_wwww_prompt(body)
    assert "[...truncated]" not in prompt
    assert body in prompt


def test_prompt_version_is_set() -> None:
    assert PROMPT_VERSION  # non-empty
    assert isinstance(PROMPT_VERSION, str)


# ---------------- Cache key ----------------


def test_cache_key_is_deterministic() -> None:
    body = "Same article body, verbatim."
    k1 = _cache_key(_hash_prompt_input(body), PROMPT_VERSION)
    k2 = _cache_key(_hash_prompt_input(body), PROMPT_VERSION)
    assert k1 == k2


def test_cache_key_ignores_formatting() -> None:
    # normalize_body flattens whitespace + lowercases, so these should share key
    k1 = _cache_key(_hash_prompt_input("The RBI HELD rates today."), PROMPT_VERSION)
    k2 = _cache_key(
        _hash_prompt_input("  the   rbi  HELD  rates   today.  "), PROMPT_VERSION
    )
    assert k1 == k2


def test_cache_key_differs_for_different_content() -> None:
    k1 = _cache_key(_hash_prompt_input("Article A content."), PROMPT_VERSION)
    k2 = _cache_key(_hash_prompt_input("Article B content."), PROMPT_VERSION)
    assert k1 != k2


def test_cache_key_includes_prompt_version() -> None:
    body = "Same body."
    k_v1 = _cache_key(_hash_prompt_input(body), "v1")
    k_v2 = _cache_key(_hash_prompt_input(body), "v2")
    assert k_v1 != k_v2  # version bump must invalidate cache


def test_cache_key_shape() -> None:
    key = _cache_key("abc123", "v7")
    assert key.startswith("ai:wwww:v7:abc123")


# ---------------- Categorization math (no ML call) ----------------


def _mock_vec(seed: int, dim: int = 384) -> list[float]:
    """Deterministic L2-normalized vector — stand-in for an embedding."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    v /= np.linalg.norm(v)
    return v.tolist()


def test_cosine_top_k_picks_most_similar() -> None:
    """The scoring logic we use inline in enrich_article — verified in isolation."""
    # Query matches vec 2 exactly
    query = np.asarray(_mock_vec(42), dtype=np.float32)

    matrix = np.stack(
        [
            np.asarray(_mock_vec(1), dtype=np.float32),
            np.asarray(_mock_vec(2), dtype=np.float32),
            query,                           # index 2 — perfect match
            np.asarray(_mock_vec(4), dtype=np.float32),
            np.asarray(_mock_vec(5), dtype=np.float32),
        ]
    )
    scores = matrix @ query
    top = np.argsort(-scores)[:TOP_K_TAGS]
    assert top[0] == 2                       # perfect match comes first
    assert float(scores[2]) == pytest.approx(1.0, abs=1e-5)


def test_tag_confidence_threshold_filters_low_scores() -> None:
    # All scores below threshold → no tags
    low_scores = np.array([0.1, 0.15, 0.2])
    assert not any(s >= MIN_TAG_CONFIDENCE for s in low_scores)
    # Mix → only the ones above threshold survive
    mixed = np.array([0.1, 0.3, 0.5])
    passing = [s for s in mixed if s >= MIN_TAG_CONFIDENCE]
    assert len(passing) == 2


def test_normalized_vectors_dot_product_equals_cosine() -> None:
    a = np.asarray(_mock_vec(7), dtype=np.float32)
    b = np.asarray(_mock_vec(8), dtype=np.float32)
    dot = float(np.dot(a, b))
    cosine = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    # Since both already L2-normalized, the two must match to float precision
    assert dot == pytest.approx(cosine, abs=1e-6)
    # And be bounded
    assert -1.0 <= dot <= 1.0
