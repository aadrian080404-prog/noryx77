"""Authenticated export manifest for HYPERSYNTH integrity evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import hmac

from .crypto import CryptoIntegrity
from .attestation import StageAttestation
from .kernel_continuity import KernelContinuityRecord
from .kernel_continuity_81_90 import ContinuitySeal
from .hypersynth_integrity_91_100 import HypersynthIntegrityVerifier


@dataclass(frozen=True)
class IntegrityManifest:
    algorithm: str
    version: int
    session_id: str
    task_id: str
    risk_class: str
    requirements: tuple[str, ...]
    stage_order: tuple[str, ...]
    attestations_digest: str
    payloads_digest: str
    continuity_records_digest: str
    continuity_evidence_digest: str
    continuity_seal_digest: str
    final_continuity_tag: str
    tag: str


class ExportIntegrityManifest:
    """Binds every exported evidence collection into one authenticated manifest."""

    ALGORITHM = "HMAC-SHA256"
    VERSION = 1
    DOMAIN = "hypersynth_export_manifest"
    TAG_LENGTH = 64
    REQUIRED_STAGE_ORDER = (
        "perception", "context", "planning", "hypothesis", "simulation",
        "allocation", "execution", "verification", "metacognition",
    )

    @staticmethod
    def _valid_text(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    @classmethod
    def _digest(cls, crypto: CryptoIntegrity, domain: str, value: Any) -> str:
        return crypto.digest(domain, value)

    @classmethod
    def _validate_inputs(
        cls, crypto: CryptoIntegrity, *, session_id: str, task_id: str, risk_class: str,
        requirements: tuple[str, ...], stage_order: tuple[str, ...],
        attestations: tuple[StageAttestation, ...], payloads: tuple[Any, ...],
        continuity_records: tuple[KernelContinuityRecord, ...],
        continuity_evidence: tuple[tuple[str, Any, Any, Any, str], ...],
        continuity_seal: ContinuitySeal, final_continuity_tag: str,
    ) -> None:
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto")
        if not all(cls._valid_text(v) for v in (session_id, task_id, risk_class)):
            raise ValueError("invalid_manifest_identity")
        if not isinstance(requirements, tuple) or any(not cls._valid_text(v) for v in requirements):
            raise ValueError("invalid_manifest_requirements")
        if stage_order != cls.REQUIRED_STAGE_ORDER:
            raise ValueError("invalid_manifest_stage_order")
        if not isinstance(attestations, tuple) or not isinstance(payloads, tuple):
            raise TypeError("invalid_manifest_attestations")
        if not isinstance(continuity_records, tuple) or not isinstance(continuity_evidence, tuple):
            raise TypeError("invalid_manifest_continuity")
        if len(attestations) != len(stage_order) or len(payloads) != len(stage_order):
            raise ValueError("invalid_manifest_stage_count")
        if len(continuity_records) != len(stage_order) or len(continuity_evidence) != len(stage_order):
            raise ValueError("invalid_manifest_continuity_count")
        if not isinstance(continuity_seal, ContinuitySeal):
            raise TypeError("invalid_manifest_seal")
        if not isinstance(final_continuity_tag, str) or len(final_continuity_tag) != cls.TAG_LENGTH:
            raise ValueError("invalid_manifest_final_tag")

    @classmethod
    def create(
        cls,
        crypto: CryptoIntegrity,
        *,
        session_id: str,
        task_id: str,
        risk_class: str,
        requirements: tuple[str, ...],
        stage_order: tuple[str, ...],
        attestations: tuple[StageAttestation, ...],
        payloads: tuple[Any, ...],
        continuity_records: tuple[KernelContinuityRecord, ...],
        continuity_evidence: tuple[tuple[str, Any, Any, Any, str], ...],
        continuity_seal: ContinuitySeal,
        final_continuity_tag: str,
    ) -> IntegrityManifest:
        cls._validate_inputs(
            crypto, session_id=session_id, task_id=task_id, risk_class=risk_class,
            requirements=requirements, stage_order=stage_order, attestations=attestations,
            payloads=payloads, continuity_records=continuity_records,
            continuity_evidence=continuity_evidence, continuity_seal=continuity_seal,
            final_continuity_tag=final_continuity_tag,
        )
        material = {
            "algorithm": cls.ALGORITHM,
            "version": cls.VERSION,
            "session_id": session_id,
            "task_id": task_id,
            "risk_class": risk_class,
            "requirements": requirements,
            "stage_order": stage_order,
            "attestations_digest": cls._digest(crypto, "hypersynth_manifest_attestations", attestations),
            "payloads_digest": cls._digest(crypto, "hypersynth_manifest_payloads", payloads),
            "continuity_records_digest": cls._digest(crypto, "hypersynth_manifest_records", continuity_records),
            "continuity_evidence_digest": cls._digest(crypto, "hypersynth_manifest_evidence", continuity_evidence),
            "continuity_seal_digest": cls._digest(crypto, "hypersynth_manifest_seal", continuity_seal),
            "final_continuity_tag": final_continuity_tag,
        }
        tag = crypto.digest(cls.DOMAIN, material)
        return IntegrityManifest(**material, tag=tag)

    @classmethod
    def verify(
        cls,
        crypto: CryptoIntegrity,
        manifest: IntegrityManifest,
        *,
        session_id: str,
        task_id: str,
        risk_class: str,
        requirements: tuple[str, ...],
        stage_order: tuple[str, ...],
        attestations: tuple[StageAttestation, ...],
        payloads: tuple[Any, ...],
        continuity_records: tuple[KernelContinuityRecord, ...],
        continuity_evidence: tuple[tuple[str, Any, Any, Any, str], ...],
        continuity_seal: ContinuitySeal,
        final_continuity_tag: str,
    ) -> bool:
        try:
            if not isinstance(manifest, IntegrityManifest):
                return False
            cls._validate_inputs(
                crypto, session_id=session_id, task_id=task_id, risk_class=risk_class,
                requirements=requirements, stage_order=stage_order, attestations=attestations,
                payloads=payloads, continuity_records=continuity_records,
                continuity_evidence=continuity_evidence, continuity_seal=continuity_seal,
                final_continuity_tag=final_continuity_tag,
            )
            if manifest.algorithm != cls.ALGORITHM or manifest.version != cls.VERSION:
                return False
            if (manifest.session_id, manifest.task_id, manifest.risk_class) != (session_id, task_id, risk_class):
                return False
            if manifest.requirements != requirements or manifest.stage_order != stage_order:
                return False
            if manifest.final_continuity_tag != final_continuity_tag:
                return False
            expected = cls.create(
                crypto,
                session_id=session_id, task_id=task_id, risk_class=risk_class,
                requirements=requirements, stage_order=stage_order, attestations=attestations,
                payloads=payloads, continuity_records=continuity_records,
                continuity_evidence=continuity_evidence, continuity_seal=continuity_seal,
                final_continuity_tag=final_continuity_tag,
            )
            return isinstance(manifest.tag, str) and len(manifest.tag) == cls.TAG_LENGTH and hmac.compare_digest(expected.tag, manifest.tag)
        except Exception:
            return False


__all__ = ["IntegrityManifest", "ExportIntegrityManifest"]
