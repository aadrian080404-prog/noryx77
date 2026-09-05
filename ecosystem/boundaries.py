"""Explicit boundaries between the four NORYX fronts.

The boundary layer contains no model, browser, OS, or provider implementation.
It prevents accidental coupling by representing only the permitted direction
of orchestration: interaction -> intent -> front dispatch -> verified result.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Final

MAX_INTENT_SIZE: Final[int] = 4096


class Front(str, Enum):
    JARVIS = "jarvis"
    BROWSER = "browser"
    HYPERSYNTH = "hypersynth"
    ORCHESTRATION = "orchestration"


@dataclass(frozen=True)
class IntentEnvelope:
    intent_id: str
    front: Front
    operation: str
    payload_digest: str

    def __post_init__(self) -> None:
        if not self.intent_id or not isinstance(self.intent_id, str):
            raise ValueError("intent_id_required")
        if not isinstance(self.front, Front):
            raise ValueError("front_required")
        if not isinstance(self.operation, str) or not self.operation.strip():
            raise ValueError("operation_required")
        if len(self.operation.encode("utf-8")) > MAX_INTENT_SIZE:
            raise ValueError("operation_size_exceeded")
        if not isinstance(self.payload_digest, str) or len(self.payload_digest) != 64:
            raise ValueError("payload_digest_required")
        if any(c not in "0123456789abcdef" for c in self.payload_digest):
            raise ValueError("payload_digest_invalid")


def make_intent(front: Front, operation: str, payload: bytes) -> IntentEnvelope:
    """Create a deterministic digest envelope; payload bytes are not retained."""
    if not isinstance(front, Front):
        raise ValueError("front_required")
    if not isinstance(operation, str) or not operation.strip():
        raise ValueError("operation_required")
    if not isinstance(payload, bytes):
        raise TypeError("payload_bytes_required")
    if len(operation.encode("utf-8")) > MAX_INTENT_SIZE:
        raise ValueError("operation_size_exceeded")
    digest = sha256(payload).hexdigest()
    intent_id = sha256(f"{front.value}|{operation}|{digest}".encode("utf-8")).hexdigest()
    return IntentEnvelope(intent_id, front, operation, digest)
