"""Security primitives: password hashing (argon2id), JWTs, refresh tokens.

Design:
- Passwords: argon2id via argon2-cffi (OWASP-recommended 2024+).
- Access tokens: short-lived (15m) JWT carrying {sub, exp, type}.
- Refresh tokens: opaque 32-byte urlsafe string. The raw token is sent to the
  client; only SHA-256(token) is stored in DB. Rotation on every refresh.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings
from app.core.errors import UnauthorizedError

# argon2id with defaults recommended by OWASP (2024): m=19456 (19MiB), t=2, p=1.
# argon2-cffi defaults are close enough; we pin them explicitly for clarity.
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


# ---------------- Passwords ----------------


def hash_password(plaintext: str) -> str:
    """Hash a password. Returns a self-describing argon2 string."""
    return _hasher.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    """Return True if plaintext matches the stored hash. Timing-safe."""
    try:
        _hasher.verify(hashed, plaintext)
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        # Malformed hash, bcrypt-from-legacy, etc. — treat as mismatch.
        return False


def password_needs_rehash(hashed: str) -> bool:
    """True if the hash uses outdated params — re-hash on next successful login."""
    try:
        return _hasher.check_needs_rehash(hashed)
    except Exception:
        return True


# ---------------- JWT access tokens ----------------

TokenType = Literal["access", "refresh"]


def _now() -> datetime:
    return datetime.now(UTC)


def create_access_token(user_id: uuid.UUID, extra_claims: dict[str, Any] | None = None) -> str:
    now = _now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_access_ttl_minutes)).timestamp()),
        "type": "access",
        "jti": secrets.token_urlsafe(12),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token. Raises UnauthorizedError on any failure."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise UnauthorizedError("Access token has expired.") from e
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError("Invalid access token.") from e

    if payload.get("type") != "access":
        raise UnauthorizedError("Wrong token type.")
    return payload


# ---------------- Refresh tokens (opaque) ----------------


def generate_refresh_token() -> tuple[str, str]:
    """Return (raw_token_for_client, sha256_hash_for_db). Only ever call once per session."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    """Deterministic SHA-256 of the refresh token. Cheap → fine for equality lookup."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return _now() + timedelta(days=settings.jwt_refresh_ttl_days)
