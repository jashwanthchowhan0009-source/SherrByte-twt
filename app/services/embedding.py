"""Local embedding encoder.

Loads all-MiniLM-L6-v2 (384-dim, ~80MB) once per process. Model download happens
on first use — takes ~30 seconds. After that, ~10-20ms per sentence on CPU.

Why local, not an API? At 500 articles/day this is free; an API would cost
tokens-per-article × articles-per-day. Also avoids vendor lock-in for the
recommender's core signal.
"""

from __future__ import annotations

import asyncio
from threading import Lock
from typing import TYPE_CHECKING

import numpy as np

from app.core.logging import get_logger

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

log = get_logger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"
_model: "SentenceTransformer | None" = None
_model_lock = Lock()


def _load_model() -> "SentenceTransformer":
    """Lazy-load with a lock so concurrent callers don't each download."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer  # heavy import

            log.info("embed_model_loading", model=_MODEL_NAME)
            _model = SentenceTransformer(_MODEL_NAME, device="cpu")
            log.info("embed_model_ready", model=_MODEL_NAME, dim=_model.get_sentence_embedding_dimension())
    return _model


def _encode_sync(texts: list[str]) -> np.ndarray:
    """Blocking encode. Always returns L2-normalized vectors (cosine-ready)."""
    model = _load_model()
    arr = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.asarray(arr, dtype=np.float32)


async def encode(texts: list[str]) -> list[list[float]]:
    """Async wrapper — runs the CPU-bound encode in a thread."""
    if not texts:
        return []
    arr = await asyncio.to_thread(_encode_sync, texts)
    return arr.tolist()


async def encode_one(text: str) -> list[float]:
    out = await encode([text])
    return out[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """For pre-normalized vectors, dot product == cosine. Cheap."""
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    return float(np.dot(va, vb))


def model_name() -> str:
    return _MODEL_NAME
