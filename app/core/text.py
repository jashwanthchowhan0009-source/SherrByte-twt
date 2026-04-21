"""Text normalization, content hashing, and simhash.

- `normalize_body` collapses whitespace and strips boilerplate so two crawls of
  the same article produce the same content_hash.
- `content_hash` is SHA-256 over normalized text → kills exact republications.
- `simhash64` produces a 64-bit Charikar simhash over word shingles → near-dup
  detection via Hamming distance (threshold ≤ 3 for our scale).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter

# Common RSS tail boilerplate we'd rather not hash on
_BOILERPLATE_PATTERNS = [
    re.compile(r"read more at.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"also read:.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"click here to.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"copyright\s*©.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"all rights reserved.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"follow us on.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"first published:.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"for the latest.*breaking news.*$", re.IGNORECASE | re.MULTILINE),
]


def normalize_body(text: str) -> str:
    """Canonical form for hashing and comparison. Lossy by design."""
    if not text:
        return ""
    # NFKC normalization unifies compatibility characters (smart quotes, etc.)
    text = unicodedata.normalize("NFKC", text)
    for pat in _BOILERPLATE_PATTERNS:
        text = pat.sub("", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def content_hash(text: str) -> str:
    """SHA-256 hex digest of normalized text."""
    return hashlib.sha256(normalize_body(text).encode("utf-8")).hexdigest()


# -------- Simhash (Charikar) --------

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _shingles(text: str, k: int = 3) -> list[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    if len(tokens) < k:
        return [" ".join(tokens)] if tokens else []
    return [" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)]


def _stable_hash64(token: str) -> int:
    """Deterministic 64-bit hash (first 8 bytes of md5)."""
    return int.from_bytes(hashlib.md5(token.encode("utf-8")).digest()[:8], "big")


def simhash64(text: str, k: int = 3) -> int:
    """Charikar-style 64-bit simhash of k-word shingles.

    Stored in a BigInteger column; two articles are near-duplicates when the
    Hamming distance of their simhashes is small (≤3 is a common threshold).
    """
    shingles = _shingles(normalize_body(text), k=k)
    if not shingles:
        return 0
    counts = Counter(shingles)
    vec = [0] * 64
    for shingle, weight in counts.items():
        h = _stable_hash64(shingle)
        for i in range(64):
            bit = (h >> i) & 1
            vec[i] += weight if bit else -weight
    out = 0
    for i, v in enumerate(vec):
        if v > 0:
            out |= 1 << i
    return out


def hamming_distance(a: int, b: int) -> int:
    """Bit count of a XOR b, across 64 bits."""
    return ((a ^ b) & ((1 << 64) - 1)).bit_count()
