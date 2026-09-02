"""Attested HYPERSYNTH execution facade."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from .attestation import HypersynthAttestation, StageAttestation
from .attestation_session import AttestationSession
from .contracts import TaskSpec
from .crypto import CryptoIntegrity
from .hypersynth import Hypersynth
from .kernel_continuity import KernelContinuity, KernelContinuityRecord
from .kernel_continuity_81_90 import ContinuitySeal, KernelContinuityPolicy
from .hypersynth_integrity_91_100 import HypersynthIntegrityVerifier
from .export_manifest_121_130 import ExportIntegrityManifest, IntegrityManifest
from .export_manifest_boundary_131_140 import ExportManifestAcceptanceBoundary


class AttestedHypersynthKernel:
    """Run the bounded kernel and emit authenticated stage evidence."""

    STAGE_ORDER = (
        "perception", "context", "planning", "hypothesis", "simulation",
        "allocation", "execution", "verification", "metacognition",
    )

    def __init__(self, kernel: Hypersynth, *, crypto: CryptoIntegrity | None = None,
                 attestation: HypersynthAttestation | None = None):
        if not isinstance(kernel, Hypersynth):
            raise TypeError("invalid_hypersynth_kernel")
        if attestation is not None and crypto is not None:
            raise ValueError("crypto_and_attestation_are_mutually_exclusive")
        self.kernel = kernel
        self.attestation = attestation or HypersynthAttestation(crypto or CryptoIntegrity())

    @classmethod
    def _canonical(cls, value: Any) -> Any:
        if is_dataclass(value) and not isinstance(value, type):
            return {key: cls._canonical(item) for key, item in asdict(value).items()}
        if isinstance(value, dict):
            return {str(key): cls._canonical(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [cls._canonical(item) for item in value]
        if isinstance(value, (str, int, bool)) or value is None:
            return value
        if isinstance(value, float):
            if value != value or value in (float("inf"), float("-inf")):
                raise TypeError("non_finite_kernel_evidence")
            return value
        raise TypeError("non_canonical_kernel_evidence")

    @classmethod
    def _payload(cls, result: dict[str, Any], stage: str) -> Any:
        if stage == "perception":
            state = result.get("state")
            return {"task_id": getattr(state, "task_id", result.get("task_id")),
                    "verification": cls._canonical(result.get("verification"))}
        if stage == "context":
            return cls._canonical(result.get("context"))
        if stage == "planning":
            return cls._canonical(result.get("plan"))
        if stage == "hypothesis":
            return cls._canonical(result.get("hypotheses"))
        if stage == "simulation":
            return cls._canonical(result.get("simulations"))
        if stage == "allocation":
            return cls._canonical(tuple((r.agent_id, r.task_id) for r in result.get("results", ())))
        if stage == "execution":
            return cls._canonical(result.get("results"))
        if stage == "verification":
            return cls._canonical(result.get("verification"))
        if stage == "metacognition":
            return cls._canonical(result.get("reflection"))
        raise ValueError("unknown_hypersynth_stage")

    @classmethod
    def _continuity_state(cls, result: dict[str, Any], stage: str) -> Any:
        state = result.get("state")
        return {"stage": stage, "state": cls._canonical(state),
                "status": result.get("status"), "phase": result.get("phase")}

    @classmethod
    def _continuity_input(cls, result: dict[str, Any], stage: str, previous: str) -> Any:
        return {"stage": stage, "previous_continuity_tag": previous,
                "payload": cls._payload(result, stage)}

    @staticmethod
    def _reject(phase: str, reason: str, *, attestations=(), continuity_records=(), **extra):
        return {"status": "rejected", "phase": phase,
                "verification": {"valid": False, "reason": reason},
                "attestations": tuple(attestations),
                "continuity_records": tuple(continuity_records), **extra}

    def run(self, task):
        # TaskSpec is the source-of-truth identity for every downstream
        # attestation field.  Reject subclasses before invoking the kernel so
        # hostile attribute access cannot influence execution or authentication.
        if type(task) is not TaskSpec or not task.is_well_formed():
            raise RuntimeError("malformed_hypersynth_task_contract")
        result = self.kernel.run(task)
        if not isinstance(result, dict):
            raise RuntimeError("malformed_hypersynth_result")
        task_id = task.task_id
        risk_class = task.risk_class
        requirements = task.verification_requirements
        if (not isinstance(task_id, str) or not task_id.strip()
                or not isinstance(risk_class, str) or not risk_class.strip()
                or not isinstance(requirements, tuple)):
            raise RuntimeError("malformed_hypersynth_task_contract")

        if result.get("status") != "completed":
            return {**result, "attestations": ()}

        try:
            session = AttestationSession(self.attestation.crypto, task_id, risk_class, requirements)
            continuity = KernelContinuity(
                self.attestation.crypto, session_id=session.session_id,
                task_id=task_id, risk_class=risk_class,
                verification_requirements=requirements,
            )
            continuity_policy = KernelContinuityPolicy(
                self.attestation.crypto, session_id=session.session_id,
                task_id=task_id, stage_order=self.STAGE_ORDER,
            )
        except Exception as exc:
            return self._reject("perception", "attestation_session_failure",
                                error=type(exc).__name__)

        attestations: list[StageAttestation] = []
        payloads: list[Any] = []
        continuity_records: list[KernelContinuityRecord] = []
        continuity_evidence: list[tuple[str, Any, Any, Any, str]] = []
        previous_continuity = ""

        for stage in self.STAGE_ORDER:
            try:
                payload = self._payload(result, stage)
                attestation = session.attest(stage, payload)
                dependency = session.context_tag if not attestations else attestations[-1].tag
                state = self._continuity_state(result, stage)
                stage_input = self._continuity_input(result, stage, previous_continuity)
                record = continuity.attest(stage, state, stage_input, payload, dependency_tag=dependency)
                attestations.append(attestation)
                payloads.append(payload)
                continuity_records.append(record)
                continuity_evidence.append((stage, state, stage_input, payload, dependency))
                previous_continuity = record.tag
            except Exception as exc:
                session.close()
                return self._reject(stage, "attestation_failure",
                                    attestations=attestations,
                                    continuity_records=continuity_records,
                                    error=type(exc).__name__)

        chain = tuple(attestations)
        continuity_chain = tuple(continuity_records)
        evidence = tuple(continuity_evidence)
        for stage, attestation, payload in zip(self.STAGE_ORDER, chain, payloads):
            if not session.verify(attestation, stage, payload, consume=True):
                session.close()
                return self._reject("verification", "attestation_session_verification_failure",
                                    attestations=chain, continuity_records=continuity_chain)

        if not continuity.verify_chain(continuity_chain, evidence):
            session.close()
            return self._reject("verification", "kernel_continuity_verification_failure",
                                attestations=chain, continuity_records=continuity_chain)

        if not continuity_policy.admit(continuity_chain):
            session.close()
            return self._reject("verification", "kernel_continuity_policy_rejection",
                                attestations=chain, continuity_records=continuity_chain)

        try:
            continuity_seal: ContinuitySeal = continuity_policy.seal(continuity_chain)
        except Exception:
            session.close()
            return self._reject("verification", "kernel_continuity_seal_failure",
                                attestations=chain, continuity_records=continuity_chain)

        if not continuity_policy.verify_seal(continuity_seal, continuity_chain):
            session.close()
            return self._reject("verification", "kernel_continuity_seal_verification_failure",
                                attestations=chain, continuity_records=continuity_chain)

        stage_tags = tuple(item.tag for item in chain)
        continuity_tags = tuple(item.tag for item in continuity_chain)
        final_tag = HypersynthIntegrityVerifier.final_tag(
            self.attestation.crypto,
            session_id=session.session_id,
            task_id=task_id,
            risk_class=risk_class,
            requirements=requirements,
            stage_order=self.STAGE_ORDER,
            stage_tags=stage_tags,
            continuity_tags=continuity_tags,
            continuity_seal=continuity_seal.seal,
        )

        exported_ok = HypersynthIntegrityVerifier.verify_exported_integrity(
            self.attestation.crypto,
            session_id=session.session_id,
            task_id=task_id,
            risk_class=risk_class,
            requirements=requirements,
            stage_order=self.STAGE_ORDER,
            attestations=chain,
            payloads=tuple(payloads),
            continuity_records=continuity_chain,
            continuity_seal=continuity_seal,
            final_continuity_tag=final_tag,
            context_tag=session.context_tag,
            continuity_evidence=evidence,
        )
        if not exported_ok:
            session.close()
            return self._reject("verification", "independent_final_integrity_failure",
                                attestations=chain, continuity_records=continuity_chain)

        try:
            manifest = ExportIntegrityManifest.create(
                self.attestation.crypto,
                session_id=session.session_id,
                task_id=task_id,
                risk_class=risk_class,
                requirements=requirements,
                stage_order=self.STAGE_ORDER,
                attestations=chain,
                payloads=tuple(payloads),
                continuity_records=continuity_chain,
                continuity_evidence=evidence,
                continuity_seal=continuity_seal,
                final_continuity_tag=final_tag,
            )
            manifest_ok = ExportManifestAcceptanceBoundary.verify(
                self.attestation.crypto,
                manifest,
                session_id=session.session_id,
                task_id=task_id,
                risk_class=risk_class,
                requirements=requirements,
                stage_order=self.STAGE_ORDER,
                attestations=chain,
                payloads=tuple(payloads),
                continuity_records=continuity_chain,
                continuity_evidence=evidence,
                continuity_seal=continuity_seal,
                final_continuity_tag=final_tag,
                context_tag=session.context_tag,
            )
        except Exception:
            session.close()
            return self._reject("verification", "export_manifest_failure",
                                attestations=chain, continuity_records=continuity_chain)
        session.close()
        if not manifest_ok:
            return self._reject("verification", "export_manifest_verification_failure",
                                attestations=chain, continuity_records=continuity_chain)

        return {
            **result,
            "attestations": chain,
            "attestation_verified": True,
            "attestation_session_id": session.session_id,
            "attestation_context_tag": session.context_tag,
            "continuity_records": continuity_chain,
            "continuity_evidence": evidence,
            "continuity_verified": True,
            "continuity_seal": continuity_seal,
            "final_continuity_tag": final_tag,
            "integrity_manifest": manifest,
            "export_manifest_verified": True,
            "final_integrity_verified": True,
        }


__all__ = ["AttestedHypersynthKernel"]
