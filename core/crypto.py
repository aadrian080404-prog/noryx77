"""Standard-library cryptographic integrity primitives for NORYX7."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class CryptoEnvelope:
    domain: str
    nonce: str
    counter: int
    payload: bytes
    tag: str
    algorithm: str = "HMAC-SHA256"
    version: int = 1


class CryptoIntegrity:
    """Domain-separated HMAC-SHA-256 integrity with explicit anti-replay state."""

    _PREFIX = b"NORYX7:CRYPTO:v1:"
    ALGORITHM = "HMAC-SHA256"
    VERSION = 1
    MAX_DOMAIN_LENGTH = 128
    MAX_NONCE_LENGTH = 256

    def __init__(self, key: bytes | None = None):
        key = secrets.token_bytes(32) if key is None else key
        if not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("crypto key must contain at least 32 bytes")
        self._master = bytes(key)
        self._highest: dict[str, int] = {}
        self._nonces: dict[str, set[str]] = {}
        self._state_lock = Lock()

    @staticmethod
    def canonical(value: Any) -> bytes:
        try:
            return json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeError) as exc:
            raise TypeError("non_canonical_crypto_payload") from exc

    def _validate_domain(self, domain: str) -> None:
        if not isinstance(domain, str) or not domain.strip() or len(domain) > self.MAX_DOMAIN_LENGTH:
            raise ValueError("invalid_crypto_domain")

    def _domain_key(self, domain: str) -> bytes:
        self._validate_domain(domain)
        return hmac.new(self._master, self._PREFIX + domain.encode("utf-8"), hashlib.sha256).digest()

    def _message(self, domain: str, nonce: str, counter: int, payload: bytes) -> bytes:
        return (
            self.VERSION.to_bytes(2, "big")
            + self.ALGORITHM.encode("ascii")
            + b"\x00"
            + domain.encode("utf-8")
            + b"\x00"
            + counter.to_bytes(8, "big")
            + b"\x00"
            + nonce.encode("utf-8")
            + b"\x00"
            + payload
        )

    def sign(self, domain: str, payload: Any, counter: int, nonce: str | None = None) -> CryptoEnvelope:
        self._validate_domain(domain)
        if isinstance(counter, bool) or not isinstance(counter, int) or counter < 0 or counter >= 2**64:
            raise ValueError("invalid_crypto_counter")
        nonce = secrets.token_hex(16) if nonce is None else nonce
        if not isinstance(nonce, str) or not nonce.strip() or len(nonce) > self.MAX_NONCE_LENGTH:
            raise ValueError("invalid_crypto_nonce")
        body = self.canonical(payload)
        tag = hmac.new(self._domain_key(domain), self._message(domain, nonce, counter, body), hashlib.sha256).hexdigest()
        return CryptoEnvelope(domain, nonce, counter, body, tag, self.ALGORITHM, self.VERSION)

    def verify(self, envelope: CryptoEnvelope, *, consume: bool = True) -> bool:
        if not isinstance(envelope, CryptoEnvelope):
            return False
        if envelope.algorithm != self.ALGORITHM or envelope.version != self.VERSION:
            return False
        try:
            self._validate_domain(envelope.domain)
        except Exception:
            return False
        if not isinstance(envelope.nonce, str) or not envelope.nonce.strip() or len(envelope.nonce) > self.MAX_NONCE_LENGTH:
            return False
        if isinstance(envelope.counter, bool) or not isinstance(envelope.counter, int) or envelope.counter < 0 or envelope.counter >= 2**64:
            return False
        if not isinstance(envelope.payload, bytes) or not isinstance(envelope.tag, str) or len(envelope.tag) != 64:
            return False
        try:
            expected = hmac.new(self._domain_key(envelope.domain), self._message(envelope.domain, envelope.nonce, envelope.counter, envelope.payload), hashlib.sha256).hexdigest()
        except Exception:
            return False
        if not hmac.compare_digest(expected, envelope.tag):
            return False
        if not consume:
            return True
        with self._state_lock:
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
