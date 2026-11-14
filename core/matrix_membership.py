"""Policy-only node admission and revocation state machine.

Cryptographic attestation verification and durable consensus are injected by the
caller; this module does not pretend to implement either.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Callable


class MemberState(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass(frozen=True)
class AdmissionEvidence:
    node_id: str
    owner_id: str
    failure_domain: str
    software_measurement: str
    epoch: int
    nonce: str
    capabilities: frozenset[str]


@dataclass(frozen=True)
class MemberRecord:
    node_id: str
    owner_id: str
    failure_domain: str
    software_measurement: str
    epoch: int
    capabilities: frozenset[str]
    state: MemberState
    last_nonce: str


class MembershipRegistry:
    """In-memory reference state machine; persist/replicate before production use."""

    def __init__(self) -> None:
        self._records: dict[str, MemberRecord] = {}
        self._lock = RLock()

    def admit(
        self,
        evidence: AdmissionEvidence,
        proof: bytes,
        verify: Callable[[AdmissionEvidence, bytes], bool],
    ) -> MemberRecord:
        for value in (evidence.node_id, evidence.owner_id, evidence.failure_domain,
                      evidence.software_measurement, evidence.nonce):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("admission_fields_required")
        if isinstance(evidence.epoch, bool) or not isinstance(evidence.epoch, int) or evidence.epoch < 1:
            raise ValueError("invalid_membership_epoch")
        if not isinstance(proof, bytes) or not proof:
            raise ValueError("attestation_proof_required")
        if any(not isinstance(x, str) or not x.strip() for x in evidence.capabilities):
            raise ValueError("invalid_capability")
        with self._lock:
            previous = self._records.get(evidence.node_id)
            if previous and evidence.nonce == previous.last_nonce:
                raise PermissionError("admission_nonce_replayed")
            if previous and evidence.epoch <= previous.epoch:
                raise PermissionError("membership_epoch_not_monotonic")
            if not verify(evidence, proof):
                raise PermissionError("attestation_verification_failed")
            record = MemberRecord(
                evidence.node_id, evidence.owner_id, evidence.failure_domain,
                evidence.software_measurement, evidence.epoch,
                frozenset(evidence.capabilities), MemberState.ACTIVE, evidence.nonce,
            )
            self._records[evidence.node_id] = record
            return record

    def revoke(self, node_id: str, next_epoch: int) -> MemberRecord:
        with self._lock:
            current = self._records.get(node_id)
            if current is None:
                raise KeyError("unknown_member")
            if isinstance(next_epoch, bool) or not isinstance(next_epoch, int) or next_epoch <= current.epoch:
                raise ValueError("revocation_epoch_must_increase")
            record = MemberRecord(
                current.node_id, current.owner_id, current.failure_domain,
                current.software_measurement, next_epoch, frozenset(), MemberState.REVOKED,
                current.last_nonce,
            )
            self._records[node_id] = record
            return record

    def get(self, node_id: str) -> MemberRecord | None:
        with self._lock:
            return self._records.get(node_id)
