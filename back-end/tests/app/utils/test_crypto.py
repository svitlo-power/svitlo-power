"""Tests for app/utils/crypto.py."""
import base64
import hashlib

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.utils.crypto import SecretCipher


class TestSecretCipherInit:
    def test_init_creates_fernet_from_secret_key(self):
        cipher = SecretCipher("my-secret-key")
        assert cipher._fernet is not None

    def test_init_uses_sha256_of_secret_key(self):
        secret_key = "my-secret-key"
        cipher = SecretCipher(secret_key)
        expected_digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
        expected_key = base64.urlsafe_b64encode(expected_digest)
        expected_fernet = Fernet(expected_key)
        # Verify the key matches by encrypting with both and comparing
        test_value = "test"
        encrypted = cipher.encrypt(test_value)
        assert expected_fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8") == test_value

    def test_different_secret_keys_produce_different_ciphers(self):
        cipher1 = SecretCipher("key1")
        cipher2 = SecretCipher("key2")
        encrypted = cipher1.encrypt("test")
        with pytest.raises(InvalidToken):
            cipher2.decrypt(encrypted)


class TestSecretCipherEncrypt:
    def test_encrypt_returns_string(self):
        cipher = SecretCipher("test-key")
        result = cipher.encrypt("hello")
        assert isinstance(result, str)

    def test_encrypt_produces_different_ciphertexts(self):
        cipher = SecretCipher("test-key")
        encrypted1 = cipher.encrypt("hello")
        encrypted2 = cipher.encrypt("hello")
        assert encrypted1 != encrypted2

    def test_encrypt_empty_string(self):
        cipher = SecretCipher("test-key")
        result = cipher.encrypt("")
        assert isinstance(result, str)
        assert cipher.decrypt(result) == ""


class TestSecretCipherDecrypt:
    def test_decrypt_returns_original_value(self):
        cipher = SecretCipher("test-key")
        encrypted = cipher.encrypt("hello world")
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == "hello world"

    def test_decrypt_roundtrip_special_chars(self):
        cipher = SecretCipher("test-key")
        original = "hello!@#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = cipher.encrypt(original)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == original

    def test_decrypt_invalid_token_raises(self):
        cipher = SecretCipher("test-key")
        with pytest.raises(InvalidToken):
            cipher.decrypt("invalid-token")

    def test_decrypt_with_wrong_key_raises(self):
        cipher1 = SecretCipher("key1")
        cipher2 = SecretCipher("key2")
        encrypted = cipher1.encrypt("secret")
        with pytest.raises(InvalidToken):
            cipher2.decrypt(encrypted)


class TestSecretCipherRoundTrip:
    def test_roundtrip_various_values(self):
        cipher = SecretCipher("test-key")
        values = ["a", "hello", "12345", "complex!@#value", ""]
        for value in values:
            encrypted = cipher.encrypt(value)
            decrypted = cipher.decrypt(encrypted)
            assert decrypted == value
