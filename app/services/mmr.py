from __future__ import annotations
import numpy as np

MMR_LAMBDA = 0.60
MAX_PER_SOURCE = 2
MAX_PER_TOPIC = 3

def _cosine(a, b):
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0

def mmr_rerank(articles: list[dict], target_n: int = 20, lam: float = MMR_LAMBDA) -> list[dict]:
    if not articles:
        return []
    remaining = list(articles)
    selected, selected_vecs = [], []
    source_counts, topic_counts = {}, {}
    while remaining and len(selected) < target_n:
        best_score, best_idx = -float("inf"), 0
        for i, art in enumerate(remaining):
            rel = max(art.get("relevance_score", 0.0), 0.1)
            vec = art.get("embedding")
            div = max(_cosine(vec, sv) for sv in selected_vecs) if vec and selected_vecs else 0.0
            mmr = lam * rel - (1 - lam) * div
            if mmr > best_score:
                best_score, best_idx = mmr, i
        winner = remaining.pop(best_idx)
        src = winner.get("source_name") or "__unknown__"
        topic = winner.get("micro_topic") or winner.get("category") or "__unknown__"
        if source_counts.get(src, 0) >= MAX_PER_SOURCE:
            continue
        if topic_counts.get(topic, 0) >= MAX_PER_TOPIC:
            continue
        selected.append(winner)
        source_counts[src] = source_counts.get(src, 0) + 1
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        if winner.get("embedding"):
            selected_vecs.append(winner["embedding"])
    return selected

def inject_trending(feed: list[dict], trending: list[dict], every_n: int = 5) -> list[dict]:
    feed_ids = {a["id"] for a in feed}
    clean = [a for a in trending if a["id"] not in feed_ids]
    if not clean:
        return feed
    result, ti = [], 0
    for i, art in enumerate(feed):
        result.append(art)
        if (i + 1) % every_n == 0 and ti < len(clean):
            result.append({**clean[ti], "is_trending": True})
            ti += 1
    return result