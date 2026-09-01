"""Additional fail-closed cryptographic policy checks for NORYX7."""

from __future__ import annotations

import math
from typing import Any

from .crypto import CryptoEnvelope, CryptoIntegrity


class CryptoPolicy:
    """Validates cryptographic metadata before an envelope is trusted."""

    MAX_PAYLOAD_BYTES = 1_000_000

    def __init__(self, crypto: CryptoIntegrity):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto_integrity")
        self.crypto = crypto

    def canonical(self, payload: Any) -> bytes:
        """Reject ambiguous values instead of stringifying arbitrary Python objects."""
        if isinstance(payload, float) and not math.isfinite(payload):
            raise TypeError("non_finite_crypto_value")
        body = self.crypto.canonical(payload)
        if len(body) > self.MAX_PAYLOAD_BYTES:
            raise ValueError("crypto_payload_too_large")
        return body

    def verify_envelope(self, envelope: CryptoEnvelope, *, consume: bool = True) -> bool:
        if not isinstance(envelope, CryptoEnvelope):
            return False
        if envelope.algorithm != self.crypto.ALGORITHM or envelope.version != self.crypto.VERSION:
            return False
        if len(envelope.payload) > self.MAX_PAYLOAD_BYTES:
            return False
        return self.crypto.verify(envelope, consume=consume)
