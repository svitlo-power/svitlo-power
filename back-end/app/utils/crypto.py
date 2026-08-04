import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


class SecretCipher:
    """Symmetric encryption for credentials at rest, keyed by the application SECRET_KEY."""

    def __init__(self, secret_key: str):
        digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str) -> str:
        return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")


__all__ = [SecretCipher, InvalidToken]
