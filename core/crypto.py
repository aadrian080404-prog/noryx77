"""Authenticated encryption and key lifecycle primitives for NORYX7."""

from __future__ import annotations

from dataclasses import dataclass
import secrets
from typing import Final

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


KEY_SIZE: Final[int] = 32
NONCE_SIZE: Final[int] = 12
TAG_SIZE: Final[int] = 16
MAX_PLAINTEXT_SIZE: Final[int] = 64 * 1024 * 1024
CRYPTO_VERSION: Final[int] = 1
ALGORITHM: Final[str] = "AES-256-GCM"


def derive_subkey(root_key: bytes, *, salt: bytes, context: bytes) -> bytes:
    """Derive a domain-separated AES-256 key using the vetted HKDF primitive."""
    if not isinstance(root_key, bytes) or len(root_key) != KEY_SIZE:
        raise ValueError("root_key_required")
    if not isinstance(salt, bytes) or not salt:
        raise ValueError("hkdf_salt_required")
    if not isinstance(context, bytes) or not context:
        raise ValueError("hkdf_context_required")
    return HKDF(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        info=b"noryx7/v1/" + context,
    ).derive(root_key)


@dataclass(frozen=True)
class EncryptedEnvelope:
    """AES-256-GCM ciphertext with authenticated version and key identity."""

    key_id: str
    nonce: bytes
    ciphertext: bytes
    aad: bytes = b""
    version: int = CRYPTO_VERSION
    algorithm: str = ALGORITHM

    def is_well_formed(self) -> bool:
        return (
            isinstance(self.key_id, str) and bool(self.key_id.strip())
            and isinstance(self.nonce, bytes) and len(self.nonce) == NONCE_SIZE
            and isinstance(self.ciphertext, bytes)
            and TAG_SIZE <= len(self.ciphertext) <= MAX_PLAINTEXT_SIZE + TAG_SIZE
            and isinstance(self.aad, bytes)
            and self.version == CRYPTO_VERSION
            and self.algorithm == ALGORITHM
        )


class KeyProvider:
    """External key boundary; implementations must not expose key material."""

    def get_key(self, key_id: str) -> bytes:
        raise NotImplementedError


class InMemoryKeyProvider(KeyProvider):
    """Test-only provider; production keys belong in a KMS/secret boundary."""

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
    """AES-256-GCM with key-id binding, authenticated metadata and size limits."""

    _AAD_PREFIX: Final[bytes] = b"noryx7/aes-256-gcm/v1/"

    def __init__(self, provider: KeyProvider):
        if not isinstance(provider, KeyProvider):
            raise ValueError("key_provider_required")
        self.provider = provider

    @classmethod
    def _effective_aad(cls, key_id: str, aad: bytes) -> bytes:
        return cls._AAD_PREFIX + key_id.encode("utf-8") + b"\x00" + aad

    def encrypt(self, plaintext: bytes, *, key_id: str, aad: bytes = b"") -> EncryptedEnvelope:
        if not isinstance(plaintext, bytes):
            raise TypeError("plaintext_must_be_bytes")
        if len(plaintext) > MAX_PLAINTEXT_SIZE:
            raise ValueError("plaintext_size_exceeded")
        if not isinstance(aad, bytes):
            raise TypeError("aad_must_be_bytes")
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("invalid_key_id")
        key = self.provider.get_key(key_id)
        if not isinstance(key, bytes) or len(key) != KEY_SIZE:
            raise ValueError("aes256_key_required")
        nonce = secrets.token_bytes(NONCE_SIZE)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, self._effective_aad(key_id, aad))
        return EncryptedEnvelope(key_id, nonce, ciphertext, aad)

    def decrypt(self, envelope: EncryptedEnvelope) -> bytes:
        if not isinstance(envelope, EncryptedEnvelope) or not envelope.is_well_formed():
            raise ValueError("invalid_encrypted_envelope")
        key = self.provider.get_key(envelope.key_id)
        if not isinstance(key, bytes) or len(key) != KEY_SIZE:
            raise ValueError("aes256_key_required")
        try:
            return AESGCM(key).decrypt(
                envelope.nonce,
                envelope.ciphertext,
                self._effective_aad(envelope.key_id, envelope.aad),
            )
        except InvalidTag as exc:
            raise ValueError("ciphertext_authentication_failed") from exc


class LifecycleBoundKeyProvider(KeyProvider):
    """Gate external KMS/HSM key retrieval on durable lifecycle metadata.

    The lifecycle record is checked before and after the external key fetch.
    A rotation/revocation observed during retrieval rejects the result. A key
    returned before a later revocation is an in-flight operation; callers must
    bound its lifetime and discard it after the protected operation.
    """

    def __init__(self, lifecycle, external_provider) -> None:
        if not callable(getattr(lifecycle, "require_active", None)):
            raise TypeError("key_lifecycle_contract_required")
        if not callable(getattr(external_provider, "get_key", None)):
            raise TypeError("external_key_boundary_required")
        self._lifecycle = lifecycle
        self._external = external_provider

    def get_key(self, key_id: str) -> bytes:
        record = self._lifecycle.require_active(key_id)
        key = self._external.get_key(key_id, record.version)
        if not isinstance(key, bytes) or len(key) != KEY_SIZE:
            raise ValueError("aes256_key_required")
        current = self._lifecycle.require_active(key_id)
        if current != record:
            raise PermissionError("key_lifecycle_changed_during_key_fetch")
        return bytes(key)
