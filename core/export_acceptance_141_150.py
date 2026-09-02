"""Single-use authenticated acceptance lifecycle for HYPERSYNTH exports."""

from __future__ import annotations

from dataclasses import dataclass
import hmac
import secrets
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
    """Fail-closed, single-use admission of an already authenticated export."""

    DOMAIN = "hypersynth_export_acceptance"
    ALGORITHM = CryptoIntegrity.ALGORITHM
    VERSION = CryptoIntegrity.VERSION

    def __init__(self, crypto: CryptoIntegrity):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto")
        self.crypto = crypto
        self._counter = 0
        self._accepted: set[str] = set()
        self._receipts: dict[str, AcceptanceReceipt] = {}

    @staticmethod
    def _manifest_identity(manifest: IntegrityManifest) -> str:
        return manifest.tag

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
            counter = self._counter + 1
            if counter >= 2**64:
                return None
            nonce = secrets.token_hex(16)
            payload = {
                "algorithm": self.ALGORITHM,
                "version": self.VERSION,
                "nonce": nonce,
                "counter": counter,
                "manifest_tag": identity,
                "session_id": session_id,
                "task_id": task_id,
                "risk_class": risk_class,
            }
            envelope = self.crypto.sign(self.DOMAIN, payload, counter=counter, nonce=nonce)
            if not self.crypto.verify(envelope, consume=True):
                return None
            receipt = AcceptanceReceipt(
                self.ALGORITHM, self.VERSION, nonce, counter, identity,
                session_id, task_id, risk_class, envelope.tag,
            )
            self._accepted.add(identity)
            self._receipts[identity] = receipt
            self._counter = counter
            return receipt
        except Exception:
            return None

    def verify_receipt(self, receipt: AcceptanceReceipt, *, manifest_tag: str, session_id: str, task_id: str, risk_class: str) -> bool:
        try:
            if not isinstance(receipt, AcceptanceReceipt):
                return False
            if receipt.algorithm != self.ALGORITHM or receipt.version != self.VERSION:
                return False
            if receipt.manifest_tag != manifest_tag or receipt.session_id != session_id or receipt.task_id != task_id or receipt.risk_class != risk_class:
                return False
            if not isinstance(receipt.nonce, str) or not receipt.nonce.strip() or not isinstance(receipt.counter, int) or receipt.counter <= 0:
                return False
            payload = {
                "algorithm": receipt.algorithm,
                "version": receipt.version,
                "nonce": receipt.nonce,
                "counter": receipt.counter,
                "manifest_tag": receipt.manifest_tag,
                "session_id": receipt.session_id,
                "task_id": receipt.task_id,
                "risk_class": receipt.risk_class,
            }
            expected = self.crypto.sign(self.DOMAIN, payload, counter=receipt.counter, nonce=receipt.nonce).tag
            return hmac.compare_digest(expected, receipt.receipt_tag) and self._receipts.get(manifest_tag) == receipt
        except Exception:
            return False

    def accepted(self, manifest_tag: str) -> bool:
        return isinstance(manifest_tag, str) and manifest_tag in self._accepted

    def receipt(self, manifest_tag: str) -> AcceptanceReceipt | None:
        return self._receipts.get(manifest_tag)


__all__ = ["AcceptanceReceipt", "ExportAcceptanceController"]
