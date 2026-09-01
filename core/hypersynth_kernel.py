"""Attested HYPERSYNTH execution facade.

The existing Hypersynth remains the execution engine. This facade adds
cryptographically bound evidence over its externally observable stages and a
separate continuity chain for state/transition integrity. Cryptography does
not establish semantic or factual truth.
"""

from __future__ import annotations

import hmac
from dataclasses import asdict, is_dataclass
from typing import Any

from .attestation import HypersynthAttestation, StageAttestation
from .attestation_session import AttestationSession
from .crypto import CryptoIntegrity
from .hypersynth import Hypersynth
from .kernel_continuity import KernelContinuity, KernelContinuityRecord


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
        """Return the canonical observable state bound to a stage transition."""
        state = result.get("state")
        return {
            "stage": stage,
            "state": cls._canonical(state),
            "status": result.get("status"),
            "phase": result.get("phase"),
        }

    @classmethod
    def _continuity_input(cls, result: dict[str, Any], stage: str, previous: str) -> Any:
        payload = cls._payload(result, stage)
        return {"stage": stage, "previous_continuity_tag": previous, "payload": payload}

    def run(self, task):
        result = self.kernel.run(task)
        if not isinstance(result, dict):
            raise RuntimeError("malformed_hypersynth_result")
        task_id = getattr(task, "task_id", None)
        risk_class = getattr(task, "risk_class", None)
        requirements = getattr(task, "verification_requirements", None)
        if not isinstance(task_id, str) or not task_id.strip() or not isinstance(risk_class, str) or not risk_class.strip() or not isinstance(requirements, tuple):
            raise RuntimeError("malformed_hypersynth_task_contract")

        if result.get("status") != "completed":
            return {**result, "attestations": ()}

        try:
            session = AttestationSession(self.attestation.crypto, task_id, risk_class, requirements)
            continuity = KernelContinuity(
                self.attestation.crypto,
                session_id=session.session_id,
                task_id=task_id,
                risk_class=risk_class,
                verification_requirements=requirements,
            )
        except Exception as exc:
            return {
                "status": "rejected",
                "phase": "perception",
                "verification": {"valid": False, "reason": "attestation_session_failure", "error": type(exc).__name__},
                "attestations": (),
            }

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
                return {
                    "status": "rejected",
                    "phase": stage,
                    "verification": {"valid": False, "reason": "attestation_failure", "error": type(exc).__name__},
                    "attestations": tuple(attestations),
                    "continuity_records": tuple(continuity_records),
                }

        chain = tuple(attestations)
        continuity_chain = tuple(continuity_records)
        for stage, attestation, payload in zip(self.STAGE_ORDER, chain, payloads):
            if not session.verify(attestation, stage, payload, consume=True):
                session.close()
                return {
                    "status": "rejected",
                    "phase": "verification",
                    "verification": {"valid": False, "reason": "attestation_session_verification_failure"},
                    "attestations": chain,
                    "continuity_records": continuity_chain,
                }

        if not continuity.verify_chain(continuity_chain, tuple(continuity_evidence)):
            session.close()
            return {
                "status": "rejected",
                "phase": "verification",
                "verification": {"valid": False, "reason": "kernel_continuity_verification_failure"},
                "attestations": chain,
                "continuity_records": continuity_chain,
            }

        stage_tags = tuple(item.tag for item in chain)
        continuity_tags = tuple(item.tag for item in continuity_chain)
        final_material = {
            "session_id": session.session_id,
            "task_id": task_id,
            "risk_class": risk_class,
            "verification_requirements": requirements,
            "stage_order": self.STAGE_ORDER,
            "stage_tags": stage_tags,
            "continuity_tags": continuity_tags,
        }
        final_tag = self.attestation.crypto.digest("hypersynth_final_continuity", final_material)
        expected_final = self.attestation.crypto.digest("hypersynth_final_continuity", final_material)
        final_verified = hmac.compare_digest(final_tag, expected_final)
        session.close()
        if not final_verified:
            return {
                "status": "rejected",
                "phase": "verification",
                "verification": {"valid": False, "reason": "final_continuity_binding_failure"},
                "attestations": chain,
                "continuity_records": continuity_chain,
            }

        return {
            **result,
            "attestations": chain,
            "attestation_verified": True,
            "attestation_session_id": session.session_id,
            "attestation_context_tag": session.context_tag,
            "continuity_records": continuity_chain,
            "continuity_verified": True,
            "final_continuity_tag": final_tag,
        }
