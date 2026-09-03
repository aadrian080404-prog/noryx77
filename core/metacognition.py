from dataclasses import dataclass

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

    def __getitem__(self, key: str):
        """Preserve the legacy mapping-style reflection API while exposing typed fields."""
        if not isinstance(key, str) or not hasattr(self, key):
            raise KeyError(key)
        return getattr(self, key)


class MetacognitionEngine:
    """Bounded final self-check over observable pipeline invariants; no hidden reasoning traces."""

    def reflect(
        self,
        task: TaskSpec,
        plan: Plan,
        hypotheses: tuple[Hypothesis, ...],
        simulations: tuple[SimulationResult, ...],
        results: tuple[AgentResult, ...],
        final_verification: VerificationResult,
    ) -> tuple[VerificationResult, MetacognitiveReflection | None]:
        if not isinstance(task, TaskSpec) or not isinstance(plan, Plan):
            return VerificationResult(False, "metacognition", "invalid_reflection_inputs"), None
        if not isinstance(hypotheses, tuple) or not isinstance(simulations, tuple) or not isinstance(results, tuple):
            return VerificationResult(False, "metacognition", "invalid_reflection_collection"), None
        if not isinstance(final_verification, VerificationResult) or not final_verification.valid:
            return VerificationResult(False, "metacognition", "final_verification_failed"), None
        if plan.task_id != task.task_id or not plan.steps:
            return VerificationResult(False, "metacognition", "plan_identity_mismatch"), None
        if len(plan.steps) != len(hypotheses) or len(hypotheses) != len(simulations) or len(simulations) != len(results):
            return VerificationResult(False, "metacognition", "pipeline_count_mismatch"), None
        plan_step_ids = tuple(step.step_id for step in plan.steps)
        if any(not isinstance(step.step_id, str) or not step.step_id.strip() for step in plan.steps):
            return VerificationResult(False, "metacognition", "invalid_plan_step_identity"), None
        if len(set(plan_step_ids)) != len(plan_step_ids):
            return VerificationResult(False, "metacognition", "duplicate_plan_step_identity"), None
        for hypothesis, step in zip(hypotheses, plan.steps):
            if not isinstance(hypothesis, Hypothesis):
                return VerificationResult(False, "metacognition", "invalid_hypothesis_type"), None
            if hypothesis.task_id != task.task_id or hypothesis.statement != step.objective or hypothesis.basis != (step.step_id,):
                return VerificationResult(False, "metacognition", "hypothesis_plan_identity_mismatch"), None
        expected_hypothesis_ids = tuple(h.hypothesis_id for h in hypotheses)
        actual_simulation_ids = tuple(simulation.hypothesis_id for simulation in simulations if isinstance(simulation, SimulationResult))
        if len(actual_simulation_ids) != len(simulations) or actual_simulation_ids != expected_hypothesis_ids:
            return VerificationResult(False, "metacognition", "simulation_hypothesis_identity_mismatch"), None
        if any(not isinstance(result, AgentResult) or result.status != "completed" for result in results):
            return VerificationResult(False, "metacognition", "incomplete_result_set"), None
        if any(result.verification is None or not result.verification.valid for result in results):
            return VerificationResult(False, "metacognition", "unverified_result_set"), None
        if any(result.verification.stage != "agent_result" for result in results):
            return VerificationResult(False, "metacognition", "result_verification_stage_mismatch"), None
        result_task_ids = tuple(result.task_id for result in results)
        if len(set(result_task_ids)) != len(result_task_ids):
            return VerificationResult(False, "metacognition", "duplicate_result_task_identity"), None
        if result_task_ids != plan_step_ids:
            return VerificationResult(False, "metacognition", "result_plan_order_mismatch"), None
        agents = tuple(result.agent_id for result in results)
        if len(set(agents)) != len(agents):
            return VerificationResult(False, "metacognition", "duplicate_agent_identity"), None
        if any(not isinstance(simulation, SimulationResult) for simulation in simulations):
            return VerificationResult(False, "metacognition", "invalid_simulation_type"), None
        if any(not simulation.feasible for simulation in simulations):
            return VerificationResult(False, "metacognition", "infeasible_simulation_present"), None
        reflection = MetacognitiveReflection(
            result_verified=True,
            agents_used=agents,
            steps_executed=len(results),
            hypotheses_verified=len(hypotheses),
            simulations_verified=len(simulations),
            confidence=1.0,
        )
        return VerificationResult(True, "metacognition", "reflection_ok"), reflection
