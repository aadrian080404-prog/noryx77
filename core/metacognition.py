from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping

from .contracts import AgentResult, TaskSpec, VerificationResult
from .reasoning import Hypothesis, SimulationResult
from .planning import Plan


@dataclass(frozen=True)
class MetacognitiveReflection:
    result_verified: bool
    agents_used: tuple[str, ...]
    steps_executed: int
    hypotheses_verified: int
    simulations_verified: int
    confidence: float
    calibration_score: float
    strategy_score: float
    anomalies: tuple[str, ...] = ()
    error_attribution: tuple[tuple[str, str], ...] = ()
    correction_required: bool = False
    recommended_action: str = "accept"
    learning_signal: str = "stable"
    state_fingerprint: str = ""

    def __getitem__(self, key: str):
        if not isinstance(key, str) or not hasattr(self, key):
            raise KeyError(key)
        return getattr(self, key)


class MetacognitionEngine:
    """Bounded, observable self-monitoring and self-correction gate.

    Only externally observable pipeline facts are consumed. Hidden reasoning traces are
    neither inspected nor emitted. Side-effecting automatic retries are intentionally not
    performed without an explicit idempotency guarantee; the engine instead emits a bounded
    correction decision and fails closed when acceptance criteria are not met.
    """

    _MAX_ANOMALIES = 16
    _MAX_ATTRIBUTIONS = 16
    _VALID_ACTIONS = {"accept", "replan", "resimulate", "escalate", "reject"}

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _fingerprint(parts: tuple[str, ...]) -> str:
        return sha256("|".join(parts).encode("utf-8")).hexdigest()

    @staticmethod
    def _failure(reason: str):
        return VerificationResult(False, "metacognition", reason), None

    def reflect(
        self,
        task: TaskSpec,
        plan: Plan,
        hypotheses: tuple[Hypothesis, ...],
        simulations: tuple[SimulationResult, ...],
        results: tuple[AgentResult, ...],
        final_verification: VerificationResult,
        *,
        telemetry: Mapping[str, object] | None = None,
        prior_confidence: float | None = None,
    ) -> tuple[VerificationResult, MetacognitiveReflection | None]:
        if not isinstance(task, TaskSpec) or not isinstance(plan, Plan):
            return self._failure("invalid_reflection_inputs")
        if not isinstance(hypotheses, tuple) or not isinstance(simulations, tuple) or not isinstance(results, tuple):
            return self._failure("invalid_reflection_collection")
        if not isinstance(final_verification, VerificationResult) or not final_verification.is_well_formed() or not final_verification.valid:
            return self._failure("final_verification_failed")
        if plan.task_id != task.task_id or not plan.steps:
            return self._failure("plan_identity_mismatch")
        if len(plan.steps) != len(hypotheses) or len(hypotheses) != len(simulations) or len(simulations) != len(results):
            return self._failure("pipeline_count_mismatch")

        plan_step_ids = tuple(step.step_id for step in plan.steps)
        if any(not isinstance(step.step_id, str) or not step.step_id.strip() for step in plan.steps):
            return self._failure("invalid_plan_step_identity")
        if len(set(plan_step_ids)) != len(plan_step_ids):
            return self._failure("duplicate_plan_step_identity")

        for hypothesis, step in zip(hypotheses, plan.steps):
            if not isinstance(hypothesis, Hypothesis):
                return self._failure("invalid_hypothesis_type")
            if hypothesis.task_id != task.task_id or hypothesis.statement != step.objective or hypothesis.basis != (step.step_id,):
                return self._failure("hypothesis_plan_identity_mismatch")

        expected_hypothesis_ids = tuple(h.hypothesis_id for h in hypotheses)
        if any(not isinstance(simulation, SimulationResult) for simulation in simulations):
            return self._failure("invalid_simulation_type")
        if tuple(simulation.hypothesis_id for simulation in simulations) != expected_hypothesis_ids:
            return self._failure("simulation_hypothesis_identity_mismatch")
        if any(not simulation.feasible for simulation in simulations):
            return self._failure("infeasible_simulation_present")

        if any(not isinstance(result, AgentResult) or result.status != "completed" for result in results):
            return self._failure("incomplete_result_set")
        if any(result.verification is None or not result.verification.is_well_formed() or not result.verification.valid for result in results):
            return self._failure("unverified_result_set")
        if any(result.verification.stage != "agent_result" for result in results):
            return self._failure("result_verification_stage_mismatch")

        result_task_ids = tuple(result.task_id for result in results)
        if len(set(result_task_ids)) != len(result_task_ids):
            return self._failure("duplicate_result_task_identity")
        if result_task_ids != plan_step_ids:
            return self._failure("result_plan_order_mismatch")
        agents = tuple(result.agent_id for result in results)
        if len(set(agents)) != len(agents):
            return self._failure("duplicate_agent_identity")

        telemetry = telemetry if isinstance(telemetry, Mapping) else {}
        anomalies: list[str] = []
        attribution: list[tuple[str, str]] = []

        def flag(name: str, owner: str) -> None:
            if len(anomalies) < self._MAX_ANOMALIES and name not in anomalies:
                anomalies.append(name)
            if len(attribution) < self._MAX_ATTRIBUTIONS and (owner, name) not in attribution:
                attribution.append((owner, name))

        latency = telemetry.get("latency_ratio")
        if isinstance(latency, (int, float)) and not isinstance(latency, bool) and latency > 1.0:
            flag("latency_budget_pressure", "runtime")
        disagreement = telemetry.get("disagreement")
        if disagreement is True:
            flag("agent_disagreement", "coordination")
        resource_pressure = telemetry.get("resource_pressure")
        if isinstance(resource_pressure, (int, float)) and not isinstance(resource_pressure, bool) and resource_pressure > 0.9:
            flag("resource_pressure", "allocation")
        if prior_confidence is not None and (not isinstance(prior_confidence, (int, float)) or isinstance(prior_confidence, bool) or not 0.0 <= prior_confidence <= 1.0):
            return self._failure("invalid_prior_confidence")

        verification = sum(1 for result in results if result.verification and result.verification.valid) / len(results)
        simulation_quality = sum(1 for simulation in simulations if simulation.feasible) / len(simulations)
        telemetry_penalty = min(0.4, 0.1 * len(anomalies))
        confidence = self._clamp(0.35 + 0.35 * verification + 0.30 * simulation_quality - telemetry_penalty)
        if prior_confidence is not None:
            confidence = self._clamp(0.7 * confidence + 0.3 * prior_confidence)

        evidence_quality = self._clamp((verification + simulation_quality) / 2.0)
        calibration_score = self._clamp(1.0 - abs(confidence - evidence_quality))
        strategy_score = self._clamp(0.5 + 0.5 * simulation_quality - 0.1 * len(anomalies))

        action = "accept"
        learning_signal = "stable"
        correction_required = False
        if anomalies:
            correction_required = True
            action = "escalate" if len(anomalies) >= 2 else "replan"
            learning_signal = "adapt"
        if confidence < 0.60:
            correction_required = True
            action = "escalate"
            learning_signal = "uncertain"
        if calibration_score < 0.70:
            correction_required = True
            action = "escalate"
            learning_signal = "recalibrate"
        if action not in self._VALID_ACTIONS:
            return self._failure("invalid_metacognitive_action")

        fingerprint = self._fingerprint((
            task.execution_id,
            task.task_id,
            str(len(plan.steps)),
            str(len(hypotheses)),
            str(len(simulations)),
            str(len(results)),
            "|".join(agents),
            "|".join(anomalies),
        ))
        reflection = MetacognitiveReflection(
            result_verified=True,
            agents_used=agents,
            steps_executed=len(results),
            hypotheses_verified=len(hypotheses),
            simulations_verified=len(simulations),
            confidence=confidence,
            calibration_score=calibration_score,
            strategy_score=strategy_score,
            anomalies=tuple(anomalies),
            error_attribution=tuple(attribution),
            correction_required=correction_required,
            recommended_action=action,
            learning_signal=learning_signal,
            state_fingerprint=fingerprint,
        )
        if correction_required:
            return VerificationResult(False, "metacognition", "reflection_requires_correction"), reflection
        return VerificationResult(True, "metacognition", "reflection_ok"), reflection
