"""Strict exported-evidence boundary for HYPERSYNTH integrity verification."""

from __future__ import annotations

import hmac
from typing import Any

from .attestation import StageAttestation
from .crypto import CryptoIntegrity
from .hypersynth_integrity_91_100 import HypersynthIntegrityVerifier
from .kernel_continuity import KernelContinuityRecord
from .kernel_continuity_81_90 import ContinuitySeal


class ExportedIntegrityBoundary:
    """Fail closed when exported evidence is incomplete, substituted, or malformed."""

    REQUIRED_STAGE_COUNT = 9
    REQUIRED_STAGE_ORDER = (
        "perception", "context", "planning", "hypothesis", "simulation",
        "allocation", "execution", "verification", "metacognition",
    )
    TAG_LENGTH = 64

    @classmethod
    def verify(
        cls,
        crypto: CryptoIntegrity,
        *,
        session_id: str,
        context_tag: str,
        task_id: str,
        risk_class: str,
        requirements: tuple[str, ...],
        attestations: tuple[StageAttestation, ...],
        payloads: tuple[Any, ...],
        continuity_records: tuple[KernelContinuityRecord, ...],
        continuity_evidence: tuple[tuple[str, Any, Any, Any, str], ...],
        continuity_seal: ContinuitySeal,
        final_continuity_tag: str,
    ) -> bool:
        """Verify the complete exported evidence set; no optional integrity inputs are accepted."""
        try:
            if not isinstance(crypto, CryptoIntegrity):
                return False
            if not all(isinstance(value, str) and value.strip() for value in
                       (session_id, context_tag, task_id, risk_class)):
                return False
            if not isinstance(requirements, tuple) or any(
                not isinstance(item, str) or not item.strip() for item in requirements
            ):
                return False
            if not isinstance(attestations, tuple) or not isinstance(payloads, tuple):
                return False
            if not isinstance(continuity_records, tuple) or not isinstance(continuity_evidence, tuple):
                return False
            if len(attestations) != cls.REQUIRED_STAGE_COUNT or len(payloads) != cls.REQUIRED_STAGE_COUNT:
                return False
            if len(continuity_records) != cls.REQUIRED_STAGE_COUNT or len(continuity_evidence) != cls.REQUIRED_STAGE_COUNT:
                return False
            if not isinstance(continuity_seal, ContinuitySeal):
                return False
            if not isinstance(final_continuity_tag, str) or len(final_continuity_tag) != cls.TAG_LENGTH:
                return False
            if context_tag != crypto.digest(
                "hypersynth_session",
                {"session_id": session_id, "task_id": task_id,
                 "risk_class": risk_class,
                 "verification_requirements": requirements},
            ):
                return False
            for index, (attestation, payload, record, evidence) in enumerate(
                zip(attestations, payloads, continuity_records, continuity_evidence), start=1
            ):
                if not isinstance(attestation, StageAttestation) or not isinstance(record, KernelContinuityRecord):
                    return False
                if attestation.stage != cls.REQUIRED_STAGE_ORDER[index - 1]:
                    return False
                if record.stage != cls.REQUIRED_STAGE_ORDER[index - 1]:
                    return False
                if not isinstance(evidence, tuple) or len(evidence) != 5:
                    return False
                if evidence[0] != cls.REQUIRED_STAGE_ORDER[index - 1]:
                    return False
            if not HypersynthIntegrityVerifier.verify_exported_integrity(
                crypto,
                session_id=session_id,
                task_id=task_id,
                risk_class=risk_class,
                requirements=requirements,
                stage_order=cls.REQUIRED_STAGE_ORDER,
                attestations=attestations,
                payloads=payloads,
                continuity_records=continuity_records,
                continuity_seal=continuity_seal,
                final_continuity_tag=final_continuity_tag,
                context_tag=context_tag,
                continuity_evidence=continuity_evidence,
            ):
                return False
            expected_final = HypersynthIntegrityVerifier.final_tag(
                crypto,
                session_id=session_id,
                task_id=task_id,
                risk_class=risk_class,
                requirements=requirements,
                stage_order=cls.REQUIRED_STAGE_ORDER,
                stage_tags=tuple(item.tag for item in attestations),
                continuity_tags=tuple(item.tag for item in continuity_records),
                continuity_seal=continuity_seal.seal,
            )
            return hmac.compare_digest(expected_final, final_continuity_tag)
        except Exception:
            return False


__all__ = ["ExportedIntegrityBoundary"]
