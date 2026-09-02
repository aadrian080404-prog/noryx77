"""Single-use authenticated acceptance lifecycle for HYPERSYNTH exports."""

from __future__ import annotations

from dataclasses import dataclass
import hmac
from typing import Any

from .crypto import CryptoEnvelope, CryptoIntegrity
from .export_manifest_121_130 import IntegrityManifest
from .export_manifest_boundary_131_140 import ExportManifestAcceptanceBoundary
from .attestation import StageAttestation
from .kernel_continuity import KernelContinuityRecord
from .kernel_continuity_81_90 import ContinuitySeal


@dataclass(frozen=True)
class AcceptanceReceipt:
    algorithm: str
    version: int
    nonce: str
    counter: int
    manifest_tag: str
    session_id: str
    task_id: str
    risk_class: str
    receipt_tag: str


class ExportAcceptanceController:
    """Fail-closed, cryptographically single-use admission of an authenticated export."""

    DOMAIN = "hypersynth_export_acceptance"
    ALGORITHM = CryptoIntegrity.ALGORITHM
    VERSION = CryptoIntegrity.VERSION
    COUNTER = 0

    def __init__(self, crypto: CryptoIntegrity):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto")
        self.crypto = crypto
        self._accepted: set[str] = set()
        self._receipts: dict[str, AcceptanceReceipt] = {}

    @staticmethod
    def _manifest_identity(manifest: IntegrityManifest) -> str:
        if not isinstance(manifest, IntegrityManifest):
            raise TypeError("invalid_manifest")
        if not isinstance(manifest.tag, str) or len(manifest.tag) != 64:
            raise ValueError("invalid_manifest_tag")
        return manifest.tag

    @classmethod
    def _receipt_payload(cls, *, nonce: str, manifest_tag: str, session_id: str, task_id: str, risk_class: str) -> dict[str, Any]:
        return {
            "algorithm": cls.ALGORITHM,
            "version": cls.VERSION,
            "nonce": nonce,
            "counter": cls.COUNTER,
            "manifest_tag": manifest_tag,
            "session_id": session_id,
            "task_id": task_id,
            "risk_class": risk_class,
        }

    def accept(
        self,
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
    ) -> AcceptanceReceipt | None:
        """Admit exactly once per manifest while the CryptoIntegrity state is retained."""
        try:
            if not ExportManifestAcceptanceBoundary.verify(
                self.crypto, manifest,
                session_id=session_id, task_id=task_id, risk_class=risk_class,
                requirements=requirements, stage_order=stage_order,
                attestations=attestations, payloads=payloads,
                continuity_records=continuity_records,
                continuity_evidence=continuity_evidence,
                continuity_seal=continuity_seal,
                final_continuity_tag=final_continuity_tag,
                context_tag=context_tag,
            ):
                return None
            identity = self._manifest_identity(manifest)
            if identity in self._accepted:
                return None
            if not all(isinstance(x, str) and x.strip() for x in (session_id, task_id, risk_class)):
                return None
            if not isinstance(requirements, tuple) or not isinstance(stage_order, tuple):
                return None

            # The manifest tag is the anti-replay nonce. CryptoIntegrity.consume=True
            # makes this admission one-use for this crypto state, even across controller objects.
            nonce = identity
            payload = self._receipt_payload(
                nonce=nonce, manifest_tag=identity, session_id=session_id,
                task_id=task_id, risk_class=risk_class,
            )
            envelope = self.crypto.sign(self.DOMAIN, payload, counter=self.COUNTER, nonce=nonce)
            if not self.crypto.verify(envelope, consume=True):
                return None
            receipt = AcceptanceReceipt(
                self.ALGORITHM, self.VERSION, nonce, self.COUNTER, identity,
                session_id, task_id, risk_class, envelope.tag,
            )
            self._accepted.add(identity)
            self._receipts[identity] = receipt
            return receipt
        except Exception:
            return None

    def verify_receipt(
        self,
        receipt: AcceptanceReceipt,
        *,
        manifest_tag: str,
        session_id: str,
        task_id: str,
        risk_class: str,
    ) -> bool:
        try:
            if not isinstance(receipt, AcceptanceReceipt):
                return False
            if receipt.algorithm != self.ALGORITHM or receipt.version != self.VERSION:
                return False
            if receipt.counter != self.COUNTER:
                return False
            if (receipt.manifest_tag != manifest_tag or receipt.session_id != session_id
                    or receipt.task_id != task_id or receipt.risk_class != risk_class):
                return False
            if receipt.nonce != manifest_tag:
                return False
            if not isinstance(receipt.receipt_tag, str) or len(receipt.receipt_tag) != 64:
                return False
            payload = self._receipt_payload(
                nonce=receipt.nonce, manifest_tag=receipt.manifest_tag,
                session_id=receipt.session_id, task_id=receipt.task_id,
                risk_class=receipt.risk_class,
            )
            envelope = CryptoEnvelope(
                self.DOMAIN, receipt.nonce, receipt.counter,
                self.crypto.canonical(payload), receipt.receipt_tag,
                self.ALGORITHM, self.VERSION,
            )
            return self.crypto.verify(envelope, consume=False) and self._receipts.get(manifest_tag) == receipt
        except Exception:
            return False

    def accepted(self, manifest_tag: str) -> bool:
        return isinstance(manifest_tag, str) and manifest_tag in self._accepted

    def receipt(self, manifest_tag: str) -> AcceptanceReceipt | None:
        return self._receipts.get(manifest_tag)


__all__ = ["AcceptanceReceipt", "ExportAcceptanceController"]
