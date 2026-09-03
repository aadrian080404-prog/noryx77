"""Authenticated encryption and key lifecycle primitives for NORYX7.

This module deliberately uses the vetted ``cryptography`` package rather than
implementing cryptographic primitives in application code. Keys are supplied by
an external secret/KMS boundary; this module never persists or logs key bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
import secrets
from typing import Final

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


KEY_SIZE: Final[int] = 32
NONCE_SIZE: Final[int] = 12


@dataclass(frozen=True)
class EncryptedEnvelope:
    """Versioned AES-256-GCM ciphertext with authenticated metadata."""

    key_id: str
    nonce: bytes
    ciphertext: bytes
    aad: bytes = b""

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.key_id, str) and bool(self.key_id.strip())
            and isinstance(self.nonce, bytes) and len(self.nonce) == NONCE_SIZE
            and isinstance(self.ciphertext, bytes) and len(self.ciphertext) >= 16
            and isinstance(self.aad, bytes)
        )


class KeyProvider:
    """Minimal external key boundary; implementations must not expose key material."""

    def get_key(self, key_id: str) -> bytes:
        raise NotImplementedError


class InMemoryKeyProvider(KeyProvider):
    """Test-only key provider; production keys belong in a KMS/secret boundary."""

    def __init__(self, keys: dict[str, bytes] | None = None):
        self._keys: dict[str, bytes] = {}
        for key_id, key in (keys or {}).items():
            self.add(key_id, key)

    def add(self, key_id: str, key: bytes) -> None:
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("invalid_key_id")
        if not isinstance(key, bytes) or len(key) != KEY_SIZE:
            raise ValueError("aes256_key_required")
        if key_id in self._keys:
            raise ValueError("key_id_already_registered")
        self._keys[key_id] = bytes(key)

    def get_key(self, key_id: str) -> bytes:
        key = self._keys.get(key_id)
        if key is None:
            raise KeyError("unknown_key_id")
        return bytes(key)


class AuthenticatedCipher:
    """AES-256-GCM service with strict key, nonce and envelope validation."""

    def __init__(self, provider: KeyProvider):
        if not isinstance(provider, KeyProvider):
            raise ValueError("key_provider_required")
        self.provider = provider

    def encrypt(self, plaintext: bytes, *, key_id: str, aad: bytes = b"") -> EncryptedEnvelope:
        if not isinstance(plaintext, bytes):
            raise TypeError("plaintext_must_be_bytes")
        if not isinstance(aad, bytes):
            raise TypeError("aad_must_be_bytes")
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("invalid_key_id")
        key = self.provider.get_key(key_id)
        if not isinstance(key, bytes) or len(key) != KEY_SIZE:
            raise ValueError("aes256_key_required")
        nonce = secrets.token_bytes(NONCE_SIZE)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
        return EncryptedEnvelope(key_id, nonce, ciphertext, aad)

    def decrypt(self, envelope: EncryptedEnvelope) -> bytes:
        if not isinstance(envelope, EncryptedEnvelope) or not envelope.is_well_formed():
            raise ValueError("invalid_encrypted_envelope")
        key = self.provider.get_key(envelope.key_id)
        if not isinstance(key, bytes) or len(key) != KEY_SIZE:
            raise ValueError("aes256_key_required")
        try:
            return AESGCM(key).decrypt(envelope.nonce, envelope.ciphertext, envelope.aad)
        except InvalidTag as exc:
            raise ValueError("ciphertext_authentication_failed") from exc
