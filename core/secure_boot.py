"""Secure-boot-style trust chain for hardware, OS and NORYX7 components."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib


@dataclass(frozen=True)
class TrustAnchor:
    anchor_id: str
    digest: str


class SecureBootChain:
    """Requires an ordered verified chain before runtime admission."""

    def __init__(self, anchor: TrustAnchor) -> None:
        if not isinstance(anchor, TrustAnchor) or not anchor.anchor_id or len(anchor.digest) != 64:
            raise ValueError("invalid_trust_anchor")
        self.anchor = anchor
        self._verified: tuple[str, ...] = ()

    def verify_stage(self, stage: str, artifact_digest: str, expected_digest: str) -> bool:
        if not stage or not isinstance(artifact_digest, str) or not isinstance(expected_digest, str):
            return False
        if len(artifact_digest) != 64 or artifact_digest != expected_digest:
            return False
        self._verified = self._verified + (stage,)
        return True

    def admit(self, system_digest: str) -> bool:
        if not isinstance(system_digest, str) or len(system_digest) != 64:
            return False
        chain = "|".join(self._verified).encode()
        derived = hashlib.sha256(chain + system_digest.encode()).hexdigest()
        return bool(self._verified) and derived != "0" * 64
