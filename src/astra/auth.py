from __future__ import annotations

import hashlib
import hmac
import secrets
from functools import lru_cache


PBKDF2_ITERATIONS = 600_000
# 3M2AYA (Aly, 2026-09-24): 8 characters minimum. Existing hashes are unaffected.
MIN_PASSWORD_LENGTH = 8


def normalize_email(value: str) -> str:
    email = value.strip().casefold()
    if not email or "@" not in email or any(ch.isspace() for ch in email):
        raise ValueError("Enter a valid email address.")
    return email


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must contain at least {MIN_PASSWORD_LENGTH} characters.")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


@lru_cache(maxsize=1)
def dummy_password_hash() -> str:
    """A fixed hash with the real PBKDF2 cost, computed once. Sign-in checks an unknown or
    inactive email against it so that answer takes as long as a wrong password (3M2AYA)."""
    return hash_password("no account has this password", salt=b"astra-dummy-salt")


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), expected_hex)
    except (TypeError, ValueError):
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
