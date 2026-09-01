"""Cryptographic continuity records for internal HYPERSYNTH stage evidence.

This module binds each stage to the authenticated state immediately before it,
the authenticated output produced by that stage, and the exact predecessor
record. It establishes integrity/ordering; it does not establish semantic truth.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Any

from .attestation import StageAttestation
from .crypto import CryptoIntegrity


@dataclass(frozen=True)
class KernelContinuityRecord:
    task_id: str
    stage: str
    sequence: int
    state_digest: str
    input_digest: str
    output_digest: str
    dependency_tag: str
    previous_tag: str
    tag: str


class KernelContinuity:
    """Fail-closed authenticated state/transition continuity for one kernel run."""

    MAX_STAGE_LENGTH = 64
    MAX_TASK_LENGTH = 256
    MAX_SEQUENCE = 2**64 - 1

    def __init__(self, crypto: CryptoIntegrity, *, session_id: str, task_id: str,
                 risk_class: str, verification_requirements: tuple[str, ...]):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto_integrity")
        if not isinstance(session_id, str) or not session_id.strip() or len(session_id) > 64:
            raise ValueError("invalid_session_id")
        if not isinstance(task_id, str) or not task_id.strip() or len(task_id) > self.MAX_TASK_LENGTH:
            raise ValueError("invalid_continuity_task_id")
        if not isinstance(risk_class, str) or not risk_class.strip():
            raise ValueError("invalid_continuity_risk_class")
        if not isinstance(verification_requirements, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in verification_requirements
        ):
            raise ValueError("invalid_continuity_requirements")
        self.crypto = crypto
        self.session_id = session_id
        self.task_id = task_id
        self.risk_class = risk_class
        self.verification_requirements = verification_requirements
        self._sequence = 0
        self._previous = ""
        self._records: list[KernelContinuityRecord] = []

    @property
    def records(self) -> tuple[KernelContinuityRecord, ...]:
        return tuple(self._records)

    @staticmethod
    def _digest(crypto: CryptoIntegrity, domain: str, value: Any) -> str:
        return crypto.digest(domain, value)

    def _body(self, stage: str, sequence: int, state: Any, stage_input: Any,
              output: Any, dependency_tag: str, previous_tag: str) -> dict[str, Any]:
        if not isinstance(stage, str) or not stage.strip() or len(stage) > self.MAX_STAGE_LENGTH:
            raise ValueError("invalid_continuity_stage")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1 or sequence > self.MAX_SEQUENCE:
            raise ValueError("invalid_continuity_sequence")
        if not isinstance(dependency_tag, str) or len(dependency_tag) != 64:
            raise ValueError("invalid_continuity_dependency")
        if not isinstance(previous_tag, str) or (previous_tag and len(previous_tag) != 64):
            raise ValueError("invalid_continuity_previous")
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "stage": stage,
            "sequence": sequence,
            "risk_class": self.risk_class,
            "verification_requirements": self.verification_requirements,
            "state_digest": self._digest(self.crypto, "kernel_state", state),
            "input_digest": self._digest(self.crypto, "kernel_transition_input", stage_input),
            "output_digest": self._digest(self.crypto, "kernel_transition_output", output),
            "dependency_tag": dependency_tag,
            "previous_tag": previous_tag,
        }

    def attest(self, stage: str, state: Any, stage_input: Any, output: Any,
               *, dependency_tag: str) -> KernelContinuityRecord:
        if self._sequence >= self.MAX_SEQUENCE:
            raise OverflowError("continuity_sequence_exhausted")
        sequence = self._sequence + 1
        body = self._body(stage, sequence, state, stage_input, output, dependency_tag, self._previous)
        tag = self.crypto.digest("kernel_continuity", body)
        record = KernelContinuityRecord(
            self.task_id, stage, sequence,
            body["state_digest"], body["input_digest"], body["output_digest"],
            dependency_tag, self._previous, tag,
        )
        self._records.append(record)
        self._sequence = sequence
        self._previous = tag
        return record

    def verify(self, record: KernelContinuityRecord, stage: str, state: Any,
               stage_input: Any, output: Any, *, dependency_tag: str,
               previous_tag: str, sequence: int) -> bool:
        if not isinstance(record, KernelContinuityRecord):
            return False
        try:
            body = self._body(stage, sequence, state, stage_input, output, dependency_tag, previous_tag)
            expected = self.crypto.digest("kernel_continuity", body)
            if not hmac.compare_digest(expected, record.tag):
                return False
            return (
                record.task_id == self.task_id
                and record.stage == stage
                and record.sequence == sequence
                and record.state_digest == body["state_digest"]
                and record.input_digest == body["input_digest"]
                and record.output_digest == body["output_digest"]
                and record.dependency_tag == dependency_tag
                and record.previous_tag == previous_tag
            )
        except Exception:
            return False

    def verify_chain(self, records: tuple[KernelContinuityRecord, ...],
                     evidence: tuple[tuple[str, Any, Any, Any, str], ...]) -> bool:
        if not isinstance(records, tuple) or not isinstance(evidence, tuple) or not records:
            return False
        if len(records) != len(evidence):
            return False
        previous = ""
        for index, (record, item) in enumerate(zip(records, evidence), start=1):
            if not isinstance(item, tuple) or len(item) != 5:
                return False
            stage, state, stage_input, output, dependency_tag = item
            if not self.verify(record, stage, state, stage_input, output,
                               dependency_tag=dependency_tag, previous_tag=previous, sequence=index):
                return False
            previous = record.tag
        return True

    @staticmethod
    def attestation_tag(attestation: StageAttestation) -> str:
        if not isinstance(attestation, StageAttestation) or not isinstance(attestation.tag, str) or len(attestation.tag) != 64:
            raise ValueError("invalid_stage_attestation")
        return attestation.tag
