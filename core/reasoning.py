from dataclasses import dataclass

from .contracts import AgentResult, TaskSpec, VerificationResult
from .planning import Plan


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    task_id: str
    statement: str
    basis: tuple[str, ...] = ()


@dataclass(frozen=True)
class SimulationResult:
    hypothesis_id: str
    feasible: bool
    reason: str


class HypothesisEngine:
    """Bounded, inspectable hypothesis generation; never exposes hidden reasoning traces."""

    def generate(self, task: TaskSpec, plan: Plan) -> tuple[Hypothesis, ...]:
        if not plan.steps:
            return ()
        return tuple(
            Hypothesis(
                hypothesis_id=f"{task.task_id}:h{index}",
                task_id=task.task_id,
                statement=step.objective,
                basis=(step.step_id,),
            )
            for index, step in enumerate(plan.steps)
        )

    def verify(self, hypotheses: tuple[Hypothesis, ...], task: TaskSpec) -> VerificationResult:
        if not hypotheses:
            return VerificationResult(False, "hypothesis", "no_hypotheses")
        for hypothesis in hypotheses:
            if hypothesis.task_id != task.task_id or not hypothesis.statement or not hypothesis.basis:
                return VerificationResult(False, "hypothesis", "invalid_hypothesis")
        return VerificationResult(True, "hypothesis", "hypotheses_ok")


class InternalSimulator:
    """Pre-execution bounded feasibility check over the declared plan only."""

    def simulate(self, task: TaskSpec, hypotheses: tuple[Hypothesis, ...]) -> tuple[SimulationResult, ...]:
        return tuple(
            SimulationResult(
                hypothesis.hypothesis_id,
                bool(hypothesis.statement and hypothesis.task_id == task.task_id),
                "feasible" if hypothesis.statement and hypothesis.task_id == task.task_id else "invalid_hypothesis",
            )
            for hypothesis in hypotheses
        )

    def verify(self, simulations: tuple[SimulationResult, ...]) -> VerificationResult:
        if not simulations:
            return VerificationResult(False, "simulation", "no_simulations")
        if any(not item.feasible for item in simulations):
            return VerificationResult(False, "simulation", "simulation_rejected")
        return VerificationResult(True, "simulation", "simulation_ok")


class CrossChecker:
    """Checks that verified agent results map back to the declared plan steps."""

    def verify(self, task: TaskSpec, results: tuple[AgentResult, ...], hypotheses: tuple[Hypothesis, ...]) -> VerificationResult:
        if not results:
            return VerificationResult(False, "cross_check", "no_results")
        if len(results) != len(hypotheses):
            return VerificationResult(False, "cross_check", "result_hypothesis_count_mismatch")
        expected_step_ids = {hypothesis.basis[0] for hypothesis in hypotheses if hypothesis.basis}
        if len(expected_step_ids) != len(hypotheses):
            return VerificationResult(False, "cross_check", "duplicate_hypothesis_basis")
        if any(result.task_id not in expected_step_ids for result in results):
            return VerificationResult(False, "cross_check", "result_task_mismatch")
        if any(result.status != "completed" for result in results):
            return VerificationResult(False, "cross_check", "incomplete_result")
        return VerificationResult(True, "cross_check", "cross_check_ok")
