"""Phase B security primitive tests.

These run without a DB. They verify the password and JWT logic in isolation.
Full end-to-end auth flow tests will come when we have a test DB fixture.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import settings
from app.core.errors import UnauthorizedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)


# ---------------- Passwords ----------------


def test_password_hash_and_verify_roundtrip() -> None:
    plaintext = "correct horse battery staple"
    hashed = hash_password(plaintext)
    assert hashed != plaintext
    assert hashed.startswith("$argon2")
    assert verify_password(plaintext, hashed)


def test_password_verify_rejects_wrong_password() -> None:
    hashed = hash_password("secret123")
    assert not verify_password("wrong", hashed)


def test_password_verify_rejects_malformed_hash() -> None:
    # Garbage hash shouldn't crash — just return False
    assert not verify_password("anything", "not-a-real-hash")
    assert not verify_password("anything", "")


def test_two_hashes_of_same_password_differ() -> None:
    # argon2 uses a random salt → different ciphertexts
    a = hash_password("same")
    b = hash_password("same")
    assert a != b
    assert verify_password("same", a)
    assert verify_password("same", b)


# ---------------- JWT ----------------


def test_access_token_roundtrip() -> None:
    uid = uuid.uuid4()
    token = create_access_token(uid, extra_claims={"role": "user"})
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid)
    assert payload["type"] == "access"
    assert payload["role"] == "user"
    assert "exp" in payload


def test_access_token_expired_is_rejected() -> None:
    # Manually craft an already-expired token
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
            "type": "access",
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(UnauthorizedError, match="expired"):
        decode_access_token(expired)


def test_access_token_wrong_signature_is_rejected() -> None:
    bad = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600,
            "type": "access",
        },
        "wrong-secret",
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(UnauthorizedError):
        decode_access_token(bad)


def test_access_token_wrong_type_is_rejected() -> None:
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600,
            "type": "refresh",  # wrong
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(UnauthorizedError, match="Wrong token type"):
        decode_access_token(token)


def test_access_token_garbage_is_rejected() -> None:
    with pytest.raises(UnauthorizedError):
        decode_access_token("not.a.jwt")


# ---------------- Refresh tokens ----------------


def test_generate_refresh_token_returns_raw_and_hash() -> None:
    raw, hashed = generate_refresh_token()
    assert len(raw) > 20
    assert len(hashed) == 64  # sha256 hex
    assert hash_refresh_token(raw) == hashed


def test_two_refresh_tokens_differ() -> None:
    r1, h1 = generate_refresh_token()
    r2, h2 = generate_refresh_token()
    assert r1 != r2
    assert h1 != h2


def test_refresh_expiry_is_in_the_future() -> None:
    exp = refresh_token_expiry()
    assert exp > datetime.now(UTC)
    assert exp < datetime.now(UTC) + timedelta(days=settings.jwt_refresh_ttl_days + 1)
