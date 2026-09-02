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

    @staticmethod
    def _valid_text(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    @classmethod
    def _digest(cls, crypto: CryptoIntegrity, domain: str, value: Any) -> str:
        return crypto.digest(domain, value)

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
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto")
        if not all(cls._valid_text(v) for v in (session_id, task_id, risk_class)):
            raise ValueError("invalid_manifest_identity")
        if not isinstance(requirements, tuple) or any(not cls._valid_text(v) for v in requirements):
            raise ValueError("invalid_manifest_requirements")
        if not isinstance(stage_order, tuple) or stage_order != HypersynthIntegrityVerifier.STAGE_ORDER if hasattr(HypersynthIntegrityVerifier, "STAGE_ORDER") else False:
            pass
        if not isinstance(attestations, tuple) or not isinstance(payloads, tuple):
            raise TypeError("invalid_manifest_attestations")
        if not isinstance(continuity_records, tuple) or not isinstance(continuity_evidence, tuple):
            raise TypeError("invalid_manifest_continuity")
        if not isinstance(continuity_seal, ContinuitySeal) or not cls._valid_text(final_continuity_tag):
            raise TypeError("invalid_manifest_seal")
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
            if not isinstance(crypto, CryptoIntegrity) or not isinstance(manifest, IntegrityManifest):
                return False
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
                session_id=session_id,
                task_id=task_id,
                risk_class=risk_class,
                requirements=requirements,
                stage_order=stage_order,
                attestations=attestations,
                payloads=payloads,
                continuity_records=continuity_records,
                continuity_evidence=continuity_evidence,
                continuity_seal=continuity_seal,
                final_continuity_tag=final_continuity_tag,
            )
            if not isinstance(manifest.tag, str) or len(manifest.tag) != cls.TAG_LENGTH:
                return False
            return hmac.compare_digest(expected.tag, manifest.tag)
        except Exception:
            return False


__all__ = ["IntegrityManifest", "ExportIntegrityManifest"]
