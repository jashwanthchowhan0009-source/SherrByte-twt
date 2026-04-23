"""Nightly ALS training worker.

Trains implicit ALS on the full user-article interaction matrix.
Model saved to /tmp/als_model.npz for Phase F+ usage.
Runs at 02:00 IST (20:30 UTC) — after recompute_affinity.

GitHub Actions cron: '30 20 * * *'
Usage: python -m app.workers.als_train
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

logger   = logging.getLogger(__name__)
MODEL_PATH = Path("/tmp/als_model.npz")

EVENT_WEIGHTS = {
    "open": 1.0, "dwell": 2.0, "save": 3.0, "share": 4.0,
    "scroll": 0.3, "impression": 0.1,
}


async def run() -> dict:
    try:
        import implicit
    except ImportError:
        logger.error("'implicit' not installed. Run: uv pip install implicit")
        return {"error": "implicit not installed"}

    t0 = time.time()

    from app.db.session import SessionLocal
    from sqlalchemy import text

    async with SessionLocal() as db:
        rows = await db.execute(text("""
            SELECT user_id::text, article_id::text, event_type, dwell_ms
            FROM user_interactions
            WHERE event_type NOT IN ('skip', 'hide', 'mute_source')
              AND interacted_at >= NOW() - INTERVAL '180 days'
        """))
        data = rows.fetchall()

    if not data:
        logger.warning("No interaction data — skipping ALS")
        return {"users_trained": 0, "items_trained": 0, "duration_seconds": 0.0}

    user_ids    = sorted(set(r[0] for r in data))
    article_ids = sorted(set(r[1] for r in data))
    uid_idx     = {u: i for i, u in enumerate(user_ids)}
    aid_idx     = {a: i for i, a in enumerate(article_ids)}

    ri, ci, vi = [], [], []
    for uid, aid, evt, dwell_ms in data:
        w = EVENT_WEIGHTS.get(evt, 0.0)
        if evt == "dwell" and dwell_ms:
            w += min(dwell_ms / 30_000 * 0.5, 3.0)
        if w > 0:
            ri.append(uid_idx[uid]); ci.append(aid_idx[aid]); vi.append(w)

    matrix = sp.coo_matrix(
        (vi, (ri, ci)), shape=(len(user_ids), len(article_ids)), dtype=np.float32
    ).tocsr()

    model = implicit.als.AlternatingLeastSquares(
        factors=64, iterations=15, regularization=0.01, use_gpu=False
    )
    model.fit(matrix * 40.0)

    np.savez(MODEL_PATH,
             user_factors=model.user_factors,
             item_factors=model.item_factors,
             user_ids=np.array(user_ids),
             article_ids=np.array(article_ids))

    result = {
        "users_trained": len(user_ids),
        "items_trained": len(article_ids),
        "duration_seconds": round(time.time() - t0, 2),
        "model_path": str(MODEL_PATH),
    }
    logger.info("ALS complete: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run())
