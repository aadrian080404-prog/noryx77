"""Independent acceptance boundary for authenticated HYPERSYNTH exports."""

from __future__ import annotations

from typing import Any

from .attestation import StageAttestation
from .crypto import CryptoIntegrity
from .export_manifest_121_130 import ExportIntegrityManifest, IntegrityManifest
from .hypersynth_integrity_91_100 import HypersynthIntegrityVerifier
from .kernel_continuity import KernelContinuityRecord
from .kernel_continuity_81_90 import ContinuitySeal


class ExportManifestAcceptanceBoundary:
    """Fail-closed boundary that never trusts a manifest without independent evidence verification."""

    STAGE_ORDER = HypersynthIntegrityVerifier.REQUIRED_STAGE_ORDER if hasattr(
        HypersynthIntegrityVerifier, "REQUIRED_STAGE_ORDER"
    ) else (
        "perception", "context", "planning", "hypothesis", "simulation",
        "allocation", "execution", "verification", "metacognition",
    )

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
        context_tag: str,
    ) -> bool:
        """Accept only a manifest whose complete evidence is independently valid."""
        try:
            if not isinstance(crypto, CryptoIntegrity):
                return False
            if stage_order != cls.STAGE_ORDER:
                return False
            if not isinstance(context_tag, str) or len(context_tag) != 64:
                return False
            if not HypersynthIntegrityVerifier.verify_exported_integrity(
                crypto,
                session_id=session_id,
                task_id=task_id,
                risk_class=risk_class,
                requirements=requirements,
                stage_order=stage_order,
                attestations=attestations,
                payloads=payloads,
                continuity_records=continuity_records,
                continuity_seal=continuity_seal,
                final_continuity_tag=final_continuity_tag,
                context_tag=context_tag,
                continuity_evidence=continuity_evidence,
            ):
                return False
            return ExportIntegrityManifest.verify(
                crypto,
                manifest,
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
        except Exception:
            return False


__all__ = ["ExportManifestAcceptanceBoundary"]
