"""Explicit boundaries between the four NORYX fronts."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Final
MAX_INTENT_SIZE: Final[int] = 4096
MAX_ID_SIZE: Final[int] = 256
MAX_PAYLOAD_SIZE: Final[int] = 4 * 1024 * 1024
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
    principal_id: str
    def __post_init__(self) -> None:
        if not isinstance(self.intent_id, str) or not self.intent_id.strip() or len(self.intent_id.encode("utf-8")) > MAX_ID_SIZE:
            raise ValueError("intent_id_invalid")
        if not isinstance(self.front, Front):
            raise ValueError("front_required")
        if not isinstance(self.operation, str) or not self.operation.strip():
            raise ValueError("operation_required")
        if len(self.operation.encode("utf-8")) > MAX_INTENT_SIZE:
            raise ValueError("operation_size_exceeded")
        if not isinstance(self.payload_digest, str) or len(self.payload_digest) != 64 or any(c not in "0123456789abcdef" for c in self.payload_digest):
            raise ValueError("payload_digest_invalid")
        if not isinstance(self.principal_id, str) or not self.principal_id.strip() or len(self.principal_id.encode("utf-8")) > MAX_ID_SIZE:
            raise ValueError("principal_id_invalid")
def make_intent(front: Front, operation: str, payload: bytes, *, principal_id: str) -> IntentEnvelope:
    if not isinstance(front, Front): raise ValueError("front_required")
    if not isinstance(operation, str) or not operation.strip(): raise ValueError("operation_required")
    if not isinstance(payload, bytes): raise TypeError("payload_bytes_required")
    if len(operation.encode("utf-8")) > MAX_INTENT_SIZE: raise ValueError("operation_size_exceeded")
    if len(payload) > MAX_PAYLOAD_SIZE: raise ValueError("payload_size_exceeded")
    if not isinstance(principal_id, str) or not principal_id.strip() or len(principal_id.encode("utf-8")) > MAX_ID_SIZE:
        raise ValueError("principal_id_invalid")
    digest = sha256(payload).hexdigest()
    intent_id = sha256(f"{front.value}|{operation}|{principal_id}|{digest}".encode("utf-8")).hexdigest()
    return IntentEnvelope(intent_id, front, operation, digest, principal_id)
