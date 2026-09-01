"""Small standard-library cryptographic primitives used by NORYX7 integrity gates."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CryptoEnvelope:
    domain: str
    nonce: str
    counter: int
    payload: bytes
    tag: str


class CryptoIntegrity:
    """Domain-separated HMAC-SHA-256 integrity with explicit anti-replay state."""

    _PREFIX = b"NORYX7:CRYPTO:v1:"

    def __init__(self, key: bytes | None = None):
        key = secrets.token_bytes(32) if key is None else key
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("crypto key must contain at least 32 bytes")
        self._master = bytes(key)
        self._highest: dict[str, int] = {}
        self._nonces: dict[str, set[str]] = {}

    @staticmethod
    def canonical(value: Any) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")

    def _domain_key(self, domain: str) -> bytes:
        if not isinstance(domain, str) or not domain.strip():
            raise ValueError("invalid_crypto_domain")
        return hmac.new(self._master, self._PREFIX + domain.encode("utf-8"), hashlib.sha256).digest()

    def sign(self, domain: str, payload: Any, counter: int, nonce: str | None = None) -> CryptoEnvelope:
        if isinstance(counter, bool) or not isinstance(counter, int) or counter < 0:
            raise ValueError("invalid_crypto_counter")
        nonce = secrets.token_hex(16) if nonce is None else nonce
        if not isinstance(nonce, str) or not nonce.strip():
            raise ValueError("invalid_crypto_nonce")
        body = self.canonical(payload)
        tag = hmac.new(
            self._domain_key(domain),
            domain.encode("utf-8") + b"\x00" + counter.to_bytes(8, "big") + b"\x00" + nonce.encode("utf-8") + b"\x00" + body,
            hashlib.sha256,
        ).hexdigest()
        return CryptoEnvelope(domain, nonce, counter, body, tag)

    def verify(self, envelope: CryptoEnvelope, *, consume: bool = True) -> bool:
        if not isinstance(envelope, CryptoEnvelope):
            return False
        if not isinstance(envelope.domain, str) or not envelope.domain.strip():
            return False
        if not isinstance(envelope.nonce, str) or not envelope.nonce.strip():
            return False
        if isinstance(envelope.counter, bool) or not isinstance(envelope.counter, int) or envelope.counter < 0:
            return False
        if not isinstance(envelope.payload, bytes) or not isinstance(envelope.tag, str) or len(envelope.tag) != 64:
            return False
        expected = hmac.new(
            self._domain_key(envelope.domain),
            envelope.domain.encode("utf-8") + b"\x00" + envelope.counter.to_bytes(8, "big") + b"\x00" + envelope.nonce.encode("utf-8") + b"\x00" + envelope.payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, envelope.tag):
            return False
        if not consume:
            return True
        seen = self._nonces.setdefault(envelope.domain, set())
        highest = self._highest.get(envelope.domain, -1)
        if envelope.nonce in seen or envelope.counter <= highest:
            return False
        seen.add(envelope.nonce)
        self._highest[envelope.domain] = envelope.counter
        return True

    def digest(self, domain: str, payload: Any) -> str:
        return hmac.new(self._domain_key(domain), self.canonical(payload), hashlib.sha256).hexdigest()

    def verify_digest(self, domain: str, payload: Any, digest: str) -> bool:
        if not isinstance(digest, str) or len(digest) != 64:
            return False
        try:
            expected = self.digest(domain, payload)
        except Exception:
            return False
        return hmac.compare_digest(expected, digest)
