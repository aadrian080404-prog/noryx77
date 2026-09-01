"""Attested HYPERSYNTH execution facade.

The existing Hypersynth remains the execution engine. This facade adds a
cryptographically bound evidence record over its externally observable stages.
It never treats cryptography as proof of semantic truth.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from .attestation import HypersynthAttestation, StageAttestation
from .attestation_session import AttestationSession
from .crypto import CryptoIntegrity
from .hypersynth import Hypersynth


class AttestedHypersynthKernel:
    """Run the bounded kernel and emit an authenticated stage evidence chain."""

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
        except Exception as exc:
            return {
                "status": "rejected",
                "phase": "perception",
                "verification": {"valid": False, "reason": "attestation_session_failure", "error": type(exc).__name__},
                "attestations": (),
            }

        attestations: list[StageAttestation] = []
        payloads: list[Any] = []
        for stage in self.STAGE_ORDER:
            try:
                payload = self._payload(result, stage)
                payloads.append(payload)
                attestations.append(session.attest(stage, payload))
            except Exception as exc:
                session.close()
                return {
                    "status": "rejected",
                    "phase": stage,
                    "verification": {"valid": False, "reason": "attestation_failure", "error": type(exc).__name__},
                    "attestations": tuple(attestations),
                }

        chain = tuple(attestations)
        for stage, attestation, payload in zip(self.STAGE_ORDER, chain, payloads):
            if not session.verify(attestation, stage, payload, consume=True):
                session.close()
                return {
                    "status": "rejected",
                    "phase": "verification",
                    "verification": {"valid": False, "reason": "attestation_session_verification_failure"},
                    "attestations": chain,
                }

        session.close()
        return {
            **result,
            "attestations": chain,
            "attestation_verified": True,
            "attestation_session_id": session.session_id,
            "attestation_context_tag": session.context_tag,
        }
