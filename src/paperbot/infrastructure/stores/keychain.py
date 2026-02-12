"""Keychain-backed secret storage using the ``keyring`` library.

On macOS this stores API keys in the system Keychain.  On Linux it
delegates to SecretService / KWallet.  When ``keyring`` is not
installed or the backend is unavailable the caller should fall back
to the existing DB-level encryption.
"""

from __future__ import annotations

from loguru import logger

SERVICE_NAME = "paperbot"

_available: bool | None = None


def _is_available() -> bool:
    global _available
    if _available is not None:
        return _available
    try:
        import keyring  # noqa: F401

        _available = True
    except ImportError:
        logger.warning("keyring library not installed – falling back to DB encryption for API keys")
        _available = False
    return _available


class KeychainStore:
    @staticmethod
    def store_key(endpoint_name: str, api_key: str) -> bool:
        if not _is_available():
            return False
        import keyring

        try:
            keyring.set_password(SERVICE_NAME, endpoint_name, api_key)
            return True
        except Exception as exc:
            logger.warning(f"keychain store failed for {endpoint_name}: {exc}")
            return False

    @staticmethod
    def get_key(endpoint_name: str) -> str | None:
        if not _is_available():
            return None
        import keyring

        try:
            return keyring.get_password(SERVICE_NAME, endpoint_name)
        except Exception:
            return None

    @staticmethod
    def delete_key(endpoint_name: str) -> None:
        if not _is_available():
            return
        import keyring

        try:
            keyring.delete_password(SERVICE_NAME, endpoint_name)
        except Exception:
            pass
