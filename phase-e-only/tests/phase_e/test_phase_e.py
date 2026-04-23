"""Phase E unit tests — 18 tests, no DB/Redis needed."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest


class TestFreshness:
    def test_fresh_near_1(self):
        from app.services.scorer import _freshness
        assert _freshness(datetime.now(timezone.utc) - timedelta(minutes=5)) > 0.95

    def test_12h_half(self):
        from app.services.scorer import _freshness
        s = _freshness(datetime.now(timezone.utc) - timedelta(hours=12))
        assert 0.48 < s < 0.52

    def test_old_small(self):
        from app.services.scorer import _freshness
        assert _freshness(datetime.now(timezone.utc) - timedelta(days=5)) < 0.05

    def test_none_fallback(self):
        from app.services.scorer import _freshness
        assert _freshness(None) == 0.3


class TestCosine:
    def test_identical(self):
        from app.services.scorer import _cosine
        v = [1.0, 0.5, 0.3]
        assert abs(_cosine(v, v) - 1.0) < 1e-5

    def test_orthogonal(self):
        from app.services.scorer import _cosine
        assert abs(_cosine([1, 0], [0, 1])) < 1e-5

    def test_zero_safe(self):
        from app.services.scorer import _cosine
        assert _cosine([0.0, 0.0], [1.0, 0.5]) == 0.0


class TestMMR:
    def _arts(self, n, same_src=False):
        return [{
            "id": uuid.uuid4(),
            "relevance_score": 1.0 - i * 0.05,
            "embedding": [float(i % 5), float((i + 1) % 5)],
            "source_name": "TOI" if same_src else f"Source{i}",
            "micro_topic": f"topic_{i % 4}",
        } for i in range(n)]

    def test_max_n(self):
        from app.services.mmr import mmr_rerank
        assert len(mmr_rerank(self._arts(50), target_n=20)) <= 20

    def test_source_cap(self):
        from app.services.mmr import mmr_rerank, MAX_PER_SOURCE
        result = mmr_rerank(self._arts(30, same_src=True), target_n=20)
        assert sum(1 for a in result if a["source_name"] == "TOI") <= MAX_PER_SOURCE

    def test_empty(self):
        from app.services.mmr import mmr_rerank
        assert mmr_rerank([]) == []

    def test_no_duplicates_in_trending(self):
        from app.services.mmr import inject_trending
        ids = [uuid.uuid4() for _ in range(10)]
        feed     = [{"id": ids[i], "is_trending": False} for i in range(8)]
        trending = [{"id": ids[1]}, {"id": uuid.uuid4()}]
        result   = inject_trending(feed, trending, every_n=5)
        trending_ids = [a["id"] for a in result if a.get("is_trending")]
        assert ids[1] not in trending_ids


class TestAffinity:
    def test_sigmoid_zero(self):
        from app.services.affinity import _sigmoid
        assert abs(_sigmoid(0) - 0.5) < 0.01

    def test_sigmoid_large_pos(self):
        from app.services.affinity import _sigmoid
        assert _sigmoid(50) > 0.99

    def test_sigmoid_large_neg(self):
        from app.services.affinity import _sigmoid
        assert _sigmoid(-50) < 0.01


class TestSchemas:
    def test_batch_empty_rejected(self):
        from app.schemas.events import InteractionBatch
        with pytest.raises(Exception):
            InteractionBatch(events=[])

    def test_batch_over_50_rejected(self):
        from app.schemas.events import InteractionBatch, InteractionEvent
        with pytest.raises(Exception):
            InteractionBatch(events=[
                InteractionEvent(article_id=uuid.uuid4(), event_type="open")
                for _ in range(51)
            ])

    def test_topic_selection_min_5(self):
        from app.schemas.feed import TopicSelection
        with pytest.raises(Exception):
            TopicSelection(topic_slugs=["a", "b", "c"])

    def test_topic_selection_dedupes(self):
        from app.schemas.feed import TopicSelection
        sel = TopicSelection(topic_slugs=["a", "b", "c", "d", "e", "a", "b"])
        assert len(sel.topic_slugs) == 5


class TestProfileVectors:
    def test_norm_unit(self):
        from app.services.profile_vectors import _norm
        v = np.array([3.0, 4.0])
        assert abs(np.linalg.norm(_norm(v)) - 1.0) < 1e-5

    def test_norm_zero_safe(self):
        from app.services.profile_vectors import _norm
        v = np.array([0.0, 0.0])
        assert all(_norm(v) == 0.0)
