"""Independent final-integrity verification for HYPERSYNTH evidence."""

from __future__ import annotations

import hmac
from typing import Any, Iterable

from .attestation import HypersynthAttestation, StageAttestation
from .crypto import CryptoIntegrity
from .kernel_continuity import KernelContinuity, KernelContinuityRecord
from .kernel_continuity_81_90 import ContinuitySeal


class HypersynthIntegrityVerifier:
    """Verify exported HYPERSYNTH integrity without trusting kernel-local state."""

    @staticmethod
    def verify_continuity_seal(crypto: CryptoIntegrity, seal: ContinuitySeal, records: Iterable[KernelContinuityRecord], *, session_id: str, task_id: str, stage_order: tuple[str, ...]) -> bool:
        try:
            if not isinstance(crypto, CryptoIntegrity) or not isinstance(seal, ContinuitySeal): return False
            records = tuple(records)
            if not isinstance(stage_order, tuple) or not stage_order or len(records) != len(stage_order): return False
            if seal.session_id != session_id or seal.task_id != task_id or seal.sequence != len(records): return False
            previous = ""
            tags: list[str] = []
            for index, (record, expected_stage) in enumerate(zip(records, stage_order), start=1):
                if not isinstance(record, KernelContinuityRecord): return False
                if record.task_id != task_id or record.stage != expected_stage: return False
                if record.sequence != index or record.previous_tag != previous: return False
                if not isinstance(record.tag, str) or len(record.tag) != 64 or record.tag in tags: return False
                tags.append(record.tag); previous = record.tag
            if seal.first_tag != tags[0] or seal.final_tag != tags[-1]: return False
            material = {"session_id": session_id, "task_id": task_id, "stage_order": stage_order, "sequence": len(records), "first_tag": tags[0], "final_tag": tags[-1], "chain": tuple(tags)}
            expected_digest = crypto.digest("kernel_continuity_chain", material)
            expected_seal = crypto.digest("kernel_continuity_seal", {**material, "chain_digest": expected_digest})
            return hmac.compare_digest(expected_digest, seal.chain_digest) and hmac.compare_digest(expected_seal, seal.seal)
        except Exception:
            return False

    @staticmethod
    def verify_continuity_chain(crypto: CryptoIntegrity, records: tuple[KernelContinuityRecord, ...], evidence: tuple[tuple[str, Any, Any, Any, str], ...], *, session_id: str, task_id: str, risk_class: str, requirements: tuple[str, ...], stage_order: tuple[str, ...]) -> bool:
        try:
            if not isinstance(crypto, CryptoIntegrity) or not isinstance(records, tuple) or not isinstance(evidence, tuple): return False
            if not isinstance(stage_order, tuple) or not stage_order or len(records) != len(evidence) or len(records) != len(stage_order): return False
            verifier = KernelContinuity(crypto, session_id=session_id, task_id=task_id, risk_class=risk_class, verification_requirements=requirements)
            previous = ""; seen: set[str] = set()
            for index, (record, item, expected_stage) in enumerate(zip(records, evidence, stage_order), start=1):
                if not isinstance(record, KernelContinuityRecord) or not isinstance(item, tuple) or len(item) != 5: return False
                stage, state, stage_input, output, dependency_tag = item
                if stage != expected_stage or record.task_id != task_id or record.stage != stage or record.sequence != index: return False
                if record.previous_tag != previous or record.tag in seen: return False
                if not verifier.verify(record, stage, state, stage_input, output, dependency_tag=dependency_tag, previous_tag=previous, sequence=index): return False
                seen.add(record.tag); previous = record.tag
            return True
        except Exception:
            return False

    @staticmethod
    def verify_attestation_chain(crypto: CryptoIntegrity, attestations: tuple[StageAttestation, ...], payloads: tuple[Any, ...], *, task_id: str, risk_class: str, requirements: tuple[str, ...], stage_order: tuple[str, ...], session_id: str | None = None, context_tag: str | None = None) -> bool:
        try:
            if not isinstance(crypto, CryptoIntegrity) or not isinstance(attestations, tuple) or not isinstance(payloads, tuple): return False
            if not isinstance(stage_order, tuple) or not stage_order or len(attestations) != len(payloads) or len(attestations) != len(stage_order): return False
            if (session_id is None) != (context_tag is None): return False
            verifier = HypersynthAttestation(crypto); previous = ""
            for index, (attestation, payload, expected_stage) in enumerate(zip(attestations, payloads, stage_order), start=1):
                if not isinstance(attestation, StageAttestation): return False
                if attestation.task_id != task_id or attestation.stage != expected_stage or attestation.sequence != index or attestation.risk_class != risk_class or attestation.verification_requirements != requirements or attestation.previous_tag != previous: return False
                verification_payload = payload if session_id is None else {"session_id": session_id, "context_tag": context_tag, "payload": payload}
                if not verifier.verify_stage(attestation, verification_payload): return False
                previous = attestation.tag
            return True
        except Exception:
            return False

    @staticmethod
    def final_tag(crypto: CryptoIntegrity, *, session_id: str, task_id: str, risk_class: str, requirements: tuple[str, ...], stage_order: tuple[str, ...], stage_tags: tuple[str, ...], continuity_tags: tuple[str, ...], continuity_seal: str) -> str:
        material = {"session_id": session_id, "task_id": task_id, "risk_class": risk_class, "verification_requirements": requirements, "stage_order": stage_order, "stage_tags": stage_tags, "continuity_tags": continuity_tags, "continuity_seal": continuity_seal}
        return crypto.digest("hypersynth_final_continuity", material)

    @classmethod
    def verify_exported_integrity(cls, crypto: CryptoIntegrity, *, session_id: str, task_id: str, risk_class: str, requirements: tuple[str, ...], stage_order: tuple[str, ...], attestations: tuple[StageAttestation, ...], payloads: tuple[Any, ...], continuity_records: tuple[KernelContinuityRecord, ...], continuity_seal: ContinuitySeal, final_continuity_tag: str, context_tag: str | None = None, continuity_evidence: tuple[tuple[str, Any, Any, Any, str], ...]) -> bool:
        """Verify a complete exported evidence set; continuity evidence is mandatory."""
        try:
            if not isinstance(continuity_evidence, tuple): return False
            if not cls.verify_attestation_chain(crypto, attestations, payloads, task_id=task_id, risk_class=risk_class, requirements=requirements, stage_order=stage_order, session_id=session_id, context_tag=context_tag): return False
            if not cls.verify_continuity_chain(crypto, continuity_records, continuity_evidence, session_id=session_id, task_id=task_id, risk_class=risk_class, requirements=requirements, stage_order=stage_order): return False
            if not cls.verify_continuity_seal(crypto, continuity_seal, continuity_records, session_id=session_id, task_id=task_id, stage_order=stage_order): return False
            if not isinstance(final_continuity_tag, str) or len(final_continuity_tag) != 64: return False
            expected = cls.final_tag(crypto, session_id=session_id, task_id=task_id, risk_class=risk_class, requirements=requirements, stage_order=stage_order, stage_tags=tuple(item.tag for item in attestations), continuity_tags=tuple(item.tag for item in continuity_records), continuity_seal=continuity_seal.seal)
            return hmac.compare_digest(expected, final_continuity_tag)
        except Exception:
            return False


__all__ = ["HypersynthIntegrityVerifier"]
