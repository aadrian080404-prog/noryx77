"""Additional fail-closed controls for authenticated kernel continuity."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Iterable

from .crypto import CryptoIntegrity
from .kernel_continuity import KernelContinuityRecord


@dataclass(frozen=True)
class ContinuitySeal:
    session_id: str
    task_id: str
    sequence: int
    first_tag: str
    final_tag: str
    chain_digest: str
    seal: str


class KernelContinuityPolicy:
    """Admission/finalization checks for a KernelContinuity record chain."""

    def __init__(self, crypto: CryptoIntegrity, *, session_id: str, task_id: str,
                 stage_order: tuple[str, ...]):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto_integrity")
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("invalid_session_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("invalid_task_id")
        if not isinstance(stage_order, tuple) or not stage_order or len(set(stage_order)) != len(stage_order):
            raise ValueError("invalid_stage_order")
        if any(not isinstance(stage, str) or not stage.strip() for stage in stage_order):
            raise ValueError("invalid_stage_order")
        self.crypto = crypto
        self.session_id = session_id
        self.task_id = task_id
        self.stage_order = stage_order
        self._sealed = False

    def _admit_records(self, records: Iterable[KernelContinuityRecord]) -> bool:
        try:
            records = tuple(records)
            if len(records) != len(self.stage_order):
                return False
            previous = ""
            seen: set[str] = set()
            for index, (record, expected_stage) in enumerate(zip(records, self.stage_order), start=1):
                if not isinstance(record, KernelContinuityRecord):
                    return False
                if record.task_id != self.task_id or record.stage != expected_stage:
                    return False
                if record.sequence != index or record.previous_tag != previous:
                    return False
                if not isinstance(record.tag, str) or len(record.tag) != 64 or record.tag in seen:
                    return False
                seen.add(record.tag)
                previous = record.tag
            return True
        except Exception:
            return False

    def admit(self, records: Iterable[KernelContinuityRecord]) -> bool:
        return not self._sealed and self._admit_records(records)

    def seal(self, records: tuple[KernelContinuityRecord, ...]) -> ContinuitySeal:
        if not self.admit(records):
            raise ValueError("continuity_chain_not_admissible")
        chain = tuple(record.tag for record in records)
        material = {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "stage_order": self.stage_order,
            "sequence": len(records),
            "first_tag": chain[0],
            "final_tag": chain[-1],
            "chain": chain,
        }
        chain_digest = self.crypto.digest("kernel_continuity_chain", material)
        seal = self.crypto.digest("kernel_continuity_seal", {**material, "chain_digest": chain_digest})
        self._sealed = True
        return ContinuitySeal(self.session_id, self.task_id, len(records), chain[0], chain[-1], chain_digest, seal)

    def verify_seal(self, seal: ContinuitySeal, records: tuple[KernelContinuityRecord, ...]) -> bool:
        try:
            if not isinstance(seal, ContinuitySeal) or not self._admit_records(records):
                return False
            chain = tuple(record.tag for record in records)
            if (seal.session_id != self.session_id or seal.task_id != self.task_id
                    or seal.sequence != len(records) or seal.first_tag != chain[0]
                    or seal.final_tag != chain[-1]):
                return False
            material = {
                "session_id": self.session_id,
                "task_id": self.task_id,
                "stage_order": self.stage_order,
                "sequence": len(records),
                "first_tag": chain[0],
                "final_tag": chain[-1],
                "chain": chain,
            }
            expected_digest = self.crypto.digest("kernel_continuity_chain", material)
            expected_seal = self.crypto.digest("kernel_continuity_seal", {**material, "chain_digest": expected_digest})
            return hmac.compare_digest(expected_digest, seal.chain_digest) and hmac.compare_digest(expected_seal, seal.seal)
        except Exception:
            return False
