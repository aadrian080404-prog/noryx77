"""Attested HYPERSYNTH execution facade.

The existing Hypersynth remains the execution engine. This facade adds a
cryptographically bound evidence record over its externally observable stages.
It never treats cryptography as proof of semantic truth.
"""

from __future__ import annotations

from typing import Any

from .attestation import HypersynthAttestation, StageAttestation
from .crypto import CryptoIntegrity
from .hypersynth import Hypersynth


class AttestedHypersynthKernel:
    """Run the bounded kernel and emit an authenticated stage evidence chain."""

    STAGE_ORDER = (
        "perception",
        "context",
        "planning",
        "hypothesis",
        "simulation",
        "allocation",
        "execution",
        "verification",
        "metacognition",
    )

    def __init__(self, kernel: Hypersynth, *, crypto: CryptoIntegrity | None = None,
                 attestation: HypersynthAttestation | None = None):
        if not isinstance(kernel, Hypersynth):
            raise TypeError("invalid_hypersynth_kernel")
        if attestation is not None and crypto is not None:
            raise ValueError("crypto_and_attestation_are_mutually_exclusive")
        self.kernel = kernel
        self.attestation = attestation or HypersynthAttestation(crypto or CryptoIntegrity())

    @staticmethod
    def _payload(result: dict[str, Any], stage: str) -> Any:
        if stage == "perception":
            return {"task_id": result.get("state").task_id if result.get("state") is not None else result.get("task_id"),
                    "verification": result.get("verification")}
        if stage == "context":
            return result.get("context")
        if stage == "planning":
            return result.get("plan")
        if stage == "hypothesis":
            return result.get("hypotheses")
        if stage == "simulation":
            return result.get("simulations")
        if stage == "allocation":
            return tuple((r.agent_id, r.task_id) for r in result.get("results", ()))
        if stage == "execution":
            return result.get("results")
        if stage == "verification":
            return result.get("verification")
        if stage == "metacognition":
            return result.get("reflection")
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

        attestations: list[StageAttestation] = []
        for stage in self.STAGE_ORDER:
            try:
                payload = self._payload(result, stage)
                attestations.append(self.attestation.attest_stage(task_id, stage, risk_class, requirements, payload))
            except Exception as exc:
                return {
                    "status": "rejected",
                    "phase": stage,
                    "verification": {"valid": False, "reason": "attestation_failure", "error": type(exc).__name__},
                    "attestations": tuple(attestations),
                }
        chain = tuple(attestations)
        payloads = tuple(self._payload(result, stage) for stage in self.STAGE_ORDER)
        if not self.attestation.verify_pipeline(chain, payloads, task_id, risk_class, requirements):
            return {
                "status": "rejected",
                "phase": "verification",
                "verification": {"valid": False, "reason": "attestation_chain_failure"},
                "attestations": chain,
            }
        return {**result, "attestations": chain, "attestation_verified": True}
