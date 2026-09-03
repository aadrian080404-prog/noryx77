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
        if not plan.steps or len(plan.steps) != len(hypotheses) or len(hypotheses) != len(simulations) or len(simulations) != len(results):
            return VerificationResult(False, "metacognition", "pipeline_count_mismatch"), None
        if any(not isinstance(result, AgentResult) or result.status != "completed" for result in results):
            return VerificationResult(False, "metacognition", "incomplete_result_set"), None
        if any(result.verification is None or not result.verification.valid for result in results):
            return VerificationResult(False, "metacognition", "unverified_result_set"), None
        agents = tuple(result.agent_id for result in results)
        if len(set(agents)) != len(agents):
            return VerificationResult(False, "metacognition", "duplicate_agent_identity"), None
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
