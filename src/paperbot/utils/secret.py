"""Symmetric encryption helpers for secrets at rest.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the ``cryptography`` library.
The encryption key is read from the ``PAPERBOT_SECRET_KEY`` environment
variable.  When the variable is absent a deterministic fallback key is
derived so that the application still starts (with a logged warning).
"""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional

from loguru import logger

_ENV_KEY = "PAPERBOT_SECRET_KEY"

# Lazy-initialised Fernet instance.
_fernet: Optional["Fernet"] = None  # type: ignore[name-defined]


def _get_fernet() -> "Fernet":
    global _fernet
    if _fernet is not None:
        return _fernet

    from cryptography.fernet import Fernet

    raw = os.getenv(_ENV_KEY, "").strip()
    if raw:
        # Accept either a raw 32-byte-urlsafe-b64 Fernet key or an
        # arbitrary passphrase that we hash into one.
        try:
            Fernet(raw.encode())
            key = raw.encode()
        except Exception:
            key = base64.urlsafe_b64encode(
                hashlib.sha256(raw.encode()).digest()
            )
    else:
        logger.warning(
            f"{_ENV_KEY} is not set — using deterministic fallback key. "
            "Set this variable in production to secure API keys at rest."
        )
        key = base64.urlsafe_b64encode(
            hashlib.sha256(b"paperbot-default-insecure-key").digest()
        )

    _fernet = Fernet(key)
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt *plaintext* and return a Fernet token string."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a Fernet *token* back to plaintext.

    If *token* is not a valid Fernet token (e.g. a legacy plaintext value)
    it is returned as-is so that existing unencrypted data keeps working.
    """
    if not token:
        return ""
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except Exception:
        # Graceful migration: treat non-Fernet values as plaintext.
        return token
