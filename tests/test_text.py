"""Phase C text utility tests.

Covers the dedup primitives: normalization, content hashing, simhash distance.
No DB needed — these are pure functions.
"""

from __future__ import annotations

from app.core.text import (
    content_hash,
    hamming_distance,
    normalize_body,
    simhash64,
)


# ---------------- normalize_body ----------------


def test_normalize_collapses_whitespace() -> None:
    assert normalize_body("hello   world\n\n\n  foo") == "hello world foo"


def test_normalize_strips_boilerplate() -> None:
    text = "Actual content here. Also Read: irrelevant stuff"
    assert "also read" not in normalize_body(text)


def test_normalize_strips_copyright_and_follow() -> None:
    text = "News body. Copyright © 2026 NDTV. All rights reserved."
    out = normalize_body(text)
    assert "copyright" not in out
    assert "news body" in out


def test_normalize_handles_empty() -> None:
    assert normalize_body("") == ""
    assert normalize_body(None) == ""  # type: ignore[arg-type]


def test_normalize_is_case_insensitive() -> None:
    assert normalize_body("Hello World") == normalize_body("hello world")


# ---------------- content_hash ----------------


def test_content_hash_is_deterministic() -> None:
    a = "The Nifty closed at a record high today."
    assert content_hash(a) == content_hash(a)


def test_content_hash_ignores_formatting_differences() -> None:
    a = "The Nifty closed at 24,500 today."
    b = "  The   Nifty  closed  at  24,500  today.  "
    assert content_hash(a) == content_hash(b)


def test_content_hash_differs_for_different_content() -> None:
    a = content_hash("Nifty closed at 24,500 today.")
    b = content_hash("Sensex closed at 81,200 today.")
    assert a != b


def test_content_hash_is_64_char_hex() -> None:
    h = content_hash("test")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ---------------- simhash ----------------


def test_simhash_roundtrip_is_stable() -> None:
    text = "Reserve Bank of India keeps repo rate unchanged at 6.5 percent."
    assert simhash64(text) == simhash64(text)


def test_simhash_empty_is_zero() -> None:
    assert simhash64("") == 0


def test_simhash_fits_in_64_bits() -> None:
    h = simhash64("some reasonable length news article body text here")
    assert 0 <= h < (1 << 64)


def test_near_duplicates_have_low_hamming_distance() -> None:
    # Two slight rewrites of the same story should be close in simhash space
    a = (
        "Reserve Bank of India keeps the repo rate unchanged at 6.5 percent, "
        "citing inflation concerns and global headwinds."
    )
    b = (
        "The RBI kept the repo rate unchanged at 6.5 percent, "
        "citing inflation concerns and global uncertainty."
    )
    dist = hamming_distance(simhash64(a), simhash64(b))
    assert dist < 20, f"expected near-dup to have low distance, got {dist}"


def test_very_different_texts_have_high_hamming_distance() -> None:
    a = "The cricket match ended in a thrilling tie after the last over."
    b = "Scientists announced a major breakthrough in quantum computing today."
    dist = hamming_distance(simhash64(a), simhash64(b))
    assert dist > 15, f"expected dissimilar texts to have high distance, got {dist}"


def test_hamming_distance_self_is_zero() -> None:
    h = simhash64("anything")
    assert hamming_distance(h, h) == 0
