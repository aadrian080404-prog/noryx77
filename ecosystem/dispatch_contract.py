"""Fail-closed cross-front dispatch contract."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Final
from .boundaries import Front, IntentEnvelope
from .isolation import require_dispatch
MAX_ID_BYTES: Final[int] = 256
MAX_REASON_BYTES: Final[int] = 512
def _id(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > MAX_ID_BYTES:
        raise ValueError(f"invalid_{name}")
    return value
@dataclass(frozen=True)
class DispatchReceipt:
    intent_id: str
    source: Front
    target: Front
    execution_id: str
    accepted: bool
    reason: str
    evidence_digest: str
    def __post_init__(self) -> None:
        _id(self.intent_id, "intent_id"); _id(self.execution_id, "execution_id")
        if not isinstance(self.source, Front) or not isinstance(self.target, Front):
            raise ValueError("front_required")
        require_dispatch(self.source, self.target)
        if not isinstance(self.accepted, bool):
            raise TypeError("accepted_bool_required")
        if not isinstance(self.reason, str) or len(self.reason.encode("utf-8")) > MAX_REASON_BYTES:
            raise ValueError("invalid_reason")
        if not isinstance(self.evidence_digest, str) or len(self.evidence_digest) != 64 or any(c not in "0123456789abcdef" for c in self.evidence_digest):
            raise ValueError("invalid_evidence_digest")
def make_receipt(intent: IntentEnvelope, *, source: Front, target: Front, execution_id: str, accepted: bool, reason: str, evidence: bytes) -> DispatchReceipt:
    if not isinstance(intent, IntentEnvelope):
        raise TypeError("intent_required")
    if source is not intent.front:
        raise PermissionError("intent_source_mismatch")
    if not isinstance(evidence, bytes):
        raise TypeError("evidence_bytes_required")
    return DispatchReceipt(intent.intent_id, source, target, _id(execution_id, "execution_id"), accepted, reason, sha256(evidence).hexdigest())
