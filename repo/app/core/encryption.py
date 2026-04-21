"""Field-level encryption helpers using AES-256-GCM."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import sqlalchemy.types as types

from app.core.config import settings


def _derive_key(key_seed: str) -> bytes:
    return hashlib.sha256(key_seed.encode("utf-8")).digest()


def encrypt_text(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None

    key = _derive_key(settings.field_encryption_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    encrypted = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    blob = nonce + encrypted
    return base64.b64encode(blob).decode("utf-8")


def decrypt_text(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None

    key = _derive_key(settings.field_encryption_key)
    aesgcm = AESGCM(key)
    blob = base64.b64decode(ciphertext.encode("utf-8"))
    nonce = blob[:12]
    encrypted = blob[12:]
    plaintext = aesgcm.decrypt(nonce, encrypted, None)
    return plaintext.decode("utf-8")


class EncryptedField(types.TypeDecorator):
    """Custom SQLAlchemy type for transparent field-level encryption."""
    impl = types.String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_text(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_text(value)
